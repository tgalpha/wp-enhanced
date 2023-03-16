import logging
import os.path as osp

import kkpyutil as util

from wpe.pathman import PathMan


class DeployTarget:
    def __init__(self, path_man: PathMan):
        self.pathMan = path_man
        self.deployTargetConfigPath = osp.join(self.pathMan.configDir, '.deploy_target.json')
        self.deployTargetConfig = {}
        self.load()

    def items(self):
        return self.deployTargetConfig.items()

    def load(self):
        if osp.isfile(self.deployTargetConfigPath):
            self.deployTargetConfig = util.load_json(self.deployTargetConfigPath)

    def create(self):
        while True:
            name = input('Target name: ')
            if name and name not in self.deployTargetConfig.keys():
                break
            logging.warning(f'Target exists: {name}')

        engine_selections = {'ue', 'unity', 'other'}
        while True:
            engine = input('Game engine type(ue/unity/other): ')
            if engine in engine_selections:
                break
            logging.warning(f'Invalid engine: {engine}')

        while True:
            root = input('Game project root: ')
            if osp.isdir(root):
                break
            logging.warning(f'Directory not exists: {root}')

        self.deployTargetConfig[name] = {
            'engine': engine,
            'root': root
        }
        logging.info(f'New target created: {root}')

    def list(self):
        if not self.deployTargetConfig:
            logging.info('There is no deploy target.')

        for name, config in self.deployTargetConfig.items():
            print(name)
            engine = config["engine"]
            print(f'\t{engine=}')
            root = config["root"]
            print(f'\t{root=}\n')

    def delete(self, target_name: str):
        if target_name in self.deployTargetConfig.keys():
            self.deployTargetConfig.pop(target_name)
            logging.info(f'Deleted target: {target_name}')

    def save(self):
        util.save_json(self.deployTargetConfigPath, self.deployTargetConfig)
        self._lazy_create_config_gitignore()

    def _lazy_create_config_gitignore(self):
        if osp.isfile(ignore_file := osp.join(self.pathMan.configDir, '.gitignore')):
            return

        logging.info(f'Creating .gitignore for config directory: {ignore_file}')
        util.save_text(ignore_file, '.deploy_target.json')
