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
import glob
import multiprocessing
import os
import platform
import shutil
import subprocess
from common.constant import PLUGIN_NAME, WWISE_ROOT
from common.hook import invoke, POSTBUILD_HOOK
from common.registry import platform_registry

SUPPORTED_BUILD_SYSTEMS = ("Windows","Linux")

def build(target, config, hooks):
    platform_info = platform_registry.get(target)
    for arch in platform_info.build.archs:
        build_tool = os.path.join(os.environ["NDKROOT"], "ndk-build")
        # [wp-enhanced patch] use WWISESDK env var (symlinked) to get the Wwise SDK path to avoid space in path issue
        out_dir_root = os.path.join(os.getenv('WWISESDK'), "Android_" + arch)
        # [/wp-enhanced patch]
        application_mk = " NDK_APPLICATION_MK=" + PLUGIN_NAME + "_Android_application.mk"
        libs_out = " NDK_LIBS_OUT=" + os.path.join(out_dir_root, config, "libs").replace("\\", "/")
        ndk_out = " NDK_OUT=" + os.path.join(out_dir_root, config, "lib").replace("\\", "/") # the missing "s" at lib is on purpose
        ndk_app_out = " NDK_APP_OUT=" + out_dir_root.replace("\\", "/")
        target_out = " TARGET_OUT=" + os.path.join(out_dir_root, config, "lib").replace("\\", "/")

        if platform.system() == "Linux":
            ndk_project_path = "."
        else:
            ndk_project_path = ".\\"

        build_command = "{} all -j {} NDK_PROJECT_PATH={} PM5_CONFIG={}".format(
            build_tool,
            str(multiprocessing.cpu_count()),
            ndk_project_path,
            config.lower() + "_android_" + arch + application_mk + libs_out + ndk_out + ndk_app_out + target_out
        )

        print("Building {} in {} using ndk-build. Build Command:\n{}".format(target, config, build_command))
        res = subprocess.Popen(build_command, shell=True).wait()
        if res != 0:
            return res

        # need to copy dynamic lib to final destination
        so_dstdir = os.path.join(out_dir_root, config, "bin")
        if not os.path.exists(so_dstdir):
            os.makedirs(so_dstdir)

        so_glob = os.path.join(out_dir_root, config, "libs", arch, "lib*.so")
        for so_fname in glob.glob(so_glob):
            shutil.copy(so_fname, so_dstdir)

        invoke(POSTBUILD_HOOK, hooks, target, config, arch)

    return 0
