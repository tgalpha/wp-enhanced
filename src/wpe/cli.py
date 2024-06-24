import argparse

from wpe.core import Worker


def main():
    parser = argparse.ArgumentParser(
        prog='Plugin dev ci build tool',
        add_help=True,
        epilog='Wrapper of `wp.py`. Easy to premake, build, deploy and distribute wwise plugins.',
        formatter_class=argparse.RawTextHelpFormatter
    )

    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument(
        '--wp',
        action='store',
        dest='wp',
        nargs='*',
        default=[],
        required=False,
        help='Pass arguments to wp.py. Example: --wp new'
    )

    command_group.add_argument(
        '-n',
        '--new',
        action='store_true',
        dest='new',
        default=False,
        required=False,
        help='Create a new plugin project. Will auto init wpe config.'
    )

    command_group.add_argument(
        '-i',
        '--init-wpe',
        action='store_true',
        dest='initWpe',
        default=False,
        required=False,
        help='Initialize wpe project config for existing plugin project.'
    )

    command_group.add_argument(
        '-p',
        '--premake',
        action='store_true',
        dest='premake',
        default=False,
        required=False,
        help='Premake authoring project.'
    )

    command_group.add_argument(
        '-gp',
        '--generate-parameters',
        action='store_true',
        dest='generateParameters',
        default=False,
        required=False,
        help='Generate source code with parameters. Define parameters in `$PROJECT_ROOT/.wpe/wpe_parameters.toml`.'
    )

    command_group.add_argument(
        '-b',
        '--build',
        action='store_true',
        dest='build',
        default=False,
        required=False,
        help='Build project.'
    )

    command_group.add_argument(
        '-t',
        '--test',
        action='store_true',
        dest='test',
        default=False,
        required=False,
        help='Test plugin with catch2 framework.'
    )

    command_group.add_argument(
        '-P',
        '--pack',
        action='store_true',
        dest='pack',
        default=False,
        required=False,
        help='Package plugin.'
    )

    command_group.add_argument(
        '-FP',
        '--full-pack',
        action='store_true',
        dest='fullPack',
        default=False,
        required=False,
        help='Build Release&Profile for all platform and pack.'
    )

    command_group.add_argument(
        '--bump',
        action='store_true',
        dest='bump',
        default=False,
        required=False,
        help='Bump wpe project version.'
    )

    command_group.add_argument(
        '--rename',
        action='store',
        type=str,
        dest='rename',
        default='',
        required=False,
        help='Rename plugin.'
    )

    command_group.add_argument(
        '-ar',
        '--add-jetbrains-run-config',
        action='store_true',
        dest='addJetBrainsRunConfig',
        default=False,
        required=False,
        help='Add JetBrains run configuration for debugging with Wwise Authoring.'
    )

    parser.add_argument(
        '-H',
        '--with-hooks',
        action='store',
        dest='withHooks',
        nargs='*',
        default=[],
        help='''Execute command with hooks. You can specify hooks to execute. e.g. -H pre_build post_build. leave empty to execute all hooks.
Hooks should:
- be placed in `$PROJECT_ROOT/.wpe/hooks` with name `pre_<command>.py` or `post_<command>.py`.
  - supported commands: `premake`, `generate_parameters`, `build`, `pack`
- define a function with name `main`, accept followed arguments (or use `**kwargs`):
  - proj_root: project root path
  - build_config: build configuration (Debug, Profile, Release)
  - plugin_name: plugin name, which is used to glob plugin files'''
    )

    parser.add_argument(
        '-plt',
        '--platforms',
        action='store',
        choices=['Android', 'Authoring', 'Authoring_Windows', 'Authoring_Linux', 'Authoring_Mac', 'iOS', 'Linux',
                 'LinuxAuto', 'Mac', 'NX', 'PS4', 'PS5', 'QNX', 'tvOS', 'Windows_vc140', 'Windows_vc150',
                 'Windows_vc160', 'Windows_vc170', 'WinGC', 'XboxOneGC', 'XboxSeriesX'],
        dest='platforms',
        default=[],
        nargs='*',
        required=False,
        help='Platforms to premake/build. Leave empty to premake/build all platforms defined in `wpe_project.toml`.'
    )
    parser.add_argument(
        '-c',
        '--configuration',
        action='store',
        choices=('Debug', 'Profile', 'Release'),
        dest='configuration',
        default='Debug',
        required=False,
        help='Configuration to build (Debug, Release, Profile). Default value is Debug.'
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        dest='force',
        required=False,
        default=False,
        help='''Force operation. This argument is compatible with -gp or -b.
    For -gp, it will overwrite existing source files.
    For -b, it will terminate Wwise process and copy plugin files, then reopen Wwise.'''
    )
    parser.add_argument(
        '-g',
        '--gui',
        action='store_true',
        dest='gui',
        required=False,
        default=False,
        help='Effective when -gp is specified. Generate GUI resources.'
    )
    parser.add_argument(
        '-r',
        '--root',
        type=str,
        action='store',
        dest='root',
        required=False,
        default='',
        help='Project root path. Default value is current working directory.'
    )

    parsed_args = parser.parse_args()
    worker = Worker.create_platform(parsed_args)
    worker.main()


if __name__ == '__main__':
    main()
