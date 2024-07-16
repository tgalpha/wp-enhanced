#!/usr/bin/env python3

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

import argparse
import os
import re
import subprocess
import sys
import os.path as osp
from common.constant import PLUGIN_NAME, PREMAKE, PROJECT_ROOT, WWISE_ROOT
from common.platform import *
# [wp-enhanced patch] import platform patch
from wpe.wp_patch.common.platform import *
# [/wp-enhanced patch]
from common.registry import platform_registry, get_supported_platforms, is_authoring_target

SUPPORTED_PLATFORMS = get_supported_platforms("premake")

def run(argv):
    # parse the command line
    parser = argparse.ArgumentParser(description="Audiokinetic Inc. premake tool for plugins")
    parser.add_argument("platform", metavar="platform", choices=SUPPORTED_PLATFORMS, help="platform to premake ({})".format(", ".join(SUPPORTED_PLATFORMS)))
    parser.add_argument("--debugger", help="Enable lua debugger for premake scripts", action="store_true")
    args = parser.parse_args(argv)

    # prepare premake parameters
    platform_info = platform_registry.get(args.platform)
    pm_actions = platform_info.premake.actions

    pm_scripts = "--scripts={};{};{}".format(
        os.path.join(os.getenv('WWISESDK'), "source", "Build"),
        os.path.join(WWISE_ROOT, "Scripts", "Premake"),
        os.path.join(WWISE_ROOT, "Scripts", "Build"))

    pm_file = "--file={}".format(
        os.path.join(osp.dirname(__file__), "premakePlugins.lua"))

    # Default to PlatformInfo name if not specified
    pm_platform = "--os={}".format(
        platform_info.premake.platform or
        re.search(r"\w+(?=(_))|\w+", platform_info.name).group(0).lower()
    )

    pm_plugin_dir = "--plugindir={}".format(PROJECT_ROOT)

    pm_is_authoring = "--authoring={}".format("yes" if is_authoring_target(platform_info.name) else "no")

    # run premake
    for pm_action in pm_actions:
        cmd = [PREMAKE, pm_scripts, pm_file, pm_action, pm_platform, pm_plugin_dir, pm_is_authoring]
        if args.debugger:
            cmd.append("--debugger")

        print("Premake Command: " + str(cmd))
        res = subprocess.Popen(cmd).wait()
        if res != 0:
            sys.exit(res)

if __name__ == "__main__":
    run(sys.argv[1:])
