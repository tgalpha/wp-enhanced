import argparse
import sys

from wpe import core
from wpe.util import generate_integrated_description


def add_platform_arg(parser):
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


def add_deploy_parser(subparsers):
    subparser = subparsers.add_parser(
        'deploy',
        aliases=['d'],
        description='Deploy plugin to game project.',
    )
    subparser.add_argument(
        '-a',
        '--archive',
        type=str,
        dest='archive',
        required=False,
        default='',
        help='Plugin installer archive path. leave empty to use recent pack.'
    )
    subparser.add_argument(
        '-d',
        '--dest-project',
        type=str,
        dest='destProject',
        required=True,
        default='',
        help='Destination project root path. current supported: Authoring, Unreal'
    )
    subparser.set_defaults(func=core.deploy)


def add_clean_parser(subparsers):
    subparser = subparsers.add_parser(
        'clean',
        aliases=['c'],
        description='Clean deployed plugin in game project.'
    )
    subparser.add_argument(
        '-n',
        '--name',
        type=str,
        dest='name',
        required=False,
        default='',
        help='Plugin name to clean. leave empty to use current plugin project name.'
    )
    subparser.add_argument(
        '-d',
        '--dest-project',
        type=str,
        dest='destProject',
        required=True,
        default='',
        help='Destination project root path.'
    )
    subparser.set_defaults(func=core.clean)


def add_build_agent_parser(subparsers):
    subparser = subparsers.add_parser(
        'build-agent',
        aliases=['ba'],
        description='Start a build agent on current machine. Run build command through ssh to build for iOS will fail with permission issue. So we need to start a build agent process on target machine to handle build command.'
    )
    subparser.add_argument(
        '-p',
        '--port',
        type=int,
        dest='port',
        required=False,
        default=5000,
        help='Port to run the build agent on.'
    )
    subparser.set_defaults(func=core.start_build_agent)


def add_config_parser(subparsers):
    def add_key_value_args(parser):
        parser.add_argument(
            'key',
            type=str,
            default='',
            help='Setting key.'
        )
        parser.add_argument(
            'value',
            type=str,
            default='',
            help='Setting value.'
        )

    subparser = subparsers.add_parser(
        'config',
        description='Manages configuration settings.'
    )
    subparser.add_argument(
        '-l',
        '--list',
        action='store_true',
        dest='list',
        default=False,
        required=False,
        help='List all configuration settings.'
    )

    if '-h' in sys.argv or not subparser.parse_known_args()[0].list:
        add_key_value_args(subparser)

    subparser.set_defaults(func=core.config)


def add_wp_parser(subparsers):
    subparser = subparsers.add_parser(
        'wp',
        description='Pass arguments to wp.py. Example: wp new'
    )
    subparser.add_argument(
        'wpArgs',
        type=str,
        nargs='+',
        default=[],
        help='Arguments passed to wp.py'
    )
    subparser.set_defaults(func=core.wp)


def add_new_parser(subparsers):
    subparser = subparsers.add_parser(
        'new',
        aliases=['n'],
        description='Create a new plugin project. Will auto init wpe config.'
    )
    subparser.set_defaults(func=core.new)


def add_init_wpe_parser(subparsers):
    subparser = subparsers.add_parser(
        'init-wpe',
        aliases=['i'],
        description='Initialize wpe project config for existing plugin project.'
    )
    subparser.set_defaults(func=core.init_wpe)


def add_premake_parser(subparsers):
    subparser = subparsers.add_parser(
        'premake',
        aliases=['p'],
        description='Premake project.'
    )
    add_platform_arg(subparser)
    subparser.set_defaults(func=core.premake)


def add_generate_parameters_parser(subparsers):
    subparser = subparsers.add_parser(
        'generate-parameters',
        aliases=['gp'],
        description='Generate source code with parameters. Define parameters in `$PROJECT_ROOT/.wpe/wpe_parameters.toml`.'
    )
    subparser.add_argument(
        '-f',
        '--force',
        action='store_true',
        dest='force',
        required=False,
        default=False,
        help='Force operation. This argument is compatible with -gp, will overwrite existing source files.'
    )
    subparser.add_argument(
        '-g',
        '--gui',
        action='store_true',
        dest='gui',
        required=False,
        default=False,
        help='Effective when -gp is specified. Generate GUI resources.'
    )
    subparser.set_defaults(func=core.generate_parameters)


def add_build_parser(subparsers):
    subparser = subparsers.add_parser(
        'build',
        aliases=['b'],
        description='Build project.'
    )
    add_platform_arg(subparser)
    subparser.add_argument(
        '-c',
        '--configuration',
        action='store',
        choices=('Debug', 'Profile', 'Release'),
        dest='configuration',
        default='Debug',
        required=False,
        help='Configuration to build (Debug, Release, Profile). Default value is Debug.'
    )
    subparser.set_defaults(func=core.build)


def add_test_parser(subparsers):
    subparser = subparsers.add_parser(
        'test',
        aliases=['t'],
        description='Test plugin with catch2 framework.'
    )
    subparser.set_defaults(func=core.test)


def add_pack_parser(subparsers):
    subparser = subparsers.add_parser(
        'pack',
        aliases=['P'],
        description='Package plugin.'
    )
    subparser.set_defaults(func=core.pack)


def add_full_pack_parser(subparsers):
    subparser = subparsers.add_parser(
        'full-pack',
        aliases=['FP'],
        description='Build for all platform and pack.'
    )
    subparser.set_defaults(func=core.full_pack)


def add_bump_parser(subparsers):
    subparser = subparsers.add_parser(
        'bump',
        aliases=['B'],
        description='Bump wpe project version.'
    )
    subparser.set_defaults(func=core.bump)


def add_rename_parser(subparsers):
    subparser = subparsers.add_parser(
        'rename',
        aliases=['r'],
        description='Rename plugin.'
    )
    subparser.add_argument(
        '-n'
        '--new-name',
        action='store',
        type=str,
        dest='newName',
        default='',
        required=False,
        help='New plugin name.'
    )
    subparser.set_defaults(func=core.rename)


def add_jetbrains_run_config_parser(subparsers):
    subparser = subparsers.add_parser(
        'add-jetbrains-run-config',
        aliases=['ar'],
        description='Add JetBrains run configuration for debugging with Wwise Authoring.'
    )
    subparser.set_defaults(func=core.add_jetbrains_run_config)


def main(args=None):
    parser = argparse.ArgumentParser(
        prog='wpe',
        epilog='Wrapper of `wp.py`. Easy to premake, build, deploy and distribute wwise plugins.',
        formatter_class=argparse.RawTextHelpFormatter
    )

    subparsers = parser.add_subparsers(title='subcommands')
    add_wp_parser(subparsers)
    add_new_parser(subparsers)
    add_init_wpe_parser(subparsers)
    add_premake_parser(subparsers)
    add_generate_parameters_parser(subparsers)
    add_build_parser(subparsers)
    add_test_parser(subparsers)
    add_pack_parser(subparsers)
    add_full_pack_parser(subparsers)
    add_bump_parser(subparsers)
    add_rename_parser(subparsers)
    add_deploy_parser(subparsers)
    add_clean_parser(subparsers)
    add_build_agent_parser(subparsers)
    add_config_parser(subparsers)
    add_jetbrains_run_config_parser(subparsers)

    generate_integrated_description(parser, subparsers)

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
  - plugin_name: plugin name, which is used to glob plugin files'''
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

    parsed_args, remains = parser.parse_known_args(args)
    # parse global args (withHooks, root)
    seconds_args = parser.parse_args(remains)
    parsed_args.__dict__.update(seconds_args.__dict__)
    parsed_args.func(parsed_args)


if __name__ == '__main__':
    main()
