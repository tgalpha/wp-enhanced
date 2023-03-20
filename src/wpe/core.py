import logging
import os.path as osp
import platform
import subprocess
from glob import glob
from typing import Optional

# 3rd party
import kkpyutil as util

# project
from wpe.util import *
from wpe.pathman import PathMan
from wpe.wp_wrapper import WpWrapper
from wpe.deploy_target import DeployTarget


class Worker:
    def __init__(self, args, path_man=None):
        self.args = args

        self.wpWrapper = WpWrapper()
        self.pathMan = path_man
        self.deployTarget: Optional[DeployTarget] = None

        self.terminatedWwise = False

    @staticmethod
    def get_platform_worker(args):
        system = platform.system()
        if system == 'Windows':
            return WindowsWorker(args)
        raise NotImplementedError(f'Not implemented for this platform: {system}')

    def main(self):
        self.wpWrapper.validate_env()

        if self.args.wp:
            return self.wp()

        if self.args.new:
            return self.new()

        self.pathMan = self.pathMan or PathMan()
        self.process_deploy_targets()

        if self.args.premake:
            return self.premake()

        if self.args.build:
            return self.build()

    def process_deploy_targets(self):
        self.deployTarget = DeployTarget(path_man=self.pathMan)

        if self.args.createDeployTarget:
            self.deployTarget.create()
        if self.args.listDeployTargets:
            self.deployTarget.list()
        if self.args.deleteDeployTarget:
            self.deployTarget.delete(self.args.deleteDeployTarget)

        if modified_target := (self.args.createDeployTarget or
                               self.args.listDeployTargets or
                               self.args.deleteDeployTarget):
            self.deployTarget.save()

    def wp(self):
        logging.info('Run wp.py')
        self.wpWrapper.wp(self.args.wp)

    def new(self):
        logging.info('Create new project')
        self.wpWrapper.new()

    def premake(self):
        logging.info('Premake project')
        self.wpWrapper.premake('Authoring')

    def build(self):
        self._terminate_wwise()
        self._build()
        self._copy_authoring_plugin()
        self._apply_deploy_targets()
        self._reopen_wwise()

    def _build(self):
        logging.info('Build authoring plugin')
        self.wpWrapper.build('Authoring', '-c', self.args.configuration, '-x', 'x64', '-t', 'vc160')

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
            build_output_dir = osp.join(self.wpWrapper.wwiseRoot,
                                        f'Authoring/x64/{self.args.configuration}/bin/Plugins')
        else:
            build_output_dir = osp.join(self.wpWrapper.wwiseSDKRoot, f'x64_vc160/{self.args.configuration}/bin')

        self.sharedPluginFiles = list(filter(lambda x: not str(x).endswith('.xml'),
                                             glob(osp.join(build_output_dir, f'{self.pathMan.pluginName}.*'))))
        return self.sharedPluginFiles

    def _build(self):
        super()._build()
        logging.info('Build shared plugin')
        self.wpWrapper.build('Windows_vc160', '-c', self.args.configuration, '-x', 'x64', '-t', 'vc160')

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

        build_output_dir = osp.join(self.wpWrapper.wwiseRoot, f'Authoring/x64/{self.args.configuration}/bin/Plugins')
        src_files = glob(osp.join(build_output_dir, f'{self.pathMan.pluginName}.*'))
        dst_dir = osp.join(self.wpWrapper.wwiseRoot, f'Authoring/x64/Release/bin/Plugins')
        logging.info(f'Copy authoring plugin "{src_files}", from "{build_output_dir}" to "{dst_dir}"')
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
            wwise_exe = osp.join(self.wpWrapper.wwiseRoot, 'Authoring/x64/Release/bin/Wwise.exe')
            util.run_daemon([wwise_exe])
