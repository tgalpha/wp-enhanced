import logging
import re
import tomllib
import os.path as osp
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
from pathlib import Path

import kkpyutil as util

from wpe.pathman import PathMan


def overwrite_copy(src: str, dst: str):
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


def replace_in_basename(path: str, old: str, new: str):
    return osp.join(osp.dirname(path), osp.basename(path).replace(old, new))


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


def copy_template(relative, pathman: PathMan, is_forced=False):
    def _need_overwrite(_dst):
        if is_forced:
            return True
        if osp.isfile(_dst):
            content = util.load_text(_dst)
            return '[wp-enhanced template]' not in content
        return True

    src = osp.join(pathman.templatesDir, relative)
    dst = replace_in_basename(osp.join(pathman.root, relative), 'ProjectName', pathman.pluginName)
    if not _need_overwrite(dst):
        logging.info(f'Skip copying template "{osp.basename(src)}". Use -f to force overwrite.')
        return dst
    if osp.isfile(src):
        overwrite_copy(src, dst)
        util.substitute_keywords_in_file(dst,
                                         {
                                             'name': pathman.pluginName,
                                             'display_name': pathman.pluginName,
                                             'plugin_id': pathman.pluginId,
                                         })
        return dst
    else:
        raise FileNotFoundError(f'File not found: {src}')
