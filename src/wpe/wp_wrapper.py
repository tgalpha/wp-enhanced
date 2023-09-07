import os
import os.path as osp

import kkpyutil as util


class WpWrapper:
    def __init__(self):
        self.wwiseRoot: str = os.getenv('WWISEROOT')
        self.wwiseSDKRoot: str = os.getenv('WWISESDK')
        self.wwiseVersion: str = osp.basename(self.wwiseRoot).split(' ')[1]
        self.wpScriptDir = osp.join(self.wwiseRoot, 'Scripts/Build/Plugins')

        self.subcommands = (
            'build',
            'generate_bundle',
            'new',
            'package',
            'premake',
        )

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

    def build(self, *args):
        return self.run('build', *args)

    def generate_bundle(self, *args):
        return self.run('generate_bundle', *args)

    def new(self, *args):
        return self.run('new', *args)

    def package(self, *args):
        return self.run('package', *args)

    def premake(self, *args):
        return self.run('premake', *args)

    def run(self, subcommand, *args):
        subcommand_module = util.safe_import_module(osp.basename(subcommand), self.wpScriptDir)
        return subcommand_module.run(args)
