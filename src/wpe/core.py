import logging
import os.path as osp
import platform
import subprocess
import glob
from typing import Optional

# 3rd party
import kkpyutil as util

# project
import wpe.util as wpe_util
from wpe.pathman import PathMan
from wpe.wp_wrapper import WpWrapper
from wpe.parameter import ParameterGenerator
from wpe.hook_processor import HookProcessor
from wpe.project_config import ProjectConfig, PlatformTarget
from wpe.test_runner import TestRunner
from wpe.renamer import Renamer
from wpe.jb_run_manager import JbRunManager
from wpe.deployment import Deployment
from wpe import constants
from wpe.build_agent import BuildAgent
from wpe.global_config import GlobalConfig


@util.SingletonDecorator
class Session:
    current = None
    def __init__(self, args, load_configs=True):
        self.args = args

        # lazy inits
        self.pathMan: Optional[PathMan] = None
        self.projConfig: Optional[ProjectConfig] = None
        self.targetPlatforms: list[PlatformTarget] = []
        if load_configs:
            self.load_configs()

    def load_configs(self):
        self.pathMan = PathMan(self.args.root)
        self.projConfig = ProjectConfig(self.pathMan)
        self.targetPlatforms = self.projConfig.target_platforms()
        if platforms := getattr(self.args, 'platforms', []):
            self.targetPlatforms = [plt for plt in self.targetPlatforms if plt.platform in platforms]
        HookProcessor().lazy_init(self.args)


def wp(args):
    logging.info('Run wp.py')
    WpWrapper().wp(args.wpArgs)


def new(args):
    session = Session(args, load_configs=False)
    logging.info('Create new project')
    WpWrapper().new()
    init_wpe(args)
    session.load_configs()
    generate_parameters(args)
    premake(args)
    logging.info('Next step: implement your plugin, build with hooks by command: wpe -b -H')


def init_wpe(args):
    def _append_to_gitignore(root):
        gitignore = osp.join(root, '.gitignore')
        if osp.exists(gitignore):
            with open(gitignore, 'a') as f:
                f.write(constants.extra_gitignore)

    session = Session(args, load_configs=False)
    logging.info('Initialize wpe project config')
    session.pathMan = session.pathMan or PathMan()
    HookProcessor().init(session.pathMan, session.args)
    _append_to_gitignore(session.pathMan.root)
    wpe_util.overwrite_copy(
        osp.join(session.pathMan.templatesDir, '.wpe'),
        osp.join(session.pathMan.configDir)
    )


@HookProcessor().register('premake')
def premake(args):
    session = Session(args)
    logging.info('Premake project')
    platforms = set([plt.platform for plt in session.targetPlatforms])
    for plt in platforms:
        WpWrapper().premake(plt)


@HookProcessor().register('generate_parameters')
def generate_parameters(args):
    def clear_existing_doc():
        util.remove_tree(session.pathMan.docsDir)
        util.remove_tree(session.pathMan.htmlDocsDir)

    session = Session(args)
    clear_existing_doc()
    parameter_manager = ParameterGenerator(session.pathMan,
                                           is_forced=session.args.force,
                                           generate_gui_resource=session.args.gui)
    parameter_manager.main()
    WpWrapper().build('Documentation')


@HookProcessor().register('build')
def build(args):
    session = Session(args)
    logging.info('Build plugin')
    for plt in session.targetPlatforms:
        args = [plt.platform, '-c', session.args.configuration, '-x'] + plt.architectures
        if plt.need_toolset():
            args.extend(['-t', plt.toolset()])
        WpWrapper().build(*args)
    WpWrapper().build('Documentation')


@HookProcessor().register('test')
def test(args):
    session = Session(args)
    TestRunner.create_platform(session.pathMan).main()


@HookProcessor().register('pack')
def pack(args):
    def _collect_packages(_output_dir):
        util.remove_tree(_output_dir)
        for pkg in glob.iglob(osp.join(session.pathMan.root, f'{session.pathMan.pluginName}*.tar.xz')):
            util.move_file(pkg, _output_dir, isdstdir=True)
        util.move_file(osp.join(session.pathMan.root, 'bundle.json'), _output_dir, isdstdir=True)

    def _zip_bundle(_output_dir):
        util.zip_dir(_output_dir)

    session = Session(args)
    logging.info('Package plugin and generate bundle')
    version_code, build_number = WpWrapper().wwiseVersion.rsplit('.', 1)
    build_number = session.projConfig.version()

    plugin_version = f'{version_code}.{build_number}'
    output_dir = osp.join(session.pathMan.distDir, f'{session.pathMan.pluginName}_v{version_code}_Build{build_number}')
    WpWrapper().package('Common', '-v', plugin_version)
    WpWrapper().package('Documentation', '-v', plugin_version)
    for plt in session.projConfig.all_platforms():
        WpWrapper().package(plt, '-v', plugin_version)
    WpWrapper().generate_bundle('-v', plugin_version)
    _collect_packages(output_dir)
    _zip_bundle(output_dir)
    logging.info(f'Saved to {output_dir}')


@HookProcessor().register('full_pack')
def full_pack(args):
    session = Session(args)
    hook_processor = HookProcessor()
    hook_processor.buildConfig = 'Release'
    hook_processor.process_pre_hook('build')
    for plt in session.targetPlatforms:
        args = [plt.platform, '-c', 'Release', '-x'] + plt.architectures
        if plt.need_toolset():
            args.extend(['-t', plt.toolset()])
        WpWrapper().build(*args)
        if plt.is_authoring():
            continue
        args[2] = 'Profile'
        WpWrapper().build(*args)
        args[2] = 'Debug'
        WpWrapper().build(*args)
    hook_processor.process_post_hook('build')
    pack()


@HookProcessor().register('bump')
def bump(args):
    session = Session(args)
    logging.info('Bump wpe project version')
    session.projConfig.bump()
    logging.info(f'Version bumped to {session.projConfig.version()}')


@HookProcessor().register('rename')
def rename(args):
    session = Session(args)
    logging.info(f'Rename plugin from {session.pathMan.pluginName} to {args.rename}.')
    res = input('Commit your changes before renaming is recommended. Continue? [y/n]') == 'y'
    if not res:
        return
    Renamer(args.rename, session.pathMan, session.projConfig).main()
    premake()
    logging.info('Rename completed, check your changes with git status.')


def add_jetbrains_run_config(args):
    session = Session(args)
    JbRunManager(session.pathMan).lazy_add_run_config()


@HookProcessor().register('deploy')
def deploy(args):
    Deployment.create(args).deploy()


@HookProcessor().register('clean')
def clean(args):
    Deployment.create(args).clean()


def config(args):
    GlobalConfig().handle_command(args)


def start_build_agent(args):
    build_agent = BuildAgent()
    build_agent.start(args.port)
