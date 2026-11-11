"""
Run a single wp.py `build` or `package` task in its own process.

Usage: python -m wpe.build_task [build|package] <wp.py args>
(the task kind defaults to `build` when omitted)

wp.py mutates process-wide state while running (platform registry, environment variables,
working directory), so `wpe full-pack` / `wpe pack` run each task in a separate process to be
able to run them in parallel.
"""
import sys
import traceback

TASK_KINDS = ('build', 'package')


def main(argv):
    # Same import order as the CLI: importing wpe.wp_wrapper first triggers a circular import.
    import wpe.util  # noqa: F401
    from wpe.wp_wrapper import WpWrapper
    kind, args = (argv[0], argv[1:]) if argv and argv[0] in TASK_KINDS else ('build', argv)
    try:
        if kind == 'build':
            WpWrapper().build(*args)
            return 0
        res = WpWrapper().package(*args)
        return res if isinstance(res, int) else 0
    except SystemExit as e:
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        print(e.code, file=sys.stderr)
        return 1
    except BaseException:
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
