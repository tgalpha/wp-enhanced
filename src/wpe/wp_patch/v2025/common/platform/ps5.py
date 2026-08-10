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

from __future__ import absolute_import
import os
from common.constant import WWISE_ROOT
from common.command.vs import build, SUPPORTED_BUILD_SYSTEMS
from common.registry import PlatformInfo, PremakeInfo, BuildInfo, PackageInfo, platform_registry

platform_registry["PS5"] = PlatformInfo(
    name="PS5",
    premake=PremakeInfo(
        actions=("vs2017", "vs2019", "vs2022")
    ),
    build=BuildInfo(
        command=build,
        configurations=("Debug", "Profile", "Release"),
        archs=("Prospero",),
        toolsets=("vc160",),
        toolchain_env_script=os.path.join(WWISE_ROOT, "Scripts/ToolchainSetup/PS5/GetToolchainEnv.py"),
        toolchain_vers=os.path.join(WWISE_ROOT, "Scripts/ToolchainSetup/PS5/ToolchainVers.txt"),
        on=SUPPORTED_BUILD_SYSTEMS,
        require_configuration=True
    ),
    package=PackageInfo(
        is_licensed=True,
        artifacts=[
            os.path.join("SDK", "PS5_*", "*", "bin", "{plugin_name}.prx"),
            os.path.join("SDK", "PS5_*", "*", "bin", "{plugin_name}_stub.a"),
            os.path.join("SDK", "PS5_*", "*", "lib", "lib{plugin_name}*.a"),
        ]
    )
)
