import copy
import os.path as osp

import kkpyutil as util

import wpe.util as wpe_util


class ConfigKey:
    USE_WSL_FOR_LINUX = 'use-wsl-for-linux'


@util.SingletonDecorator
class GlobalConfig:
    _DEFAULT_CONFIG = {
        ConfigKey.USE_WSL_FOR_LINUX: False,
    }

    def __init__(self):
        self.configFile = osp.join(util.get_platform_appdata_dir(), 'wpe', 'config.toml')
        # Loaded as a flat dict
        self._configDict = copy.deepcopy(self._DEFAULT_CONFIG)
        self.load()

    def handle_command(self, args):
        if args.list:
            return self.list_args()
        if args.key:
            if args.value:
                self.set(args.key, args.value)
            else:
                self._print_config(args.key)

    def list_args(self):
        for key, val in self._configDict.items():
            print(f'{key} = {val}')

    def load(self):
        if not osp.isfile(self.configFile):
            return
        loaded = wpe_util.load_toml(self.configFile)
        for key, val in loaded.items():
            self._configDict[key] = val

    def save(self):
        wpe_util.save_toml(self.configFile, self._configDict)

    def get(self, key):
        if key not in self._configDict:
            raise KeyError(f'Invalid config key: {key}')
        return self._configDict[key]

    def set(self, key, value):
        def _convert_value_type(_value):
            if type(self._DEFAULT_CONFIG[key]) is bool:
                return True if _value.lower() == 'true' else False
            elif type(self._DEFAULT_CONFIG[key]) is int:
                return int(_value)
            elif type(self._DEFAULT_CONFIG[key]) is float:
                return float(_value)
            return value

        if key not in self._configDict:
            raise KeyError(f'Invalid config key: {key}')
        self._configDict[key] = _convert_value_type(value)
        self.save()

    def _print_config(self, key):
        print(f'{key} = {self.get(key)}')