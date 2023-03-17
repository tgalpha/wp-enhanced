import argparse

from wpe.core import Worker


def main():
    parser = argparse.ArgumentParser(
        prog='Plugin dev ci build tool',
        add_help=True,
        epilog='Wrapper of `wp.py`. Easy to premake, build, and deploy wwise plugins.',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '--wp',
        action='store',
        dest='wp',
        nargs='*',
        default=[],
        required=False,
        help='Pass arguments to wp.py. Example: --wp new'
    )

    parser.add_argument(
        '-n',
        '--new',
        action='store_true',
        dest='new',
        default=False,
        required=False,
        help='Create a new plugin project.'
    )

    parser.add_argument(
        '-p',
        '--premake',
        action='store_true',
        dest='premake',
        default=False,
        required=False,
        help='Premake authoring project.'
    )

    parser.add_argument(
        '-b',
        '--build',
        action='store_true',
        dest='build',
        default=False,
        required=False,
        help='Build project.'
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
        '--force-copy-file',
        action='store_true',
        dest='forceCopyFile',
        required=False,
        default=False,
        help='Terminate Wwise process and copy plugin files, then reopen Wwise.'
    )
    parser.add_argument(
        '-C',
        '--create-deploy-target',
        action='store_true',
        dest='createDeployTarget',
        required=False,
        default=False,
        help='Create a new deploy target with interactive commandline.'
    )
    parser.add_argument(
        '-l',
        '--list-deploy-targets',
        action='store_true',
        dest='listDeployTargets',
        required=False,
        default=False,
        help='List all deploy targets.'
    )
    parser.add_argument(
        '-d',
        '--delete-deploy-target',
        action='store',
        dest='deleteDeployTarget',
        required=False,
        default='',
        help='Delete deploy targets by name.'
    )

    parsed_args = parser.parse_args()
    worker = Worker.get_platform_worker(parsed_args)
    worker.main()


if __name__ == '__main__':
    main()
