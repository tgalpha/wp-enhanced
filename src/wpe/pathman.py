import os
import os.path as osp


class PathMan:
    def __init__(self, cwd=None):
        self.premakePluginLua = self.find_premake_plugin_lua_in_ancestor(cwd=cwd)
        self.root = osp.dirname(self.premakePluginLua)
        self.pluginName = self.parse_plugin_name()
        self.configDir = osp.join(self.root, '.wpe')

    def find_premake_plugin_lua_in_ancestor(self, cwd=None):
        cwd = cwd or os.getcwd()
        raise NotImplementedError()

    def parse_plugin_name(self):
        raise NotImplementedError()

    def lazy_create_config_gitignore(self):
        raise NotImplementedError()
