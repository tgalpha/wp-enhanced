---
name: wpe-cli-workflow
description: >-
  Verifies wp-enhanced (`wpe` CLI) installation, installs from PyPI or editable
  source when missing, validates Wwise environment variables, runs wpe from the
  correct working directory, and documents the build-agent HTTP API for remote
  premake/build on another host (e.g. iOS on a Mac). Use when the user or task
  involves wpe, wp-enhanced, Wwise plugin workflows, remote builds, build-agent,
  or when shell commands fail with wpe not found or WWISEROOT/WWISESDK errors.
---

# wp-enhanced (`wpe`) CLI workflow

## When to apply

Use this workflow before running Premake, build, pack, or other `wpe` subcommands for a Wwise plug-in project.

## Preconditions

- **Python:** 3.9 or newer (package `wp-enhanced` requires `^3.9`).
- **Working directory:** Commands that need project context must run from the plug-in tree that contains `PremakePlugin.lua` (wp-enhanced walks ancestors to find it and sets `cwd` to that root).

---

## 1. Check whether `wpe` is available

Run one of the following (agent should execute, not only suggest):

```bash
wpe -h
```

**Success:** stdout shows `wpe` usage and subcommands (exit code 0).

**Failure:** `command not found`, `'wpe' is not recognized`, or similar → treat as not installed or not on `PATH`.

Optional cross-checks:

```bash
python -m pip show wp-enhanced
```

```bash
python -c "import wpe.cli; print('ok')"
```

If `pip show` finds the package but `wpe` fails, the Scripts / bin directory of that Python environment is likely not on `PATH`. Prefer invoking via the same interpreter:

```bash
python -m wpe.cli -h
```

(Only works if `wpe` is installed in that environment and `wpe.cli` is importable.)

---

## 2. Install or repair `wpe`

### Standard install (users / CI)

Use the same Python that should own the CLI:

```bash
python -m pip install --upgrade wp-enhanced
```

Then re-check step 1 with `wpe -h`.

### Editable install (developing this repository)

From the `wp-enhanced` repo root:

```bash
python -m pip install -e .
```

Or with Poetry:

```bash
poetry install
poetry run wpe -h
```

Prefer `poetry run wpe ...` inside the project so the venv and `PATH` stay consistent.

**Without installing the package** (quick dev check from repo clone only):

```bash
# POSIX
PYTHONPATH=src python -m wpe.cli -h

# PowerShell
$env:PYTHONPATH = "src"; python -m wpe.cli -h
```

### Policy for agents

- If `wpe` is missing and the user did not forbid network installs → run `python -m pip install wp-enhanced` (or `pip install -e .` when working inside the wp-enhanced source tree).
- If install fails (permissions, offline) → report the error and ask whether to use a venv, a different Python, or manual install.
- After install, always re-run `wpe -h` (or `poetry run wpe -h`) to confirm.

---

## 3. Wwise environment (`WWISEROOT`, `WWISESDK`)

Many operations (anything that loads `WpWrapper` and calls into Wwise `wp.py`) **require**:

- `WWISEROOT` — Wwise installation root  
- `WWISESDK` — Wwise SDK root  

**Check:**

```bash
# POSIX
test -n "$WWISEROOT" && test -n "$WWISESDK" && echo "ok"

# PowerShell
if ($env:WWISEROOT -and $env:WWISESDK) { "ok" }
```

On Windows, users often set these via **Wwise Launcher**.

If variables are unset:

1. Tell the user they must install Wwise and set `WWISEROOT` / `WWISESDK` (or use Launcher).
2. Do not pretend premake/build against Wwise will succeed without them.

Purely local actions that never import `WpWrapper` are rare for typical `wpe` flows; assume env is required unless the specific subcommand is known not to touch Wwise.

---

## 4. Run `wpe` correctly

| Situation | Command pattern |
|-----------|-----------------|
| Global pip install | `wpe <subcommand> ...` from plug-in root (or any path under it; `PathMan` finds `PremakePlugin.lua`). |
| Poetry in wp-enhanced repo | `poetry run wpe ...` from repo root. |
| `wpe` not on PATH | `python -m wpe.cli ...` using the env where the package is installed. |

Global options (see `wpe -h`):

- `-r` / `--root` — project root if not using cwd discovery  
- `-H` / `--with-hooks` — which hooks to run  

---

## 5. Build agent (remote machine)

**Purpose:** Run `wpe p` / `wpe b` on a **second machine** that holds the repo checkout and toolchain (common for **iOS** builds on macOS while developing on Windows). The agent is a Flask app started by the `wpe` CLI; clients call it over HTTP instead of chaining SSH invocations of `wpe`.

**Start on the build host** (must have `wpe`, `WWISEROOT`, `WWISESDK`, and Git):

```bash
wpe ba
# alias: wpe build-agent
# optional: wpe ba -p <port>   # default 5000
```

Listens on `0.0.0.0:<port>`. No auth — use only on trusted networks or tunnel/VPN.

**Endpoints** — `POST` only, JSON body, `Content-Type: application/json`:

| Path | JSON fields | Shell equivalent on agent |
|------|-------------|-----------------------------|
| `/git_sync` | `root`, `branch` | `git fetch` + `reset --hard origin/<branch>` in `root` |
| `/premake` | `root`, `platform` | `wpe p -r <root> -plt <platform>` |
| `/build` | `root`, `platform`, `configuration` | `wpe b -r <root> -c <configuration> -plt <platform>` |

**Checklist for the build machine:**

- [ ] Same `wpe` / Python env as expected for CI or manual use  
- [ ] `WWISEROOT` and `WWISESDK` set (Wwise installed)  
- [ ] Git repo at `root` with `PremakePlugin.lua`  
- [ ] Caller’s port matches hook/script (template uses `:5000` unless you change both sides)

**Reference implementation:** `.wpe/hooks/pre_full_pack.py` in new projects (from [`src/wpe/templates/.wpe/hooks/pre_full_pack.py`](../../../src/wpe/templates/.wpe/hooks/pre_full_pack.py)) — optional remote iOS flow via `requests.post` to `http://<host>:5000/...` plus `scp` of artifacts. Align `5000` with `wpe ba -p` if you change the port.

---

## 6. Quick validation checklist

Copy for tasks that need a green path:

```
- [ ] `wpe -h` succeeds (or `poetry run wpe -h` / `python -m wpe.cli -h`)
- [ ] Current directory is under the plug-in that contains PremakePlugin.lua (or pass `-r`)
- [ ] `WWISEROOT` and `WWISESDK` set when running premake/build/pack/deploy flows
```

---

## 7. Common failures

| Symptom | Likely cause |
|---------|----------------|
| `FileNotFoundError: PremakePlugin.lua` | Not under a Wwise plug-in tree; `cd` to project root or use `-r`. |
| `EnvironmentError: Unknown env variable: WWISEROOT` | Wwise env not configured. |
| `wpe` not found but pip shows `wp-enhanced` | Scripts dir not on PATH; use `python -m pip install` env’s `python -m wpe.cli` or fix PATH. |
| Wrong Python / stale code | Multiple Pythons; use `where python` / `which python` and one venv consistently. |

---

## 8. Reference

- Project README: [README.md](../../../README.md) (from this skill folder, repo root).
- PyPI package name: `wp-enhanced`; console script: `wpe`.
