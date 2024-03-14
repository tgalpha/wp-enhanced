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
import platform
import sys
import re
from common.constant import PLUGIN_NAME, PROJECT_ROOT
from common.platform import *
from common.registry import platform_registry, get_supported_platforms
from common.util import exit_with_error

SUPPORTED_PLATFORMS = get_supported_platforms("build", platform.system())

def run(argv):
    # parse the command line
    parser = argparse.ArgumentParser(description="Audiokinetic Inc. build tool for plugins")
    parser.add_argument("platform", metavar="platform", choices=SUPPORTED_PLATFORMS, help="platform to build ({})".format(", ".join(SUPPORTED_PLATFORMS)))
    parser.add_argument("-c", "--configuration", help="configuration to build (Debug, Release, Profile, ...).")
    parser.add_argument("-x", "--archs", default=[], nargs='+', help="architecture to build (x32, x64, ...).")
    parser.add_argument("-t", "--toolset", help="toolset used to build on Windows platforms (vc150, vc160, vc170).")
    parser.add_argument("-f", "--build-hooks-file", help="path to a Python file defining one or more of the supported hooks (postbuild) to be called at various step during the build process")
    parser.add_argument("--toolchain-vers", help="Path to a \'ToolchainVers\' text file, containing a list of supported toolchain versions to pass to the platform's toolchain_setup script, to setup and define a set of env-vars to re-run each build step with.")
    parser.add_argument("--toolchain-env-script", help="Path to a \'GetToolchainEnv\' script, which, when executed with a version provided by the toolchain-vers file, returns a comma separated list of environment variables to apply for a build step.")
    args = parser.parse_args(argv)

    # import the build hooks
    build_hooks = None
    if args.build_hooks_file:
        sys.path.append(os.path.join(PROJECT_ROOT))
        if not os.path.exists(args.build_hooks_file):
            exit_with_error("Missing build hooks file {} at {}".format(args.build_hooks_file, PROJECT_ROOT))
        try:
            build_hooks = __import__(os.path.splitext(args.build_hooks_file)[0])
        except Exception as e:
            exit_with_error("Invalid build hooks file {} at {}\n{}".format(args.build_hooks_file, PROJECT_ROOT, str(e)))

    # handle platform-specific command line specificites
    platform_info = platform_registry.get(args.platform)

    invalid_archs = set(args.archs) - set(platform_info.build.archs)
    if invalid_archs:
        print("error: Invalid architecture(s) '{}' for target {}.".format(invalid_archs, platform_info.name))
        print("supported architectures: {}".format(', '.join(platform_info.build.archs)))
        return 1

    if not args.toolset:
        if platform_info.build.require_toolset:
            print("error: 'Toolset' argument for target {} needs to be specified using -t or --toolset, -h for more details.".format(platform_info.name))
            print("supported toolsets: {}".format(', '.join(platform_info.build.toolsets)))
            return 1
    elif args.toolset not in platform_info.build.toolsets:
        print("error: Invalid toolset '{}' for target {}.".format(args.toolset, platform_info.name))
        print("supported toolsets: {}".format(', '.join(platform_info.build.toolsets)))
        return 1

    if not args.configuration:
        if platform_info.build.require_configuration:
            exit_with_error("'Configuration' argument for target {} needs to be specified using -c or --configuration, -h for more details.".format(platform_info.name))

        print("Building {} for {}.".format(PLUGIN_NAME, platform_info.name))
    else:
        if args.configuration not in platform_info.build.configurations:
            print("error: Invalid configuration '{}' for target {}.".format(args.configuration, platform_info.name))
            print("supported configurations: {}".format(', '.join(platform_info.build.configurations)))
            return 1

        print("Building {} for {} in {}...".format(PLUGIN_NAME, platform_info.name, args.configuration))

    if args.archs:
        # build for the requested architecture instead of building them all
        platform_info.build.archs = args.archs

    if args.toolset:
        # build for the requested toolset instead of building them all
        platform_info.build.toolsets = (args.toolset,)

    if args.toolchain_vers:
        # specify an override location for the toolchain vers file
        platform_info.build.toolchain_vers = args.toolchain_vers

    if args.toolchain_env_script:
        # specify an override location for the toolchain env script
        platform_info.build.toolchain_env_script = args.toolchain_env_script

    # run the build
    return platform_info.build.command(platform_info.name, args.configuration, build_hooks)

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
