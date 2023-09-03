import os
import os.path as osp
import re

import kkpyutil as util


class PathMan:
    def __init__(self, cwd=None):
        self.root = cwd or os.getcwd()
        self.premakePluginLua = self.find_premake_plugin_lua_in_ancestor_and_update_root()
        os.chdir(self.root)
        self.pluginName = self.parse_plugin_name()
        self.pluginConfigHeader = osp.join(self.root, f'{self.pluginName}Config.h')
        self.pluginId = self.parse_plugin_id()
        self.configDir = osp.join(self.root, '.wpe')
        self.templatesDir = osp.join(osp.dirname(__file__), 'templates')
        self.parameterConfig = osp.join(self.configDir, 'wpe_parameters.toml')
        self.docsDir = osp.join(self.root, 'WwisePlugin/res/Md')

    def find_premake_plugin_lua_in_ancestor_and_update_root(self):
        premake_script_filename = 'PremakePlugin.lua'
        while self.root:
            lua = osp.join(self.root, premake_script_filename)
            if osp.isfile(lua):
                return lua
            parent = osp.dirname(self.root)
            if parent == self.root:
                break
            self.root = parent
        raise FileNotFoundError(f'Can not find PremakePlugin.lua in ancestor directories. '
                                f'This command must be executed under a plugin directory. cwd: {os.getcwd()}')

    def parse_plugin_name(self):
        lines = util.load_lines(self.premakePluginLua, rmlineend=True)
        name_define_pattern = r'Plugin.name = ".*"'
        for line in lines:
            if matched := re.match(name_define_pattern, line):
                return matched.group().split('"')[1]

    def parse_plugin_id(self):
        lines = util.load_lines(self.pluginConfigHeader, rmlineend=True)
        prefix = '    static const unsigned short PluginID = '
        name_define_pattern = rf'{prefix}\d+'
        for line in lines:
            if matched := re.match(name_define_pattern, line):
                return int(matched.group().lstrip(prefix))

    def get_premake_template_path(self):
        return osp.join(self.templatesDir, 'premakePlugins.lua')
