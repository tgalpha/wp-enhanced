# wp-enhanced

A wrapper around the Wwise `wp.py` helper that streamlines Premake, builds, packaging, deployment, and distribution of Wwise plug-ins.

**Requirements:** Python 3.9+, Wwise SDK with `WWISEROOT` / `WWISESDK` set (see below).

---

## Install

1. **Install the CLI**

   ```bash
   pip install wp-enhanced
   ```

2. **Environment variables**

   - **Windows:** set `WWISEROOT` and `WWISESDK` via Wwise Launcher (or manually).

     ![Wwise environment from Launcher](https://github.com/user-attachments/assets/624e498d-1f86-4839-9469-a7106e60a6fc)

   - **macOS:** set `WWISEROOT` and `WWISESDK` manually.

3. **Verify**

   ```bash
   wpe -h
   ```

Subcommands are often shown as short aliases (e.g. `wpe n`). Run `wpe -h` for full names and `wpe <subcommand> -h` for per-command help.

---

## New project

Create a project (equivalent to `python wp.py new`):

```bash
wpe n
```

This creates a `.wpe` directory at the project root:

```text
.wpe/
├── hooks/
│   ├── post_build.py
│   ├── pre_full_pack.py
│   └── pre_premake.py
└── wpe_project.toml
```

- **`wpe_project.toml`** — project settings for wp-enhanced.
- **`hooks/`** — optional scripts for build lifecycle steps (see [Hooks](#hooks)).

---

## Configure the project

Edit `$PROJECT_ROOT/.wpe/wpe_project.toml`. Configuration is grouped into: **version**, **platform targets**, **plug-in info**, and **parameters**.

### Version

Used when packaging the plug-in archive. Bump with:

```bash
wpe B
```

```toml
[project]
version = 1
```

### Platform targets

Controls which platforms Premake / builds target. Use `win_targets` on Windows and `mac_targets` on macOS.

Developing on **Windows** is recommended; macOS Authoring plug-ins are not supported in the same way.

```toml
[project]
version = 1
win_targets = [
    { platform = 'Authoring', architectures = ['x64'], toolset = 'vc160' },
    { platform = 'Windows_vc160', architectures = ['x64'] },
    { platform = 'Android', architectures = ['arm64-v8a', 'armeabi-v7a'] },
]
mac_targets = [
    { platform = 'iOS', architectures = ['iOS'] },
]
```

### Plug-in info

- **`MenuPath`** — groups plug-ins under the same path in the Wwise UI.
- **`platform_support`** — tells Wwise Authoring where the effect can be inserted and if it can be rendered offline.

```toml
[plugin_info]
MenuPath = 'custom'

[plugin_info.platform_support.Any]
CanBeInsertOnBusses = true
CanBeInsertOnAudioObjects = true
CanBeRendered = true
```

### Parameters

The generated config includes example parameter definitions. Reference template:

- [`src/wpe/templates/.wpe/wpe_project.toml`](src/wpe/templates/.wpe/wpe_project.toml)

Generate code from parameters:

```bash
wpe gp
```

**Overwrite behavior:** if a file does **not** contain the marker `[wp-enhanced template]`, `wpe gp` may overwrite it from templates. Typical paths:

| Scope | Files |
|--------|--------|
| Core | `ProjectNameFXParams.cpp`, `ProjectNameFXParams.h`, `ProjectName.xml`, `ProjectNamePlugin.cpp`, `ProjectNamePlugin.h` |
| With `-g` / `--gui` | `ProjectNamePluginGUI.cpp`, `ProjectNamePluginGUI.h`, `resource.h`, `ProjectName.rc` |

Default parameter examples for new projects:

- [`src/wpe/templates/.wpe/wpe_parameters.toml`](src/wpe/templates/.wpe/wpe_parameters.toml)

---

## Common commands

| Action | Command | Notes |
|--------|---------|--------|
| Premake | `wpe p` | All targets from config, or restrict with `-plt` |
| Build | `wpe b` | Default **Debug**; use `-c` for configuration, `-plt` for platforms |
| Pack | `wpe P` | Collects artifacts into `dist/`; **does not build** |
| Full pack | `wpe FP` | Build (including Release-style full pack flow) then pack for distribution |
| Deploy | `wpe d` | Deploy a packaged archive (see below) |

### Deploy

After packaging:

```bash
wpe d -d <destination>
```

- **Wwise Authoring:** pass the Wwise installation root (e.g. directory containing `Authoring/.../Wwise.exe`).
- **Unreal (Wwise integrated):** pass the UE project root (folder containing `.uproject`).

Use `-a` / `--archive` to point at a specific `.zip`; if omitted, a recent archive under `dist/` is used.

---

## Hooks

Place scripts under `$PROJECT_ROOT/.wpe/hooks/`. Name files `pre_<command>.py` or `post_<command>.py`, where `<command>` matches the action (e.g. `premake`, `generate_parameters`, `build`, `pack`, `full_pack`; also `test`, `bump`, `rename`, `deploy` when those commands are used).

Each script should define `main(**kwargs)`. wp-enhanced passes at least:

- `proj_root` — project root path  
- `plugin_name` — plug-in name  

Additional keys depend on the command (e.g. build passes `platforms`, `configuration`).

Default hook stubs are created with `wpe n`. See also `-H` / `--with-hooks` in `wpe -h`.

---

## Integrate into an existing project

From the plug-in project root:

```bash
wpe i
```

**Caution:** commit or stash your work first. Parameter generation may overwrite files if the `[wp-enhanced template]` guard is missing.
