# wp-enhanced
Wrapper of `wp.py`. Easy to premake, build, and deploy wwise plugins.

# Installation
1. Install wpe from pip
    ```
    pip install wp-enhanced
    ```
2. Set environment variables from wwise launcher
3. Check installation
    ```
    wpe -h
    usage: Plugin dev ci build tool [-h] [--wp [WP ...]] [-n] [-p] [-b] [-c {Debug,Profile,Release}] [-f] [-C] [-l]
                                    [-d DELETEDEPLOYTARGET] [--enable-cpp17]
    
    optional arguments:
      -h, --help            show this help message and exit
      --wp [WP ...]         Pass arguments to wp.py. Example: --wp new
      -n, --new             Create a new plugin project.
      -p, --premake         Premake authoring project.
      -b, --build           Build project.
      -c {Debug,Profile,Release}, --configuration {Debug,Profile,Release}
                            Configuration to build (Debug, Release, Profile). Default value is Debug.
      -f, --force-copy-file
                            Terminate Wwise process and copy plugin files, then reopen Wwise.
      -C, --create-deploy-target
                            Create a new deploy target with interactive commandline.
      -l, --list-deploy-targets
                            List all deploy targets.
      -d DELETEDEPLOYTARGET, --delete-deploy-target DELETEDEPLOYTARGET
                            Delete deploy targets by name.
      --enable-cpp17        Change premake cppdialect to c++17 in global premakePlugin.lua. Will leave a backup file in the same directory(%WWISEROOT%\Scripts\Build\Plugins).
    
    Wrapper of `wp.py`. Easy to premake, build, and deploy wwise plugins.
    ```

# Usage
