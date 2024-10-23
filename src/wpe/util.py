import logging
import os
import re
import shutil
import subprocess
import tomllib
import os.path as osp
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
from pathlib import Path

import kkpyutil as util
import toml

from wpe.pathman import PathMan


class ParserHelp:
    def __init__(self, name, parser):
        self.name = name
        self.parser = parser
        self.aliases = []

    def add_alias(self, alias):
        self.aliases.append(alias)

    def format_help(self, indent=4):
        name_with_aliases = f'{self.name} ({", ".join(self.aliases)})' if self.aliases else self.name
        return f'''{" "*indent}{name_with_aliases}: {self.parser.description}
    {" "*indent}{self.parser.format_usage()}'''


def generate_integrated_description(parser, subparsers):
    processed_parsers = {}
    for name, subparser in subparsers.choices.items():
        if subparser.prog in processed_parsers:
            processed_parsers[subparser.prog].add_alias(name)
            continue
        parser_help = ParserHelp(name, subparser)
        processed_parsers[subparser.prog] = parser_help
    parser.description = "\n\n".join((h.format_help() for h in processed_parsers.values()))


def overwrite_copy(src, dst):
    if osp.isfile(src):
        copy_file(src, dst)

    if osp.isdir(src):
        copy_tree(src, dst)


def path_is_under(child: str, parent: str) -> bool:
    return Path(parent) in Path(child).parents


def load_toml(path):
    with open(path, 'rb') as f:
        toml_content = tomllib.load(f)
    return toml_content


def save_toml(path, content):
    with open(path, 'w') as f:
        toml.dump(content, f)


def git_mv(src, dst):
    try:
        util.run_cmd(['git', 'mv', src, dst])
    except subprocess.CalledProcessError:
        # git ignored files will raise error, fallback to os.rename
        os.rename(src, dst)
    except Exception as e:
        logging.error(f'Error moving {src} to {dst} with `git mv`: {e}')
        raise e


def replace_in_basename(path, old: str, new: str, count=-1):
    return osp.join(osp.dirname(path), osp.basename(path).replace(old, new, count))


def remove_path(path, ignore_errors=True):
    if osp.isfile(path):
        os.remove(path)
    if osp.isdir(path):
        shutil.rmtree(path, ignore_errors=ignore_errors)


def replace_content_in_file(file_path, org, dst):
    content = util.load_text(file_path)
    util.save_text(file_path, content.replace(org, dst))


def path_is_under_git_repo(path: str) -> bool:
    git_exe = shutil.which('git')
    if not git_exe:
        return False
    try:
        res = util.run_cmd([git_exe, '-C', path, 'rev-parse', '--is-inside-work-tree'])
        return res.stdout.decode().strip() == 'true'
    except Exception as e:
        logging.error(f'Error checking git repo: {e}')
        return False


def remove_ansi_color(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def auto_add_line_end(lines: list[str]):
    for i, line in enumerate(lines):
        if not line.endswith('\n'):
            lines[i] += '\n'
    return lines


def add_indent(lines: list[str], indent: int):
    return [f'{" " * indent}{line}' for line in lines]


def copy_template(relative, pathman: PathMan, is_forced=False, lib_suffix='', add_suffix_after_project_name=False, lazy_create=False):
    def _need_overwrite(_dst):
        if is_forced or not osp.isfile(_dst):
            return True
        content = util.load_text(_dst)
        return '[wp-enhanced template]' not in content

    src = osp.join(pathman.templatesDir, relative)
    assert osp.isfile(src)
    dst = replace_in_basename(osp.join(pathman.root, relative), 'ProjectName',
                              pathman.pluginName + lib_suffix if add_suffix_after_project_name else pathman.pluginName)
    if not osp.isfile(dst) and not lazy_create:
        logging.info(f'Destination file "{osp.basename(dst)}" does not exist. Skipping...')
        return None

    if not _need_overwrite(dst):
        logging.info(f'Skip copying template "{osp.basename(src)}". Use -f to force overwrite.')
        return dst
    overwrite_copy(src, dst)
    util.substitute_keywords_in_file(dst,
                                     {
                                         'name': pathman.pluginName,
                                         'display_name': pathman.pluginName,
                                         'plugin_id': pathman.pluginId,
                                         'suffix': lib_suffix,
                                     })
    return dst


def parse_premake_lua_table(premake_plugin_lua_path):
    from lupa import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals()['_AK_PREMAKE'] = True
    plugin_table = lua.execute(util.load_text(premake_plugin_lua_path))
    return plugin_table


def convert_to_wsl_path(path: str):
    abs_path = osp.abspath(path)
    driver, relpath = abs_path.split(':\\')
    relpath = relpath.replace("\\", "/")
    return f'/mnt/{driver.lower()}/{relpath}'
