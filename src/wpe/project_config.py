import logging
import os.path as osp

import kkpyutil as util

# project
from wpe.util import *
from wpe.pathman import PathMan


class PluginInfo:
    def __init__(self, info_dict: dict):
        self.infoDict = info_dict
        self.defaultPlatformSupport = '''<Platform Name="Any">
  <CanBeInsertOnBusses>true</CanBeInsertOnBusses>
  <CanBeInsertOnAudioObjects>true</CanBeInsertOnAudioObjects>
  <CanBeRendered>true</CanBeRendered>
</Platform>'''

    def generate_platform_support(self) -> list[str]:
        if not self.infoDict['platform_support']:
            return self.defaultPlatformSupport.splitlines()
        lines = []
        for platform, config in self.infoDict['platform_support'].items():
            lines.append(f'<Platform Name="{platform}">')
            for key, value in config.items():
                lines.append(f'  <{key}>{str(value).lower()}</{key}>')
            lines.append('</Platform>')
        return lines


class ProjectConfig:
    def __init__(self, path_man: PathMan):
        self.pathMan = path_man
        self.config = None

    def load(self):
        if osp.isfile(self.pathMan.projConfig):
            self.config = load_toml(self.pathMan.projConfig)
            return

        if osp.isfile(self.pathMan.parameterConfig):
            self.config = load_toml(self.pathMan.parameterConfig)
            logging.warning('wpe_parameters.toml is deprecated. Please rename it to wpe_project.toml.')
            return

        raise FileNotFoundError(f'wpe project config not found: {self.pathMan.projConfig}')

    def bump(self):
        new_version = self.version() + 1
        config_lines = util.load_lines(self.pathMan.projConfig)
        for i, line in enumerate(config_lines):
            if line.startswith('version = '):
                config_lines[i] = f'version = {new_version}\n'
                break
        util.save_lines(self.pathMan.projConfig, config_lines)
        self.load()

    def plugin_info(self) -> PluginInfo:
        return PluginInfo(self.config['plugin_info'])

    def has_parameters(self) -> bool:
        return 'parameters' in self.config

    def parameter_defines(self) -> dict:
        return self.config['parameters'].get('defines', {})

    def parameter_templates(self) -> dict:
        return self.config['parameters'].get('templates', {})

    def parameter_inner_types(self) -> dict:
        return self.config['parameters'].get('inner_types', {})

    def parameter_from_templates(self) -> list:
        return self.config['parameters'].get('from_templates', [])

    def parameter_from_inner_types(self) -> list:
        return self.config['parameters'].get('from_inner_types', [])

    def version(self) -> int:
        return self.config['project']['version']
