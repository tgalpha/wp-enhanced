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
import errno
import json
from glob import glob
import os
import shutil
import subprocess
import sys
import tarfile
import re
import codecs
from common.constant import PLUGIN_NAME, PROJECT_ROOT, WWISE_ROOT, XZ_UTILS
from common.platform import *
from common.registry import platform_registry, get_supported_platforms, is_documentation, is_authoring_target
from common.util import exit_with_error, strip_comments
from common.version import VersionArgParser

SUPPORTED_PLATFORMS = get_supported_platforms("package")
DEFAULT_ADDITIONAL_ARTIFACT_FILE = "additional_artifacts.json"

def find_artifacts(args):
    # search for artifacts using the glob patterns
    artifacts_found = []
    artifacts_found_in_project = []

    platform_info = platform_registry.get(args.platform)
    # [wp-enhanced] exclude pdb and debug artifacts
    debug_artifacts_folders = {'Debug', 'Debug(StaticCRT)', 'Debug-iphoneos', 'Debug-iphonesimulator'}
    for artifact_glob in (pattern for pattern in platform_info.package.artifacts if not pattern.endswith(".pdb")):
        for artifact in glob(os.path.join(WWISE_ROOT, artifact_glob.format(plugin_name=PLUGIN_NAME))):
            sections = set(artifact.split(os.path.sep))
            if sections & debug_artifacts_folders:
                continue
            artifacts_found.append(artifact)
            print("Found {}".format(artifact))
    # [/wp-enhanced]

    # validate additional artifacts
    for artifact_glob in args.additional_artifacts:
        artifacts = glob(os.path.join(WWISE_ROOT, os.path.normpath(artifact_glob)))
        if not artifacts:
            exit_with_error("Could not find additional artifact at {}".format(artifact_glob))

        for artifact in artifacts:
            artifacts_found.append(artifact)
            print("Added {}".format(artifact))

    # do the same with additional artifacts coming from a json file
    if args.additional_artifacts_file:
        try:
            with codecs.open(os.path.join(PROJECT_ROOT, args.additional_artifacts_file), "r", "utf-8") as f:
                additional_artifacts = json.loads(strip_comments(f.read()))
                platform_name = "Authoring" if "Authoring" in platform_info.name else platform_info.name
                if platform_name in additional_artifacts:
                    platform_additional_artifacts = additional_artifacts.get(platform_name)
                    for entry in platform_additional_artifacts:
                        if isinstance(entry, dict):
                            # we have a dictionary of destination -> source globs that are relative to PROJECT_ROOT
                            for dest, sources in entry.items():
                                for artifact_glob in sources:
                                    for artifact in glob(os.path.join(PROJECT_ROOT, os.path.normpath(artifact_glob))):
                                        artifacts_found_in_project.append((artifact, dest))
                                        print("Added {}".format(artifact))
                        else:
                            # we have a source glob that is relative to WWISE_ROOT
                            for artifact in glob(os.path.join(WWISE_ROOT, os.path.normpath(entry))):
                                artifacts_found.append(artifact)
                                print("Added {}".format(artifact))
        except IOError:
            if args.additional_artifacts_file != DEFAULT_ADDITIONAL_ARTIFACT_FILE:
                # only report error if user specified a non-default value
                exit_with_error("Missing additional artifacts file {} at {}".format(args.additional_artifacts_file, PROJECT_ROOT))
        except ValueError as e:
            exit_with_error("Invalid additional artifacts file {} at {}\n{}".format(args.additional_artifacts_file, PROJECT_ROOT, str(e)))

    return (artifacts_found, artifacts_found_in_project)

def run(argv):
    # parse the command line
    parser = argparse.ArgumentParser(description="Audiokinetic Inc. packaging tool for plugins")
    parser.add_argument("-v", "--version", action=VersionArgParser, help="version of the package (formatted as 'year.major.minor.build')")
    parser.add_argument("platform", metavar="platform", choices=SUPPORTED_PLATFORMS, help="platform to package ({})".format(", ".join(SUPPORTED_PLATFORMS)))
    parser.add_argument("-a", "--additional-artifacts", nargs="*", default=[], help="path to additional artifacts to package (must be relative to the root of your Wwise installation, supports glob patterns)")
    parser.add_argument("-f", "--additional-artifacts-file", default=DEFAULT_ADDITIONAL_ARTIFACT_FILE, help="path to a JSON file listing the paths to additional artifacts to package for each platform, defaults to {}".format(DEFAULT_ADDITIONAL_ARTIFACT_FILE))
    parser.add_argument("-c", "--copy-artifacts", action="store_true", help="copy artifacts instead of packaging them, this option only applies to additional artifact files with destination -> sources entries")
    args = parser.parse_args(argv)

    platform_info = platform_registry.get(args.platform)

    if args.copy_artifacts:
        # run in copy mode, copy artifacts from the PROJECT_ROOT to the WWISE_ROOT
        print("Copying artifacts for {}...".format(platform_info.name))

        artifacts_found, artifacts_found_in_project = find_artifacts(args)
        if not artifacts_found and not artifacts_found_in_project:
            exit_with_error("Nothing to copy!")

        for (artifact, dest) in artifacts_found_in_project:
            dest = os.path.join(WWISE_ROOT, os.path.normpath(dest))
            try:
                os.makedirs(dest)
            except OSError as e:
                if e.errno != errno.EEXIST: # for python2 compatibility, ideally we would use the exist_ok param in makedirs
                    raise

            print("Copied {} to {}".format(artifact, dest))
            shutil.copy(artifact, dest)
    else:
        # run in packaging mode, compress everything into an archive
        if not args.version:
            exit_with_error("'Version' argument needs to be specified using -v or --version, -h for more details.")

        print("Packaging {} for {}...".format(PLUGIN_NAME, platform_info.name))

        artifacts_found, artifacts_found_in_project = find_artifacts(args)
        if not artifacts_found and not artifacts_found_in_project:
            print("Nothing to package!")
            return 0

        formatted_plugin_version = "v{}.{}.{}_Build{}".format(
            args.version.year, args.version.major, args.version.minor, args.version.build)

        if is_documentation(platform_info.name):
            formatted_platforms = ["Authoring.{}".format(platform_info.name)]
        elif is_authoring_target(platform_info.name):
            formatted_platforms = [{
                                       "Authoring_Windows": "{}_{}.x64",
                                       "Authoring_Mac": "{}_{}.macosx_gmake",
                                       "Authoring_Linux": "{}_{}.linux_gmake"
                                   }.get(platform_info.name, "{}").format(platform_info.name, config) for config in ["Debug", "Release"]
                                   ]
        else:
            formatted_platforms = ["SDK.{}".format(platform_info.name)]

        compressed_archive_names = [
            "{}_{}_{}.tar.xz".format(
                PLUGIN_NAME,
                formatted_plugin_version,
                formatted_platform
            ) for formatted_platform in formatted_platforms
        ]

        output_name_re = re.compile(r"^" + PLUGIN_NAME + r"_v\d+\.\d+\.\d+_Build\d+_(Authoring|Authoring_Windows|Authoring_Linux|Authoring_Mac)_(?P<config>Debug|Release)(?:\.(.*))?\.tar\.xz$")

        def is_authoring_debug_package(output_name):
            match = re.match(output_name_re, output_name)
            return False if match is None else match.group("config") == "Debug"

        def is_authoring_release_package(output_name):
            match = re.match(output_name_re, output_name)
            return False if match is None else match.group("config") == "Release"

        def is_data_artifact(artifact):
            return os.path.join("Authoring", "Data") in artifact or os.path.join("Authoring", "Help") in artifact

        def is_debug_artifact(artifact):
            artifact_re = re.compile(r"([/\\])Debug\1")
            return bool(artifact_re.search(artifact))

        # [wp-enhanced] add artifacts recursively, avoid adding empty folders
        def archive_artifacts(output_name, write_mode):
            def need_add(_artifact):
                if is_authoring_debug_package(output_name):
                    if not is_debug_artifact(_artifact) or is_data_artifact(_artifact):
                        return False
                elif is_authoring_release_package(output_name) and is_debug_artifact(_artifact):
                    return False
                return True

            artifacts_dst_pair: list[tuple[str, str]] = []
            for artifact in artifacts_found:
                if need_add(artifact):
                    print("Compressing {}...".format(artifact))
                    artifacts_dst_pair.append((artifact, os.path.relpath(artifact, WWISE_ROOT)))
            for (artifact, dest) in artifacts_found_in_project:
                if need_add(artifact):
                    print("Compressing {}...".format(artifact))
                    artifacts_dst_pair.append((artifact, os.path.join(dest, os.path.basename(artifact))))

            if not artifacts_dst_pair:
                return
            with tarfile.open(output_name, write_mode, format=tarfile.GNU_FORMAT) as tar:
                for artifact, dest in artifacts_dst_pair:
                    tar.add(artifact, dest, recursive=True)
        # [/wp-enhanced]

        for compressed_archive_name in compressed_archive_names:
            try:
                archive_artifacts(compressed_archive_name, "w:xz")
            except tarfile.CompressionError:
                # xz compression isn't supported on older versions of tarfile
                archive_name = compressed_archive_name[:-3]
                archive_artifacts(archive_name, "w")

                res = subprocess.Popen([XZ_UTILS, "-zf", archive_name]).wait()
                if res != 0:
                    return res

            print("Wrote {}".format(compressed_archive_name))

    return 0

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
