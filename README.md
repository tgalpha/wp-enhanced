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
    
        ![image](https://user-images.githubusercontent.com/61353126/228009337-742b294a-a453-4134-9b3d-ed7c09f13049.png)
    - MacOS:
        - Set `WWISEROOT` and `WWISESDK` manually
    
3. Check installation
    ```
    wpe -h
    ```

# Create new plugin project
Run `wpe -n` to create new project like original wp.py, but with some additional features.

## Parameters code generation
You can define parameters in `$PROJECT_ROOT/.wpe/wpe_project.toml` and generate code for them by running `wpe -gp`.

Be careful the followed files will be **overwritten** by template if `[wp-enhanced template]` is not found in file:
 - [ProjectNameFXParams.cpp](src%2Fwpe%2Ftemplates%2FSoundEnginePlugin%2FProjectNameFXParams.cpp)
 - [ProjectNameFXParams.h](src%2Fwpe%2Ftemplates%2FSoundEnginePlugin%2FProjectNameFXParams.h)
 - [ProjectName.xml](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectName.xml)
 - [ProjectNamePlugin.cpp](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectNamePlugin.cpp)
 - [ProjectNamePlugin.h](src%2Fwpe%2Ftemplates%2FWwisePlugin%2FProjectNamePlugin.h)

New plugin project will be created with default parameters: [wpe_project.toml](src%2Fwpe%2Ftemplates%2F.wpe%2Fwpe_parameters.toml)


## Hooks
All hooks should be placed in `$PROJECT_ROOT/.wpe/hooks` folder. 

`pre`/`post`_`premake`/`generate_parameters`/`build`/`pack`/`full_pack` are supported.

A default `post_build.py` is created when creating new project, which will copy debug authoring plugin to Release folder for loading in Wwise Authoring.

For more information about hooks, please refer to description of `-H, --with-hooks` in `wpe -h`

# Add wpe to existing project
Run `wpe -i` under project root.