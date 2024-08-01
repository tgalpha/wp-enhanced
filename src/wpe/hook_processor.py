import logging
import os.path as osp

import kkpyutil as util

from wpe.pathman import PathMan


@util.SingletonDecorator
class HookProcessor:
    def __init__(self):
        self.pathMan = None
        self.args = None
        self.buildConfig = None
        self.targetHooks = None

    def init(self, path_man: PathMan, args):
        self.pathMan = path_man
        self.args = args
        self.buildConfig = args.configuration
        self.targetHooks = args.withHooks

    def register(self, command):
        """
        return a decorator that wraps the function to run pre&post hooks
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.process_pre_hook(command)
                res = func(*args, **kwargs)
                self.process_post_hook(command)
                return res
            return wrapper
        return decorator

    def process_pre_hook(self, command):
        self._process_hook('pre', command)

    def process_post_hook(self, command):
        self._process_hook('post', command)

    def _process_hook(self, phase, command):
        def should_execute(_hook_name):
            if not self.targetHooks or _hook_name in self.targetHooks:
                return osp.isfile(osp.join(self.pathMan.hooksDir, f'{hook_name}.py'))

        hook_name = f'{phase}_{command}'
        if not should_execute(hook_name):
            return

        hook_module = util.safe_import_module(hook_name, self.pathMan.hooksDir)
        logging.info(f'Running hook: {hook_name}')
        hook_module.main(proj_root=self.pathMan.root,
                         build_config=self.buildConfig,
                         plugin_name=self.pathMan.pluginName,
                         **self.args.__dict__
                         )
