# wp-enhanced
Wrapper of `wp.py`. Easy to premake, build, deploy and distribute wwise plugins.

# Installation
1. Install wpe from pip
    ```
    pip install wp-enhanced
    ```
2. Set wwise environment variables
    - Windows:
        - Set from Wwise Launcher
    
        ![image](https://github.com/user-attachments/assets/624e498d-1f86-4839-9469-a7106e60a6fc)

    - MacOS:
        - Set `WWISEROOT` and `WWISESDK` manually
    
3. Check installation
    ```
    wpe -h
    ```

# Start to create your plugin
> The following mentioned `wpe` command line parameters will use shorter subcommands aliases. For the full subcommands name, you can view them by running `wpe -h`.
> 
> Run `wpe <SUBCOMMAND> -h` to view the help message of each subcommand.

## Create new plugin project
Run `wpe n` to create new project just like original `python wp.py new`.

After creating new project, you can find `.wpe` directory in your project root which is created by wpe. The directory structure should be like:
```
./.wpe
|-- hooks
|   |-- post_build.py
|   |-- post_full_pack.py
|   `-- pre_premake.py
`-- wpe_project.toml
```
- `wpe_project.toml`: wpe project configuration file.
- `hooks`: hooks for specific wpe actions. Refer to [Hooks](#hooks) for more information.

## Configure project
Head to `$PROJECT_ROOT/.wpe/wpe_project.toml`, the project configuration can is divided into four parts.

### Version
Determine the version of plugin, which affects packing the plugin archive.

You can bump plugin version by running `wpe B`
```toml
[project]
version = 1
```

### Platform support 
Defines the supported platforms when using Premake to build the plugin.

`win_targets`/`mac_targets` means your develop machine platform. e.g. In default configuration, when developing on Windows, you can build for Windows Authoring, Windows_vc160, Android.
> Currently developing on Windows is recommended, as MacOS authoring plugin is not supported yet.
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

### Plugin info
- `MenuPath`: Plugins with the same menu path will be grouped in the Wwise plugin popup menu.
- `platform_support`: Inform Wwise Authoring where this plugin can be inserted and whether it can be rendered offline.
```toml
[plugin_info]
MenuPath = 'custom'

[plugin_info.platform_support.Any]
CanBeInsertOnBusses = true
CanBeInsertOnAudioObjects = true
CanBeRendered = true
```

### Parameters
The initially generated configuration contains several typical parameter definition examples.
- [wpe_project.toml](src%2Fwpe%2Ftemplates%2F.wpe%2Fwpe_project.toml)

Run `wpe gp` to generate parameters code.

Be careful the followed files will be **overwritten** by template if `[wp-enhanced template]` comment is not found in file:
 - [ProjectNameFXParams.cpp](src%2Fwpe%2Ftemplates%2FSoundEnginePlugin%2FProjectNameFXParams.cpp)
 - [ProjectNameFXParams.h](src%2Fwpe%2Ftemplates%2FSoundEnginePlugin%2FProjectNameFXParams.h)
 - [ProjectName.xml](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectName.xml)
 - [ProjectNamePlugin.cpp](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectNamePlugin.cpp)
 - [ProjectNamePlugin.h](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectNamePlugin.h)

if `-gui` flag is set: 
 - [ProjectNamePluginGUI.cpp](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FWin32%2FProjectNamePluginGUI.cpp)
 - [ProjectNamePluginGUI.h](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FWin32%2FProjectNamePluginGUI.h)
 - [resource.h](src%2Fwpe%2Ftemplates%2FWwisePlugin%2Fresource.h)
 - [ProjectName.rc](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectName.rc)

New plugin project will be created with default parameters: [wpe_project.toml](src%2Fwpe%2Ftemplates%2F.wpe%2Fwpe_parameters.toml)


## Premake
Run `wpe p`. Default to premake all platforms defined in targets. You can also specify platforms by `-plt` flag.

## Build
Run `wpe b`. Default to build all platforms defined in targets with Debug config. You can also specify platforms by `-plt` flag, and specify config by `-c` flag.

## Pack
Run `wpe P` to package plugin. This will collect the build artifacts for all local platforms and generate the plugin archive in the `dist` directory.
> Will NOT build plugin. If you need to fully build plugin and package it for distribution, try `wpe FP`

## Deploy
After package your plugin into an archive, you can run `wpe d` to deploy it to different places.

Currently supported:
- Pass WwiseRoot to `-d` argument to deploy to Wwise Authoring.
- Pass Wwise integrated UE project root to `-d` argument to deploy to UE project.


## Hooks
All hooks should be placed in `$PROJECT_ROOT/.wpe/hooks` folder. 

`pre`/`post`_`premake`/`generate_parameters`/`build`/`pack`/`full_pack` are supported.

Hook scripts should contain a `main` function with `**kwargs`, the followed arguments are passed by wpe:
- `proj_root`: project root directory
- `plugin_name`
- subcommand args. For example, build command will pass `platforms` and `configuration`.

Some default are created when creating new project, you can modify them or add new hooks.

For more information about hooks, please refer to description of `-H, --with-hooks` in `wpe -h`

# Integrate wpe to existing project
If your have existing project, you can integrate wpe to it by running `wpe i` in your project root.

**CAUTION ❗❗**: Make sure to stage your modified files before running `wpe i`, as the parameters code generation may overwrite your files.
