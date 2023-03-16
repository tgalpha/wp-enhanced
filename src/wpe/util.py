import os.path as osp
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
from pathlib import Path


__all__ = [
    'overwrite_copy',
    'path_is_under'
]


def overwrite_copy(src: str, dst: str):
    if osp.isfile(src):
        copy_file(src, dst)

    if osp.isdir(src):
        copy_tree(src, dst)


def path_is_under(child: str, parent: str) -> bool:
    return Path(parent) in Path(child).parents


