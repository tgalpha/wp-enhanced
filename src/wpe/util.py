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
