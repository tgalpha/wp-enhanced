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
from common.command.vs import build, SUPPORTED_BUILD_SYSTEMS
from common.registry import PlatformInfo, PremakeInfo, BuildInfo, PackageInfo, platform_registry

platform_registry["PS5"] = PlatformInfo(
    name="PS5",
    premake=PremakeInfo(
        # [wp-enhanced patch] PS5 SDK integrate with vs2019 now
        actions=("vs2019",)
    ),
    build=BuildInfo(
        command=build,
        configurations=("Debug", "Profile", "Release"),
        archs=("Prospero",),
        # [wp-enhanced patch] PS5 SDK integrate with vs2019 now
        toolsets=("vc160",),
        on=SUPPORTED_BUILD_SYSTEMS,
        require_configuration=True
    ),
    package=PackageInfo(
        is_licensed=True,
        artifacts=[
            os.path.join("SDK", "PS5", "*", "bin", "{plugin_name}.prx"),
            os.path.join("SDK", "PS5", "*", "bin", "{plugin_name}_stub.a"),
            os.path.join("SDK", "PS5", "*", "lib", "lib{plugin_name}*.a"),
        ]
    )
)
