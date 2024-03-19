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

from __future__ import absolute_import
import os
# [wp-enhanced patch] import android platform patch
from wpe.wp_patch.common.command.android import build, SUPPORTED_BUILD_SYSTEMS
# [/wp-enhanced patch]
from common.registry import PlatformInfo, PremakeInfo, BuildInfo, PackageInfo, platform_registry

platform_registry["Android"] = PlatformInfo(
    name="Android",
    premake=PremakeInfo(
        actions=("androidmk",)
    ),
    build=BuildInfo(
        command=build,
        configurations=("Debug", "Profile", "Release"),
        archs=("armeabi-v7a", "x86", "arm64-v8a", "x86_64"),
        on=SUPPORTED_BUILD_SYSTEMS,
        require_configuration=True
    ),
    package=PackageInfo(
        artifacts = [
            os.path.join("SDK", "Android_*", "*", "bin", "lib{plugin_name}.so"),
            os.path.join("SDK", "Android_*", "*", "lib", "lib{plugin_name}*.a"),
        ]
    )
)
