"""
The content of this file includes portions of the AUDIOKINETIC Wwise Technology
released in source code form as part of the SDK installer package.

Commercial License Usage

Licensees holding valid commercial licenses to the AUDIOKINETIC Wwise Technology
may use this file in accordance with the end user license agreement provided
with the software or, alternatively, in accordance with the terms contained in a
written agreement between you and Audiokinetic Inc.

  Copyright (c) 2021 Audiokinetic Inc.
"""

import os
import os.path as osp

import packaging.version as pkg_ver

from wpe.wp_wrapper import WpWrapper


def basename_without_extension(path):
    return osp.splitext(osp.basename(path))[0]


def installed_in_sdk(module_name):
    return osp.isfile(osp.join(os.getenv('WWISEROOT'), 'Scripts/Build/Plugins/common/platform', f'{module_name}.py'))


def should_import(filename):
    module_name = basename_without_extension(filename)

    if module_name == 'ps5':
        wp_wrapper = WpWrapper()
        wwise_version = pkg_ver.parse(wp_wrapper.wwiseVersion)
        # Wwise from 2021.1.12 and up supports multiple Prospero SDK versions
        if wwise_version >= pkg_ver.parse('2021.1.12'):
            return False
    return installed_in_sdk(module_name) and filename.endswith(".py") and filename != osp.basename(__file__)


__all__ = [
    basename_without_extension(f)
    for f in os.listdir(osp.dirname(__file__))
    if should_import(f)
]
