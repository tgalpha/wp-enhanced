import os
import os.path as osp
import platform

import kkpyutil as util

import wpe.util as wpe_util
from wpe.global_config import GlobalConfig, ConfigKey


def create_sdk_symlink(wwise_sdk):
    temp_sdk_dir = 'C:\\temp\\wpe\\WWISESDK' if platform.system() == 'Windows' else osp.expanduser(
        '~/temp/wpe/WWISESDK')
    if osp.exists(temp_sdk_dir):
        if osp.islink(temp_sdk_dir):
            os.remove(temp_sdk_dir)
        else:
            raise FileExistsError(f'{temp_sdk_dir} exists and is not a symlink to WWISESDK')
    os.makedirs(osp.dirname(temp_sdk_dir), exist_ok=True)
    os.symlink(wwise_sdk, temp_sdk_dir)
    return temp_sdk_dir


def inject_wwise_sdk_for_android(func):
    def wrapper(*args, **kwargs):
        plt = args[0] if args else ''
        if plt != 'Android':
            return func(*args, **kwargs)
        org_sdk_dir = os.getenv('WWISESDK')
        temp_sdk_dir = create_sdk_symlink(org_sdk_dir)
        os.environ['WWISESDK'] = temp_sdk_dir
        res = func(*args, **kwargs)
        os.environ['WWISESDK'] = org_sdk_dir
        return res
    return wrapper


@util.SingletonDecorator
class WpWrapper:
    def __init__(self):
        self.wwiseRoot: str = os.getenv('WWISEROOT')
        self.wwiseSDKRoot: str = os.getenv('WWISESDK')
        self.wwiseVersion: str = self._load_wwise_version()
        self.wpScriptDir = osp.join(self.wwiseRoot, 'Scripts/Build/Plugins')
        util.lazy_prepend_sys_path([self.wpScriptDir])

        self.subcommands = (
            'build',
            'generate_bundle',
            'new',
            'package',
            'premake',
        )
        self.validate_env()

    def _load_wwise_version(self) -> str:
        install_entry = util.load_json(osp.join(self.wwiseRoot, 'install-entry.json'))
        version = install_entry['bundle']['version']
        return f'{version["year"]}.{version["major"]}.{version["minor"]}.{version["build"]}'

    def validate_env(self):
        if self.wwiseRoot is None:
            raise EnvironmentError(f'Unknown env variable: WWISEROOT\n  - Try setting environment variables in Wwise '
                                   f'Launcher')

        if self.wwiseSDKRoot is None:
            raise EnvironmentError(f'Unknown env variable: WWISESDK\n  - Try setting environment variables in Wwise '
                                   f'Launcher')

        if not osp.isfile((wp := osp.join(self.wpScriptDir, 'wp.py'))):
            raise FileNotFoundError(f'"{wp}" not found.')

        for subcommand in self.subcommands:
            if not osp.isfile((subcommand_file := osp.join(self.wpScriptDir, f'{subcommand}.py'))):
                raise FileNotFoundError(f'Subcommand "{subcommand_file}" not found.')

    def wp(self, args):
        subcommand = args[0]
        if subcommand not in self.subcommands:
            raise ValueError(f'Unknown subcommand: {subcommand}')
        return self.run(subcommand, *args[1:])

    @inject_wwise_sdk_for_android
    def build(self, *args):
        plt = args[0]
        if plt == 'Linux' and GlobalConfig().get(ConfigKey.USE_WSL_FOR_LINUX):
            return self.build_with_wsl(*args)

        import wpe.wp_patch.build as wpe_build
        res = wpe_build.run(args)
        if res != 0:
            raise RuntimeError(f'Build failed. Exit code: {res}')
        return res

    def build_with_wsl(self, *args):
        util.run_cmd(['wsl', '--', 'python3', self.__get_wsl_wwise_root(), 'build'] + list(args))

    def generate_bundle(self, *args):
        return self.run('generate_bundle', *args)

    def new(self, *args):
        return self.run('new', *args)

    @staticmethod
    def package(*args):
        import wpe.wp_patch.package as wpe_package
        res = wpe_package.run(args)
        return res

    @inject_wwise_sdk_for_android
    def premake(self, *args):
        plt = args[0]
        if plt == 'Linux' and GlobalConfig().get(ConfigKey.USE_WSL_FOR_LINUX):
            return self.premake_with_wsl(*args)

        import wpe.wp_patch.premake as wpe_premake
        res = wpe_premake.run(args)
        return res

    def premake_with_wsl(self, *args):
        util.run_cmd(['wsl', '--', 'python3', self.__get_wsl_wwise_root(), 'premake'] + list(args))

    def run(self, subcommand, *args):
        subcommand_module = util.safe_import_module(osp.basename(subcommand), self.wpScriptDir)
        return subcommand_module.run(args)

    def __get_wsl_wwise_root(self):
        wwise_root = wpe_util.convert_to_wsl_path(self.wwiseRoot)
        wp_py_rel_path = 'Scripts/Build/Plugins/wp.py'
        return f'{wwise_root}/{wp_py_rel_path}'
