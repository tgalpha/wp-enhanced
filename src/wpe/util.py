import re
import tomllib
import os.path as osp
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
from pathlib import Path

__all__ = [
    'overwrite_copy',
    'path_is_under',
    'load_toml',
    'replace_in_basename',
    'remove_ansi_color',
    'auto_add_line_end',
    'add_indent',
]


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
