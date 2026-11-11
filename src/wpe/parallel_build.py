"""
Progress dashboard for `wpe full-pack`.

- Every pipeline step (hooks, platform builds, pack) is shown as one progress row.
- Platforms are built in parallel; configurations of the same platform are built
  sequentially, each one in its own `python -m wpe.build_task` subprocess.
- Packages of different platforms are also created in parallel subprocesses (see PackageRunner,
  also used by `wpe pack` without the dashboard).
- All output (builds, hooks, pack, and wpe's own logging) is redirected to log files.
  The terminal only shows the progress rows, followed by a summary when finished.
"""
import builtins
import io
import locale
import logging
import os
import os.path as osp
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.console import Console, ConsoleDimensions
from rich.progress import (BarColumn, MofNCompleteColumn, Progress, ProgressColumn, Task, TextColumn,
                           TimeElapsedColumn)
from rich.spinner import Spinner
from rich.table import Column, Table
from rich.text import Text


class Status:
    WAITING = 'waiting'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    SKIPPED = 'skipped'


_STATUS_STYLE = {
    Status.WAITING: 'dim',
    Status.RUNNING: 'cyan',
    Status.SUCCESS: 'green',
    Status.FAILED: 'bold red',
    Status.SKIPPED: 'yellow',
}

_LOG_ENCODING = locale.getpreferredencoding(False)


# Step kinds that run out-of-process (their output never goes through this process' stdout),
# so an in-process hook may safely run in the background while they are running.
PARALLELIZABLE_STEP_KINDS = ('build',)


class StepFailed(Exception):
    pass


class PackageFailed(RuntimeError):
    pass


@dataclass
class TaskResult:
    """One unit of work, i.e. one line in the summary table and one log file."""
    name: str
    config: str
    log: str
    status: str = Status.WAITING
    duration: float = 0.0
    detail: str = ''


@dataclass
class Row:
    """One progress row."""
    name: str
    kind: str  # 'hook' | 'build' | 'pack' | 'unsupported'
    results: list[TaskResult]
    taskId: Optional[int] = None
    currentLog: Optional[str] = None
    state: str = Status.WAITING
    total: int = 1


@dataclass
class PlatformBuildJob:
    platform: str
    # wp.py build args, with `{config}` placeholder for the configuration value
    build_args: list[str]
    configs: list[str]
    row: Optional[Row] = None

    def args_for(self, config: str) -> list[str]:
        return [config if arg == '{config}' else arg for arg in self.build_args]


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}h {m:02d}m {s:02d}s'
    if m:
        return f'{m}m {s:02d}s'
    return f'{s}s'


def _read_log_tail(path: str, max_bytes: int = 8192) -> list[str]:
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read()
    except OSError:
        return []
    text = data.decode(_LOG_ENCODING, errors='replace')
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def _kill_tree(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()


class ProcessRegistry:
    """Thread-safe set of running child processes, to be able to kill them all on Ctrl+C / abort."""

    def __init__(self):
        self._lock = threading.Lock()
        self._procs: set[subprocess.Popen] = set()

    def add(self, proc: subprocess.Popen):
        with self._lock:
            self._procs.add(proc)

    def discard(self, proc: subprocess.Popen):
        with self._lock:
            self._procs.discard(proc)

    def kill_all(self):
        with self._lock:
            procs = list(self._procs)
        for proc in procs:
            _kill_tree(proc)


def run_task_process(kind: str, args: list[str], cwd: str, log_path: str,
                     registry: Optional[ProcessRegistry] = None) -> int:
    """Run `python -m wpe.build_task <kind> <args>` with all its output written to `log_path`."""
    cmd = [sys.executable, '-u', '-m', 'wpe.build_task', kind] + list(args)
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    with open(log_path, 'wb') as log_file:
        log_file.write(f'> {subprocess.list2cmdline(cmd)}\n\n'.encode(_LOG_ENCODING, errors='replace'))
        log_file.flush()
        popen_kwargs = {'start_new_session': True} if os.name != 'nt' else {}
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=log_file, stderr=subprocess.STDOUT, **popen_kwargs)
        if registry is not None:
            registry.add(proc)
        try:
            return proc.wait()
        finally:
            if registry is not None:
                registry.discard(proc)


def _wait_futures(futures):
    pending = set(futures)
    while pending:
        # Short timeout keeps the main thread responsive to Ctrl+C.
        _, pending = wait(pending, timeout=0.2, return_when=FIRST_EXCEPTION)
    for f in futures:
        f.result()


class PackageListener:
    """Progress callbacks of PackageRunner. Called from worker threads."""

    def started(self, result: TaskResult):
        pass

    def finished(self, result: TaskResult):
        pass


class _LoggingPackageListener(PackageListener):
    def started(self, result: TaskResult):
        logging.info(f'Packaging {result.config}... (log: {result.log})')

    def finished(self, result: TaskResult):
        if result.status == Status.SUCCESS:
            logging.info(f'Packaged {result.config} in {format_duration(result.duration)}')
        else:
            logging.error(f'Packaging {result.config} failed ({result.detail}), log: {result.log}')


class PackageRunner:
    """
    Run `wp.py package <target>` for several targets in parallel, each in its own process and log file.
    The packages are written to `cwd` (the plugin project root) with distinct names, and the packaging
    only reads build artifacts, so the targets do not interfere with each other.
    On failure, running targets are left to finish, targets not started yet are skipped.
    """

    def __init__(self, cwd: str, log_dir: str, max_workers: int,
                 results: Optional[dict] = None,
                 listener: Optional[PackageListener] = None):
        self.cwd = cwd
        self.logDir = log_dir
        self.maxWorkers = max(1, max_workers)
        self.results: dict[str, TaskResult] = dict(results or {})
        self.listener = listener or _LoggingPackageListener()
        self.elapsed = 0.0

    @staticmethod
    def result_for(name: str, target: str, log_dir: str) -> TaskResult:
        return TaskResult(name, target, osp.join(log_dir, f'pack_{target}.log'))

    def run(self, targets: list[str], version: str) -> list[TaskResult]:
        os.makedirs(self.logDir, exist_ok=True)
        results = [self.results.setdefault(t, self.result_for('pack', t, self.logDir)) for t in targets]
        # Authoring packages (Debug + Release archives in one task) are the largest, start them first.
        ordered = sorted(results, key=lambda r: not r.config.startswith('Authoring'))
        abort = threading.Event()
        registry = ProcessRegistry()

        def run_one(result: TaskResult):
            if abort.is_set():
                result.status = Status.SKIPPED
                return
            result.status = Status.RUNNING
            self.listener.started(result)
            start = time.perf_counter()
            returncode = None
            try:
                returncode = run_task_process('package', [result.config, '-v', version], self.cwd, result.log,
                                              registry)
            except BaseException as e:
                result.detail = f'{type(e).__name__}: {e}'
                raise
            finally:
                result.duration = time.perf_counter() - start
                if returncode == 0:
                    result.status = Status.SUCCESS
                else:
                    result.status = Status.FAILED
                    result.detail = result.detail or f'exit code {returncode}'
                    abort.set()
                self.listener.finished(result)

        start = time.perf_counter()
        try:
            with ThreadPoolExecutor(max_workers=self.maxWorkers, thread_name_prefix='wpe-package') as pool:
                _wait_futures([pool.submit(run_one, r) for r in ordered])
        except BaseException:
            abort.set()
            registry.kill_all()
            raise
        finally:
            self.elapsed = time.perf_counter() - start
        failed = [r for r in results if r.status == Status.FAILED]
        if failed:
            raise PackageFailed(f'Package failed: {", ".join(r.config for r in failed)}. '
                                f'Logs: {", ".join(r.log for r in failed)}')
        return results


class OutputRedirect:
    """
    Redirect everything written to stdout/stderr of this process to a log file:
    OS-level fds 1/2 (inherited by child processes), sys.stdout/sys.stderr and the
    stream handlers of the root logger. Supports nesting.
    """

    def __init__(self, log_path: str):
        self.logPath = log_path

    def __enter__(self):
        sys.stdout.flush()
        sys.stderr.flush()
        self._log = open(self.logPath, 'ab', buffering=0)
        self._savedFds = (os.dup(1), os.dup(2))
        os.dup2(self._log.fileno(), 1)
        os.dup2(self._log.fileno(), 2)
        self._stream = io.TextIOWrapper(os.fdopen(os.dup(self._log.fileno()), 'wb'), encoding=_LOG_ENCODING,
                                        errors='replace', line_buffering=True, write_through=True)
        self._savedSys = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = self._stream
        self._savedHandlers = [(h, h.setStream(self._stream)) for h in logging.root.handlers
                               if type(h) is logging.StreamHandler]
        return self

    def __exit__(self, *exc):
        for handler, stream in self._savedHandlers:
            handler.setStream(stream)
        sys.stdout, sys.stderr = self._savedSys
        try:
            self._stream.flush()
        finally:
            os.dup2(self._savedFds[0], 1)
            os.dup2(self._savedFds[1], 2)
            for fd in self._savedFds:
                os.close(fd)
            self._stream.close()
            self._log.close()
        return False


def _enable_windows_vt():
    """Enable ANSI escape sequence processing on classic Windows consoles (conhost)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


class _TerminalConsole(Console):
    """
    Console bound to a dedicated terminal fd. Rich queries the terminal size via the standard fds,
    which point to log files while the output is redirected, so query our own fd instead.
    """

    def __init__(self, terminal_file, **kwargs):
        self._terminalFd = terminal_file.fileno()
        super().__init__(file=terminal_file, **kwargs)

    @property
    def size(self) -> ConsoleDimensions:
        try:
            width, height = os.get_terminal_size(self._terminalFd)
        except (OSError, ValueError):
            return Console.size.fget(self)
        return ConsoleDimensions(width - self.legacy_windows, height)

    @size.setter
    def size(self, new_size):
        Console.size.fset(self, new_size)


class _StateColumn(ProgressColumn):
    def __init__(self):
        super().__init__(table_column=Column(width=1, no_wrap=True))
        self.spinner = Spinner('dots', style='cyan')

    def render(self, task: Task):
        state = task.fields.get('state', Status.WAITING)
        if state == Status.RUNNING:
            return self.spinner.render(task.get_time())
        symbol = {Status.WAITING: '·', Status.SUCCESS: '√', Status.FAILED: '×', Status.SKIPPED: '-'}[state]
        return Text(symbol, style=_STATUS_STYLE[state])


class _DashboardProgress(Progress):
    """
    Progress with compact fixed-width columns followed by a single-line log preview on the same line.
    The log preview takes all the remaining terminal width and is truncated with an ellipsis.
    """
    BAR_WIDTH = 12
    STATUS_WIDTH = 10
    ELAPSED_WIDTH = 9

    def __init__(self, **kwargs):
        self._nameColumn = Column(no_wrap=True)
        self._mofnColumn = Column(no_wrap=True, justify='right')
        super().__init__(
            _StateColumn(),
            TextColumn('[bold]{task.fields[name]}', table_column=self._nameColumn),
            BarColumn(bar_width=self.BAR_WIDTH, table_column=Column(width=self.BAR_WIDTH, no_wrap=True)),
            MofNCompleteColumn(table_column=self._mofnColumn),
            TextColumn('{task.fields[status]}',
                       table_column=Column(width=self.STATUS_WIDTH, no_wrap=True, overflow='ellipsis')),
            TimeElapsedColumn(table_column=Column(width=self.ELAPSED_WIDTH, no_wrap=True)),
            expand=False,
            **kwargs)

    def _fit_columns(self, tasks) -> int:
        """Size the variable columns to their content, returns the total width of the fixed part."""
        self._nameColumn.width = max([len(t.fields.get('name', '')) for t in tasks] + [4])
        self._mofnColumn.width = max([len(f'{int(t.completed)}/{int(t.total or 0)}') for t in tasks] + [3])
        widths = [1, self._nameColumn.width, self.BAR_WIDTH, self._mofnColumn.width, self.STATUS_WIDTH,
                  self.ELAPSED_WIDTH]
        return sum(widths) + len(widths) - 1  # 1 padding between columns

    def get_renderables(self):
        tasks = [t for t in self.tasks if t.visible]
        if not tasks:
            return
        fixed_width = self._fit_columns(tasks)
        log_width = max(1, self.console.width - fixed_width - 1)
        table = Table.grid(*[c.get_table_column().copy() for c in self.columns],
                           Column(no_wrap=True, overflow='ellipsis', width=log_width), padding=(0, 1))
        for task in tasks:
            table.add_row(*(column(task) for column in self.columns),
                          Text(task.fields.get('last', ''), style='dim', no_wrap=True, overflow='ellipsis'))
        yield table


class FullPackDashboard:
    def __init__(self, log_dir: str):
        self.logDir = log_dir
        os.makedirs(self.logDir, exist_ok=True)
        self.mainLog = osp.join(self.logDir, 'full_pack.log')
        # Dedicated handle to the real terminal, unaffected by the output redirection.
        sys.stdout.flush()
        _enable_windows_vt()
        self._terminal = open(os.dup(1), 'w', encoding=sys.stdout.encoding or 'utf-8', errors='replace',
                              buffering=1, closefd=True)
        self.console = _TerminalConsole(self._terminal)
        self.rows: list[Row] = []
        self.buildElapsed = 0.0
        self.maxWorkers = 1
        self.extraInfo: list[tuple[str, str]] = []
        self._abort = threading.Event()
        self._lock = threading.Lock()
        self._procs = ProcessRegistry()
        self._packRunner: Optional[PackageRunner] = None
        self._stopTail = threading.Event()
        self._inputLock = threading.Lock()
        self._stepContext = threading.local()
        self._progress = _DashboardProgress(
            console=self.console,
            refresh_per_second=8,
            redirect_stdout=False,
            redirect_stderr=False,
        )

    # ---------------------------------------------------------------- lifecycle
    def __enter__(self):
        self.console.print(f'[bold]wpe full-pack[/bold]  logs: {self.logDir}', highlight=False)
        self._progress.start()
        self._tailThread = threading.Thread(target=self._tail_loop, name='wpe-log-tail', daemon=True)
        self._tailThread.start()
        self._redirect = OutputRedirect(self.mainLog)
        self._redirect.__enter__()
        self._orgInput = builtins.input
        builtins.input = self._input
        return self

    def __exit__(self, *exc):
        builtins.input = self._orgInput
        self._redirect.__exit__(*exc)
        for row in self.rows:
            for r in row.results:
                if r.status in (Status.WAITING, Status.RUNNING):
                    r.status = Status.SKIPPED
            if row.state in (Status.WAITING, Status.RUNNING):
                self._set_row(row, Status.SKIPPED, '[yellow]skipped')
        self._stopTail.set()
        self._tailThread.join()
        self._progress.stop()
        return False

    def close(self):
        self._terminal.close()

    # ---------------------------------------------------------------- rows
    def _add_row(self, row: Row, total: int) -> Row:
        row.total = total
        row.taskId = self._progress.add_task('', total=total, start=False, name=row.name,
                                             state=Status.WAITING, status='[dim]waiting', last='')
        self.rows.append(row)
        return row

    def add_step(self, name: str, kind: str, log_name: str, waiting_status: Optional[str] = None) -> Row:
        row = self._add_row(Row(name, kind, [TaskResult(name, '', osp.join(self.logDir, log_name))]), 1)
        if waiting_status:
            self._progress.update(row.taskId, status=waiting_status)
        return row

    def add_build(self, job: PlatformBuildJob) -> Row:
        results = [TaskResult(job.platform, cfg, osp.join(self.logDir, f'build_{job.platform}_{cfg}.log'))
                   for cfg in job.configs]
        job.row = self._add_row(Row(job.platform, 'build', results), len(job.configs))
        return job.row

    def add_pack(self, targets: list[str]) -> Row:
        """Pack row: the first result is the pack step itself, followed by one result per package target."""
        results = [TaskResult('pack', '', osp.join(self.logDir, 'pack.log'))]
        results += [PackageRunner.result_for('pack', t, self.logDir) for t in targets]
        return self._add_row(Row('pack', 'pack', results), max(1, len(targets)))

    def package_runner(self, row: Row, cwd: str, max_workers: int) -> PackageRunner:
        """PackageRunner reporting its progress to the pack row."""
        dashboard = self
        running: list[TaskResult] = []

        class Listener(PackageListener):
            @staticmethod
            def _refresh():
                names = ', '.join(r.config for r in running)
                dashboard._progress.update(row.taskId, status=f'[cyan]{names}' if names else '[cyan]running')

            def started(self, result: TaskResult):
                with dashboard._lock:
                    running.append(result)
                    row.currentLog = result.log
                    self._refresh()
                dashboard._note(f'[pack] {result.config} started')

            def finished(self, result: TaskResult):
                with dashboard._lock:
                    if result in running:
                        running.remove(result)
                    row.currentLog = running[-1].log if running else row.results[0].log
                    if result.status == Status.SUCCESS:
                        dashboard._progress.advance(row.taskId)
                    self._refresh()
                dashboard._note(f'[pack] {result.config} {result.status} in {format_duration(result.duration)}')

        runner = PackageRunner(cwd, self.logDir, max_workers, results={r.config: r for r in row.results[1:]},
                               listener=Listener())
        self._packRunner = runner
        return runner

    def add_unsupported(self, name: str) -> Row:
        row = self._add_row(Row(name, 'unsupported', [TaskResult(name, '', '', Status.SKIPPED,
                                                                 detail='not supported on this host')]), 1)
        self._set_row(row, Status.SKIPPED, '[yellow]not supported')
        return row

    def _set_row(self, row: Row, state: str, status: str):
        row.state = state
        self._progress.update(row.taskId, state=state, status=status, last='')

    def _note(self, message: str):
        # Live progress is not rendered on non-interactive output, print plain events instead.
        if not self.console.is_terminal:
            self.console.print(message, markup=False, highlight=False)

    def _tail_loop(self):
        while not self._stopTail.wait(0.2):
            for row in self.rows:
                log = row.currentLog
                if log:
                    lines = _read_log_tail(log, max_bytes=2048)
                    self._progress.update(row.taskId, last=lines[-1].strip() if lines else '')

    def _input(self, prompt=''):
        """
        Replacement of builtins.input while the dashboard is active: stdout is redirected to log files,
        so pause the live display and ask on the real terminal.
        """
        prompt = str(prompt)
        row = getattr(self._stepContext, 'row', None)
        with self._inputLock:
            live = self._progress.live
            live.transient = True
            self._progress.stop()
            live.transient = False
            live_render = getattr(live, '_live_render', None)
            if live_render is not None:
                # Forget the erased render, otherwise the restart would overwrite the prompt lines.
                live_render._shape = None
            try:
                if row is not None:
                    self.console.print(Text(f'[{row.name}] ', style='bold cyan'), end='')
                self.console.print(prompt, end='', markup=False, highlight=False)
                self._terminal.flush()
                line = sys.stdin.readline()
                if not line:
                    raise EOFError
                line = line.rstrip('\r\n')
                # Keep the question and the answer in the step log.
                print(f'{prompt}{line}')
                return line
            finally:
                self._progress.start()

    # ---------------------------------------------------------------- in-process steps
    def run_step(self, row: Optional[Row], func: Callable[[], object], background: bool = False):
        """Run `func` in this process with its output redirected to the row's log file."""
        if row is None:
            return None
        result = row.results[0]
        result.status = Status.RUNNING
        row.currentLog = result.log
        self._progress.start_task(row.taskId)
        self._set_row(row, Status.RUNNING, '[cyan]running (parallel)' if background else '[cyan]running')
        self._note(f'[{row.name}] started' + (' in background' if background else ''))
        start = time.perf_counter()
        error = None
        ret = None
        self._stepContext.row = row
        with OutputRedirect(result.log):
            try:
                ret = func()
            except Exception as e:
                traceback.print_exc()
                error = e
            finally:
                self._stepContext.row = None
        result.duration = time.perf_counter() - start
        row.currentLog = None
        self._progress.stop_task(row.taskId)
        if error is not None:
            result.status = Status.FAILED
            result.detail = f'{type(error).__name__}: {error}'
            self._set_row(row, Status.FAILED, '[bold red]failed')
            self._note(f'[{row.name}] FAILED')
            raise StepFailed(f'{row.name} failed: {result.detail}')
        result.status = Status.SUCCESS
        self._progress.update(row.taskId, completed=row.total)
        self._set_row(row, Status.SUCCESS, '[green]done')
        self._note(f'[{row.name}] succeeded in {format_duration(result.duration)}')
        return ret

    # ---------------------------------------------------------------- parallel builds
    def run_builds(self, jobs: list[PlatformBuildJob], cwd: str, max_workers: int):
        self.maxWorkers = max(1, max_workers)
        start = time.perf_counter()
        # Start platforms with more configurations first to shorten the overall wall time.
        ordered = sorted(jobs, key=lambda j: len(j.configs), reverse=True)
        try:
            with ThreadPoolExecutor(max_workers=self.maxWorkers, thread_name_prefix='wpe-build') as pool:
                _wait_futures([pool.submit(self._run_job_safe, job, cwd) for job in ordered])
        except BaseException:
            self._abort.set()
            self._procs.kill_all()
            raise
        finally:
            self.buildElapsed = time.perf_counter() - start
        failed = [f'{r.name}/{r.config}' for job in jobs for r in job.row.results if r.status == Status.FAILED]
        if failed:
            raise StepFailed(f'Build failed: {", ".join(failed)}')

    def _run_job_safe(self, job: PlatformBuildJob, cwd: str):
        try:
            self._run_job(job, cwd)
        except BaseException as e:
            self._abort.set()
            job.row.currentLog = None
            for r in job.row.results:
                if r.status == Status.RUNNING:
                    r.status = Status.FAILED
                    r.detail = f'{type(e).__name__}: {e}'
            self._set_row(job.row, Status.FAILED, '[bold red]error')
            raise

    def _run_job(self, job: PlatformBuildJob, cwd: str):
        row = job.row
        if self._abort.is_set():
            return
        self._progress.start_task(row.taskId)
        failed = False
        for result in row.results:
            if failed or self._abort.is_set():
                result.status = Status.SKIPPED
                continue
            result.status = Status.RUNNING
            row.currentLog = result.log
            self._set_row(row, Status.RUNNING, f'[cyan]{result.config}')
            self._note(f'[{row.name}] {result.config} started')

            start = time.perf_counter()
            returncode = run_task_process('build', job.args_for(result.config), cwd, result.log, self._procs)
            result.duration = time.perf_counter() - start

            if returncode == 0:
                result.status = Status.SUCCESS
                self._progress.advance(row.taskId)
                self._note(f'[{row.name}] {result.config} succeeded in {format_duration(result.duration)}')
            else:
                result.status = Status.FAILED
                result.detail = f'exit code {returncode}'
                failed = True
                self._abort.set()
                self._note(f'[{row.name}] {result.config} FAILED ({result.detail})')

        row.currentLog = None
        self._progress.stop_task(row.taskId)
        if failed:
            failed_cfg = next(r.config for r in row.results if r.status == Status.FAILED)
            self._set_row(row, Status.FAILED, f'[bold red]{failed_cfg} failed')
        elif any(r.status == Status.SKIPPED for r in row.results):
            self._set_row(row, Status.SKIPPED, '[yellow]aborted')
        else:
            self._set_row(row, Status.SUCCESS, '[green]done')

    # ---------------------------------------------------------------- summary
    def print_summary(self, total_elapsed: float, show_failure_logs: bool = True):
        console = self.console
        table = Table(title='Summary', title_justify='left', show_edge=False)
        table.add_column('Step', style='bold')
        table.add_column('Config')
        table.add_column('Result')
        table.add_column('Time', justify='right')
        table.add_column('Log / Detail', overflow='fold')
        for row in self.rows:
            for r in row.results:
                log = osp.basename(r.log) if r.log and osp.isfile(r.log) else ''
                detail = r.detail if r.status != Status.SUCCESS and r.detail else ''
                table.add_row(r.name, r.config, Text(r.status, style=_STATUS_STYLE[r.status]),
                              format_duration(r.duration) if r.duration else '-',
                              ' | '.join(filter(None, [log, detail])))
        console.print()
        console.print(table)

        if show_failure_logs:
            for row in self.rows:
                for r in row.results:
                    if r.status != Status.FAILED or not r.log:
                        continue
                    # The pack step failure is explained by the failed package logs, if any.
                    if row.kind == 'pack' and r is row.results[0] and \
                            any(x.status == Status.FAILED for x in row.results[1:]):
                        continue
                    title = f'{r.name} {r.config}'.strip()
                    console.print()
                    console.rule(f'[bold red]{title} failed', align='left')
                    for line in _read_log_tail(r.log)[-40:]:
                        console.print(line, markup=False, highlight=False)
                    console.print(f'Full log: {r.log}', style='red', highlight=False)

        builds = [r for row in self.rows if row.kind == 'build' for r in row.results]
        hooks = [r for row in self.rows if row.kind == 'hook' for r in row.results]
        packs = [row.results[0] for row in self.rows if row.kind == 'pack']
        package_tasks = [r for row in self.rows if row.kind == 'pack' for r in row.results[1:]]
        console.print()
        console.rule('[bold]full_pack timing', align='left')
        lines = []
        if self.buildElapsed:
            lines.append((f'Build (parallel, -j {self.maxWorkers})', format_duration(self.buildElapsed)))
            serial = sum(r.duration for r in builds)
            lines.append(('Sum of build task time',
                          f'{format_duration(serial)} (~{serial / self.buildElapsed:.2f}x speedup vs. serial)'))
        if hooks:
            lines.append(('Hooks', format_duration(sum(r.duration for r in hooks))))
        if any(r.duration for r in packs):
            lines.append(('Pack', format_duration(sum(r.duration for r in packs))))
            runner = self._packRunner
            serial = sum(r.duration for r in package_tasks)
            if runner is not None and runner.elapsed and serial:
                lines.append((f'  Packages (parallel, -j {runner.maxWorkers})', format_duration(runner.elapsed)))
                lines.append(('  Sum of package task time',
                              f'{format_duration(serial)} (~{serial / runner.elapsed:.2f}x speedup vs. serial)'))
        lines.append(('[bold]Total', f'[bold]{format_duration(total_elapsed)}'))
        width = max(len(Text.from_markup(k).plain) for k, _ in lines)
        for k, v in lines:
            pad = ' ' * (width - len(Text.from_markup(k).plain))
            console.print(f'  {k}{pad} : {v}', highlight=False)
        console.print()
        for k, v in self.extraInfo:
            console.print(f'{k}: {v}', highlight=False)
        console.print(f'Logs: {self.logDir}', highlight=False)


class BackgroundStep:
    """An in-process step (hook) running in a background thread alongside out-of-process steps."""

    def __init__(self, dashboard: FullPackDashboard, row: Row, func: Callable[[], object]):
        self.dashboard = dashboard
        self.row = row
        self.func = func
        self.error: Optional[StepFailed] = None
        # Daemon: an interrupted full-pack must not hang on exit waiting for a remote call.
        self.thread = threading.Thread(target=self._run, name=f'wpe-{row.name}', daemon=True)

    def _run(self):
        try:
            self.dashboard.run_step(self.row, self.func, background=True)
        except StepFailed as e:
            self.error = e
        except BaseException as e:
            self.error = StepFailed(f'{self.row.name} failed: {type(e).__name__}: {e}')

    def start(self):
        self.thread.start()
        return self

    def join(self):
        # Short timeout keeps the main thread responsive to Ctrl+C.
        while self.thread.is_alive():
            self.thread.join(0.2)
        if self.error:
            raise self.error


@dataclass
class PipelineStep:
    kind: str  # 'hook' | 'build' | 'pack'
    row: Optional[Row]  # None: hook not present (skipped) / build step without own row
    func: Callable[[], object]
    # Only for hooks: step kinds this hook may run in parallel with (see PARALLELIZABLE_STEP_KINDS).
    parallelWith: frozenset = frozenset()


def run_pipeline(dashboard: FullPackDashboard, steps: list[PipelineStep]):
    """
    Run steps in order.
    A hook declaring `parallelWith` is deferred until the first step it may overlap with, then runs in a
    background thread; it is joined before any step it may not overlap with.
    In-process steps never overlap each other, because they share the process-wide output redirection.
    On failure, waits for running background hooks, then raises the first StepFailed.
    """
    deferred: list[PipelineStep] = []
    running: list[tuple[PipelineStep, BackgroundStep]] = []
    errors: list[StepFailed] = []

    def join(predicate):
        for item in [r for r in running if predicate(r[0])]:
            running.remove(item)
            try:
                item[1].join()
            except StepFailed as e:
                errors.append(e)

    def run_deferred(predicate):
        for d in [d for d in deferred if predicate(d)]:
            deferred.remove(d)
            join(lambda _: True)
            dashboard.run_step(d.row, d.func)

    try:
        for index, step in enumerate(steps):
            later_kinds = {s.kind for s in steps[index:]}
            if step.kind != 'build' and step.row is None:
                continue
            if step.parallelWith:
                deferred.append(step)
                continue
            if step.kind in PARALLELIZABLE_STEP_KINDS:
                run_deferred(lambda d: step.kind not in d.parallelWith)
                join(lambda s: step.kind not in s.parallelWith)
                for d in [d for d in deferred if step.kind in d.parallelWith]:
                    deferred.remove(d)
                    running.append((d, BackgroundStep(dashboard, d.row, d.func).start()))
            else:
                join(lambda _: True)
                # Keep deferring hooks that can still overlap with a later step; run the others now.
                run_deferred(lambda d: not (d.parallelWith & later_kinds))
            if errors:
                break
            if step.row is None:
                step.func()
            else:
                dashboard.run_step(step.row, step.func)
        if not errors:
            join(lambda _: True)
            run_deferred(lambda _: True)
    except StepFailed as e:
        errors.insert(0, e)
        join(lambda _: True)
    if errors:
        raise errors[0]
