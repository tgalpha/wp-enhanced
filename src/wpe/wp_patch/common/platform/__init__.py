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


def installed_in_sdk(module_name):
    return os.path.isfile(os.path.join(os.getenv('WWISEROOT'), 'Scripts/Build/Plugins/common/platform', f'{module_name}.py'))


__all__ = [
    module_name
    for f in os.listdir(os.path.dirname(__file__))
    if installed_in_sdk(module_name := os.path.basename(f)[:-3]) and f.endswith(".py") and f != os.path.basename(__file__)
]
