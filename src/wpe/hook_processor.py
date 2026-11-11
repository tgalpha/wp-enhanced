import logging
import os.path as osp

import kkpyutil as util

from wpe.pathman import PathMan


@util.SingletonDecorator
class HookProcessor:
    def __init__(self):
        self.pathMan = None
        self.args = None
        self.targetHooks = None

    def lazy_init(self, args):
        self.pathMan = PathMan(cwd=args.root)
        self.args = args
        self.targetHooks = args.withHooks

    def register(self, command):
        """
        return a decorator that wraps the function to run pre&post hooks
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.lazy_init(args[0])
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

    def will_execute(self, phase, command) -> bool:
        hook_name = f'{phase}_{command}'
        if self.targetHooks and hook_name not in self.targetHooks:
            return False
        return osp.isfile(osp.join(self.pathMan.hooksDir, f'{hook_name}.py'))

    def parallel_with(self, phase, command) -> set[str]:
        """
        Step kinds the hook declares it may run in parallel with, via a module-level variable, e.g.
        `WPE_PARALLEL_WITH = ['build']`. Only honored by commands supporting it (currently `full-pack`).
        """
        if not self.will_execute(phase, command):
            return set()
        hook_module = util.safe_import_module(f'{phase}_{command}', self.pathMan.hooksDir)
        return set(getattr(hook_module, 'WPE_PARALLEL_WITH', None) or ())

    def _process_hook(self, phase, command):
        hook_name = f'{phase}_{command}'
        if not self.will_execute(phase, command):
            return

        hook_module = util.safe_import_module(hook_name, self.pathMan.hooksDir)
        logging.info(f'Running hook: {hook_name}')
        hook_module.main(proj_root=self.pathMan.root,
                         plugin_name=self.pathMan.pluginName,
                         **self.args.__dict__
                         )
