import importlib
import os
import os.path as osp

import kkpyutil as util

_PATCH_TAG = None


def wwise_year() -> int:
    wwise_root = os.getenv('WWISEROOT')
    if not wwise_root:
        raise EnvironmentError('WWISEROOT is not set')
    install_entry = util.load_json(osp.join(wwise_root, 'install-entry.json'))
    return int(install_entry['bundle']['version']['year'])


def reset_patch_cache():
    global _PATCH_TAG
    _PATCH_TAG = None


def patch_tag() -> str:
    global _PATCH_TAG
    if _PATCH_TAG is None:
        _PATCH_TAG = 'v2025' if wwise_year() >= 2025 else 'v2021'
    return _PATCH_TAG


def patch_dir() -> str:
    return osp.join(osp.dirname(__file__), patch_tag())


def patch_module(name: str):
    return importlib.import_module(f'wpe.wp_patch.{patch_tag()}.{name}')


def apply_platform_patches():
    importlib.import_module(f'wpe.wp_patch.{patch_tag()}.common.platform')
