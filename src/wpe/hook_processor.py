import logging
import os.path as osp

import kkpyutil as util

from wpe.pathman import PathMan


class HookProcessor:
    def __init__(self, path_man: PathMan, build_config: str, enabled=False):
        self.pathMan = path_man
        self.buildConfig = build_config
        self.enabled = enabled

    def processPreHook(self, command):
        self._processHook('pre', command)

    def processPostHook(self, command):
        self._processHook('post', command)

    def _processHook(self, phase, command):
        hook_name = f'{phase}_{command}'
        if not self.enabled or not osp.isfile(osp.join(self.pathMan.hooksDir, f'{hook_name}.py')):
            return

        hook_module = util.safe_import_module(hook_name, self.pathMan.hooksDir)
        logging.info(f'Running hook: {hook_name}')
        hook_module.main(proj_root=self.pathMan.root,
                         build_config=self.buildConfig,
                         plugin_name=self.pathMan.pluginName,
                         )
