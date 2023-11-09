import argparse

from wpe.core import Worker


def main():
    parser = argparse.ArgumentParser(
        prog='Plugin dev ci build tool',
        add_help=True,
        epilog='Wrapper of `wp.py`. Easy to premake, build, and deploy wwise plugins.',
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
        help='Create a new plugin project.'
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
        '-P',
        '--pack',
        action='store_true',
        dest='pack',
        default=False,
        required=False,
        help='Package plugin.'
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
    command_group.add_argument(
        '-C',
        '--create-deploy-target',
        action='store_true',
        dest='createDeployTarget',
        required=False,
        default=False,
        help='Create a new deploy target with interactive commandline.'
    )
    command_group.add_argument(
        '-l',
        '--list-deploy-targets',
        action='store_true',
        dest='listDeployTargets',
        required=False,
        default=False,
        help='List all deploy targets.'
    )
    command_group.add_argument(
        '-d',
        '--delete-deploy-target',
        action='store',
        dest='deleteDeployTarget',
        required=False,
        default='',
        help='Delete deploy targets by name.'
    )

    command_group.add_argument(
        '--enable-cpp17',
        action='store_true',
        dest='enableCpp17',
        required=False,
        default=False,
        help='Change premake cppdialect to c++17 in global premakePlugin.lua. Will leave a backup file in the same directory(%%WWISEROOT%%\\Scripts\\Build\\Plugins).'
    )

    parsed_args = parser.parse_args()
    worker = Worker.get_platform_worker(parsed_args)
    worker.main()


if __name__ == '__main__':
    main()
