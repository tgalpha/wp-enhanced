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


class Worker:
    def __init__(self, args, path_man=None):
        self.args = args

        self.wpWrapper = WpWrapper()
        self.pathMan = path_man

        self.terminatedWwise = False

    @staticmethod
    def get_platform_worker(args):
        system = platform.system()
        if system == 'Windows':
            return WindowsWorker(args)
        raise NotImplementedError(f'Not implemented for this platform: {system}')

    def _lazy_init_pathman(self):
        self.pathMan = self.pathMan or PathMan()

    def main(self):
        self.wpWrapper.validate_env()

        if self.args.wp:
            return self.wp()

        if self.args.new:
            return self.new()

        self._lazy_init_pathman()

        if self.args.initWpe:
            return self.init_wpe()

        if self.args.enableCpp17:
            return self.enable_cpp17()

        hook_processor = HookProcessor(self.pathMan, self.args.configuration, self.args.withHooks)
        if self.args.premake:
            hook_processor.processPreHook('premake')
            self.premake()
            hook_processor.processPostHook('premake')

        if self.args.generateParameters:
            hook_processor.processPreHook('generate_parameters')
            self.generate_parameters()
            hook_processor.processPostHook('generate_parameters')

        if self.args.build:
            hook_processor.processPreHook('build')
            self.build()
            hook_processor.processPostHook('build')

        if self.args.pack:
            hook_processor.processPreHook('pack')
            self.pack()
            hook_processor.processPostHook('pack')

    def wp(self):
        logging.info('Run wp.py')
        self.wpWrapper.wp(self.args.wp)

    def new(self):
        logging.info('Create new project')
        self.wpWrapper.new()
        self.init_wpe()
        self.premake()
        self.generate_parameters()
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
        self.wpWrapper.premake('Authoring')

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
        output_dir = osp.join(self.pathMan.distDir, f'{self.pathMan.pluginName}_v{version_code}_Build{build_number}')
        self.wpWrapper.package('Common', '-v', self.wpWrapper.wwiseVersion)
        self.wpWrapper.package('Documentation', '-v', self.wpWrapper.wwiseVersion)
        self.wpWrapper.package('Windows_vc160', '-v', self.wpWrapper.wwiseVersion)
        self.wpWrapper.package('Authoring', '-v', self.wpWrapper.wwiseVersion)
        self.wpWrapper.generate_bundle('-v', self.wpWrapper.wwiseVersion)
        _collect_packages(output_dir)
        _zip_bundle(output_dir)
        logging.info(f'Saved to {output_dir}')

    def _build(self):
        logging.info('Build authoring plugin')
        self.wpWrapper.build('Authoring', '-c', self.args.configuration, '-x', 'x64', '-t', 'vc160')

    def _terminate_wwise(self):
        raise NotImplementedError('subclass it')

    def _reopen_wwise(self):
        raise NotImplementedError('subclass it')

    def enable_cpp17(self):
        logging.info('Enable C++17')
        template = self.pathMan.get_premake_template_path()
        target = osp.abspath(osp.join(self.wpWrapper.wpScriptDir, 'premakePlugins.lua'))
        backup = target + '.bak'
        if osp.isfile(backup):
            if input(f'Backup file "{backup}" already exists, overwrite? [y/n]') != 'y':
                logging.info('Abort')
                return

        util.copy_file(target, backup)
        util.copy_file(template, target)
        logging.info(f'premakePlugins.lua updated. Modification is wrapped in [wp-enhanced]. Backup file: "{backup}"')


class WindowsWorker(Worker):
    def __init__(self, args):
        super().__init__(args)

    def _build(self):
        super()._build()
        logging.info('Build shared plugin')
        self.wpWrapper.build('Windows_vc160', '-c', self.args.configuration, '-x', 'x64', '-t', 'vc160')

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
