import logging
import os.path as osp
import platform

import kkpyutil as util
import requests

from wpe.pathman import PathMan
from wpe.util import overwrite_copy, remove_ansi_color, parse_premake_lua_table


class PluginTestRunner:
    def __init__(self, path_man: PathMan):
        self.pathMan = path_man

    @staticmethod
    def create_platform(path_man: PathMan):
        system = platform.system()
        if system == 'Windows':
            return _WindowsTestRunner(path_man)
        raise NotImplementedError(f'Not implemented for this platform: {system}')

    def main(self):
        self._lazy_create_test_project()
        self._build_test_project()
        self._run_test()

    def _lazy_create_test_project(self):
        def lazy_download_catch2_src():
            catch2_files = ['catch_amalgamated.hpp', 'catch_amalgamated.cpp']
            catch2_dir = osp.join(self.pathMan.testDir, 'catch2')
            if all(osp.isfile(osp.join(catch2_dir, f)) for f in catch2_files):
                return
            logging.info('downloading catch2 source files')
            download_base_url = 'https://github.com/catchorg/Catch2/releases/download/v3.5.3/'
            for file in catch2_files:
                res = requests.get(download_base_url + file)
                util.save_text(osp.join(catch2_dir, file), res.text)

        def lazy_copy_test_src():
            test_src_files = ['CMakeLists.txt', 'main.cpp', '.gitignore', 'util']
            if all(osp.exists(osp.join(self.pathMan.testDir, p)) for p in test_src_files):
                return
            logging.info('copying test source files')
            test_templates_dir = osp.join(self.pathMan.templatesDir, 'test')
            for file in test_src_files:
                overwrite_copy(osp.join(test_templates_dir, file), osp.join(self.pathMan.testDir, file))

            util.substitute_keywords_in_file(osp.join(self.pathMan.testDir, 'CMakeLists.txt'), {
                'name': self.pathMan.pluginName,
                'test_util': self.pathMan.testUtilDir.replace('\\', '/')
            })

        def extract_includes_from_premake():
            plugin_table = parse_premake_lua_table(self.pathMan.premakePluginLua)
            includes = list(plugin_table['sdk']['static']['includedirs'].values())
            return includes

        def sync_includes_from_premake():
            includes = extract_includes_from_premake()
            inserts = [f'include_directories({include})\n' for include in includes]
            cmakelists_file = osp.join(self.pathMan.testDir, 'CMakeLists.txt')
            util.substitute_lines_in_file(inserts, cmakelists_file,
                                          '# [PremakeDefinedIncludes]',
                                          '# [/PremakeDefinedIncludes]')

        lazy_download_catch2_src()
        lazy_copy_test_src()
        sync_includes_from_premake()

    def _build_test_project(self):
        util.run_cmd(
            [
                'cmake',
                '.',
                '-B',
                'build'
            ],
            cwd=self.pathMan.testDir
        )

    def _run_test(self):
        raise NotImplementedError('subclass it')


class _WindowsTestRunner(PluginTestRunner):
    def _build_test_project(self):
        super()._build_test_project()
        util.run_cmd(
            [
                'msbuild',
                'build\\test.sln',
                '/verbosity:quiet',
                '/property:Configuration=RelWithDebInfo',
            ],
            cwd=self.pathMan.testDir
        )

    def _run_test(self):
        divider = '-------------------------------------------------------------------------------'
        log_lines = [
            divider,
            'CPU Info'
        ]

        query_cpu_info_proc = util.run_cmd(['wmic', 'CPU', 'GET', 'name'])
        log_lines.extend(filter(None, query_cpu_info_proc.stdout.decode(util.LOCALE_CODEC).splitlines()))
        log_lines.append(divider)

        test_proc = util.run_cmd(
            [
                osp.join(self.pathMan.testDir, 'build\\RelWithDebInfo\\test.exe'),
                '--colour-mode', 'ansi',
                '--benchmark-samples', '10',
                '-s'
            ],
            cwd=self.pathMan.testDir
        )
        log_lines.extend(remove_ansi_color(test_proc.stdout.decode(util.LOCALE_CODEC)).splitlines())

        util.save_lines(osp.join(self.pathMan.testDir, 'test_benchmark_report.txt'), log_lines, addlineend=True)
