import logging
import os
import os.path as osp
import platform
import subprocess
from glob import glob

# 3rd party
import kkpyutil as util

# project
from wpe.util import *
from wpe.pathman import PathMan
from wpe.deploy_target import DeployTarget


class Worker:
    def __init__(self, args, path_man=None):
        self.args = args
        self.wwiseRoot: str = os.getenv('WWISEROOT')
        self.wwiseSDKRoot: str = os.getenv('WWISESDK')
        self.wpScript = osp.join(self.wwiseRoot, 'Scripts/Build/Plugins/wp.py')

        self.pathMan = path_man or PathMan()
        self.deployTarget = DeployTarget(path_man=self.pathMan)

        self.terminatedWwise = False

    @staticmethod
    def get_platform_worker(args):
        system = platform.system()
        if system == 'Windows':
            return WindowsWorker(args)
        raise NotImplementedError(f'Not implemented for this platform: {system}')

    def main(self):
        if self.args.newDeployTarget:
            self.deployTarget.create()
        if self.args.listDeployTargets:
            self.deployTarget.list()
        if self.args.deleteDeployTarget:
            self.deployTarget.delete(self.args.deleteDeployTarget)

        if modified_target := (self.args.newDeployTarget or
                               self.args.listDeployTargets or
                               self.args.deleteDeployTarget):
            self.deployTarget.save()
            return

        self._validate_env()

        if self.args.premake:
            return self.premake()

        if self.args.build:
            return self.build()

    def premake(self):
        logging.info('Premake project')
        util.run_cmd(
            [
                'python',
                self.wpScript,
                'build',
                'Authoring',
                '-c',
                self.args.configuration,
                '-x',
                'x64',
                '-t',
                'vc160'
            ],
            cwd=self.pathMan.root
        )

    def build(self):
        self._terminate_wwise()
        self._build()
        self._copy_authoring_plugin()
        self._apply_deploy_targets()
        self._reopen_wwise()

    def _validate_env(self):
        if self.wwiseRoot is None:
            raise EnvironmentError(f'Unknown env variable: WWISEROOT\n  - Try setting environment variables in Wwise '
                                   f'Launcher')

        if self.wwiseSDKRoot is None:
            raise EnvironmentError(f'Unknown env variable: WWISESDK\n  - Try setting environment variables in Wwise '
                                   f'Launcher')

        if not osp.isfile(self.wpScript):
            raise FileNotFoundError(f'"{self.wpScript}" not found.')

    def _build(self):
        logging.info('Build authoring plugin')
        util.run_cmd(
            [
                'python',
                self.wpScript,
                'build',
                'Authoring',
                '-c',
                self.args.configuration,
                '-x',
                'x64',
                '-t',
                'vc160'
            ],
            cwd=self.pathMan.root
        )

    def _terminate_wwise(self):
        raise NotImplementedError('subclass it')

    def _copy_authoring_plugin(self):
        raise NotImplementedError('subclass it')

    def _apply_deploy_targets(self):
        raise NotImplementedError('subclass it')

    def _reopen_wwise(self):
        raise NotImplementedError('subclass it')


class WindowsWorker(Worker):
    def __init__(self, args):
        super().__init__(args)
        self.sharedPluginFiles = None

    def __lazy_query_shared_plugin_files(self) -> list:
        if self.sharedPluginFiles is not None:
            return self.sharedPluginFiles

        if self.args.configuration == 'Debug':
            # Use authoring plugin in debug mode for assert hook
            build_output_dir = osp.join(self.wwiseRoot, f'Authoring/x64/{self.args.configuration}/bin/Plugins')
        else:
            build_output_dir = osp.join(self.wwiseSDKRoot, f'x64_vc160/{self.args.configuration}/bin')

        self.sharedPluginFiles = list(filter(lambda x: not str(x).endswith('.xml'),
                                             glob(osp.join(build_output_dir, f'{self.pathMan.pluginName}'))))
        return self.sharedPluginFiles

    def _build(self):
        super()._build()
        logging.info('Build shared plugin')
        util.run_cmd(
            [
                'python',
                self.wpScript,
                'build',
                'Windows_vc160',
                '-c',
                self.args.configuration,
                '-x',
                'x64'
            ],
            cwd=self.pathMan.root
        )

    def _terminate_wwise(self):
        if self.args.forceCopyFile:
            cmd = ['taskkill', '/IM', 'wwise.exe', '/F']
            try:
                util.run_cmd(cmd)
                self.terminatedWwise = True
            except subprocess.CalledProcessError:
                pass

    def _copy_authoring_plugin(self):
        if self.args.configuration == 'Release':
            return

        build_output_dir = osp.join(self.wwiseRoot, f'Authoring/x64/{self.args.configuration}/bin/Plugins')
        src_files = glob(osp.join(build_output_dir, f'{self.pathMan.pluginName}'))
        dst_dir = osp.join(self.wwiseRoot, f'Authoring/x64/Release/bin/Plugins')
        logging.info(f'Copy shared plugin "{src_files}", from "{build_output_dir}" to "{dst_dir}"')
        for src in src_files:
            dst = osp.join(dst_dir, osp.basename(src))
            overwrite_copy(src, dst)

    def _apply_deploy_targets(self):
        plugin_files = self.__lazy_query_shared_plugin_files()

        for name, config in self.deployTarget.items():
            deploy_path = None
            if (engine := config['engine']) == 'ue':
                deploy_path = osp.join(f'{config["root"]}/Plugins/Wwise/ThirdParty/x64_vc160/Profile/bin')
            elif engine == 'unity':
                logging.warning('Unity is currently unsupported, skipped.')
            elif engine == 'other':
                deploy_path = osp.join(f'{config["root"]}')
            else:
                logging.warning(f'Unsupported engine type: {engine}, skipped.')

            if deploy_path is not None:
                logging.info(f'Apply deploy target: {name}')
                for output in plugin_files:
                    logging.info(
                        f'Copy shared plugin "{output}" to "{deploy_path}"')
                    dst = osp.join(deploy_path, osp.basename(output))
                    overwrite_copy(output, dst)

    def _reopen_wwise(self):
        if self.args.forceCopyFile and self.terminatedWwise:
            wwise_exe = osp.join(self.wwiseRoot, 'Authoring/x64/Release/bin/Wwise.exe')
            util.run_daemon([wwise_exe])
