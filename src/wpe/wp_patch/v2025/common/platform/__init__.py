"""
The content of this file includes portions of the AUDIOKINETIC Wwise Technology
released in source code form as part of the SDK installer package.

Commercial License Usage

Licensees holding valid commercial licenses to the AUDIOKINETIC Wwise Technology
may use this file in accordance with the end user license agreement provided
with the software or, alternatively, in accordance with the terms contained in a
written agreement between you and Audiokinetic Inc.

  Copyright (c) 2026 Audiokinetic Inc.
"""

import os
import os.path as osp


def basename_without_extension(path):
    return osp.splitext(osp.basename(path))[0]


def installed_in_sdk(module_name):
    return osp.isfile(osp.join(os.getenv('WWISEROOT'), 'Scripts/Build/Plugins/common/platform', f'{module_name}.py'))


def should_import(filename):
    module_name = basename_without_extension(filename)

    if module_name in ('android', 'ps5'):
        if module_name == 'ps5' and installed_in_sdk(module_name):
            return False
        return filename.endswith('.py') and filename != osp.basename(__file__)

    return installed_in_sdk(module_name) and filename.endswith(".py") and filename != osp.basename(__file__)


__all__ = [
    basename_without_extension(f)
    for f in os.listdir(osp.dirname(__file__))
    if should_import(f)
]
