import logging
import os.path as osp
import platform
import subprocess
import glob

# 3rd party
import kkpyutil as util

# project
import wpe.util as wpe_util
from wpe.pathman import PathMan
from wpe.wp_wrapper import WpWrapper
from wpe.parameter import ParameterGenerator
from wpe.hook_processor import HookProcessor
from wpe.project_config import ProjectConfig, PlatformTarget


class Worker:
    def __init__(self, args, path_man=None):
        self.args = args

        self.wpWrapper = WpWrapper()
        self.pathMan = path_man

        self.projConfig = None
        self.targetPlatforms: list[PlatformTarget] = []

        self.terminatedWwise = False

    @staticmethod
    def get_platform_worker(args):
        system = platform.system()
        if system == 'Windows':
            return WindowsWorker(args)
        raise NotImplementedError(f'Not implemented for this platform: {system}')

    def _lazy_init_pathman(self):
        self.pathMan = self.pathMan or PathMan()
        self.projConfig = ProjectConfig(self.pathMan)
        self.targetPlatforms = self.projConfig.target_platforms()
        if self.args.platform:
            self.targetPlatforms = [plt for plt in self.targetPlatforms if plt.platform == self.args.platform]

    def main(self):
        self.wpWrapper.validate_env()

        if self.args.wp:
            return self.wp()

        if self.args.new:
            return self.new()

        self._lazy_init_pathman()

        if self.args.initWpe:
            return self.init_wpe()

        hook_processor = HookProcessor(self.pathMan, self.args.configuration, self.args.withHooks)
        if self.args.premake:
            hook_processor.process_pre_hook('premake')
            self.premake()
            hook_processor.process_post_hook('premake')

        if self.args.generateParameters:
            hook_processor.process_pre_hook('generate_parameters')
            self.generate_parameters()
            hook_processor.process_post_hook('generate_parameters')

        if self.args.build:
            hook_processor.process_pre_hook('build')
            self.build()
            hook_processor.process_post_hook('build')

        if self.args.pack:
            hook_processor.process_pre_hook('pack')
            self.pack()
            hook_processor.process_post_hook('pack')

        if self.args.fullPack:
            hook_processor.process_pre_hook('build')
            hook_processor.process_pre_hook('pack')
            self.full_pack()
            hook_processor.process_post_hook('build')
            hook_processor.process_post_hook('pack')

        if self.args.bump:
            hook_processor.process_pre_hook('bump')
            self.bump()
            hook_processor.process_post_hook('bump')

    def wp(self):
        logging.info('Run wp.py')
        self.wpWrapper.wp(self.args.wp)

    def new(self):
        logging.info('Create new project')
        self.wpWrapper.new()
        self.init_wpe()
        self.premake()
        logging.info('Next step: implement your plugin, build with hooks by command: wpe -b -H')

    def init_wpe(self):
        logging.info('Initialize wpe project config')
        self._lazy_init_pathman()

        wpe_util.overwrite_copy(
            osp.join(self.pathMan.templatesDir, '.wpe'),
            osp.join(self.pathMan.configDir)
        )

    def premake(self):
        logging.info('Premake project')
        for plt in self.targetPlatforms:
            self.wpWrapper.premake(plt.platform)

    def generate_parameters(self):
        parameter_manager = ParameterGenerator(self.pathMan, is_forced=self.args.force)
        parameter_manager.main()
        self.wpWrapper.build('Documentation')

    def build(self):
        self._terminate_wwise()
        self._build()
        self._reopen_wwise()

    def pack(self):
        def _collect_packages(_output_dir):
            util.remove_tree(_output_dir)
            for pkg in glob.iglob(osp.join(self.pathMan.root, f'{self.pathMan.pluginName}*.tar.xz')):
                util.move_file(pkg, _output_dir, isdstdir=True)
            util.move_file(osp.join(self.pathMan.root, 'bundle.json'), _output_dir, isdstdir=True)

        def _zip_bundle(_output_dir):
            util.zip_dir(_output_dir)

        logging.info('Package plugin and generate bundle')
        version_code, build_number = self.wpWrapper.wwiseVersion.rsplit('.', 1)
        build_number = self.projConfig.version()

        plugin_version = f'{version_code}.{build_number}'
        output_dir = osp.join(self.pathMan.distDir, f'{self.pathMan.pluginName}_v{version_code}_Build{build_number}')
        self.wpWrapper.package('Common', '-v', plugin_version)
        self.wpWrapper.package('Documentation', '-v', plugin_version)
        for plt in self.targetPlatforms:
            self.wpWrapper.package(plt.platform, '-v', plugin_version)
        self.wpWrapper.generate_bundle('-v', plugin_version)
        _collect_packages(output_dir)
        _zip_bundle(output_dir)
        logging.info(f'Saved to {output_dir}')

    def full_pack(self):
        for plt in self.targetPlatforms:
            args = [plt.platform, '-c', 'Release', '-x', plt.architecture]
            if plt.need_toolset():
                args.extend(['-t', plt.toolset()])
            self.wpWrapper.build(*args)
            if plt.is_authoring():
                continue
            args[2] = 'Profile'
            self.wpWrapper.build(*args)
        self.pack()

    def bump(self):
        logging.info('Bump wpe project version')
        self.projConfig.bump()
        logging.info(f'Version bumped to {self.projConfig.version()}')

    def _build(self):
        logging.info('Build plugin')
        for plt in self.targetPlatforms:
            args = [plt.platform, '-c', self.args.configuration, '-x', plt.architecture]
            if plt.need_toolset():
                args.extend(['-t', plt.toolset()])
            self.wpWrapper.build(*args)
        self.wpWrapper.build('Documentation')

    def _terminate_wwise(self):
        raise NotImplementedError('subclass it')

    def _reopen_wwise(self):
        raise NotImplementedError('subclass it')


class WindowsWorker(Worker):
    def __init__(self, args):
        super().__init__(args)

    def _terminate_wwise(self):
        if self.args.force:
            cmd = ['taskkill', '/IM', 'wwise.exe', '/F']
            try:
                util.run_cmd(cmd)
                self.terminatedWwise = True
            except subprocess.CalledProcessError:
                pass

    def _reopen_wwise(self):
        if self.args.force and self.terminatedWwise:
            wwise_exe = osp.join(self.wpWrapper.wwiseRoot, 'Authoring/x64/Release/bin/Wwise.exe')
            util.run_daemon([wwise_exe])
