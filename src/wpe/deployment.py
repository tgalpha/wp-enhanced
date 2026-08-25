import glob
import json
import os
import os.path as osp
import re
import zipfile
import tarfile
import lzma
from typing import Optional

import kkpyutil as util

from wpe.pathman import PathMan
import wpe.util as wpe_util

_ARCHIVE_NAME_RE = re.compile(
    r'^(?P<plugin>.+)_v(?P<wwise_version>\d+\.\d+\.\d+)_Build(?P<build>\d+)\.zip$'
)


class _Package:
    def __init__(self, meta_dict):
        self.meta = meta_dict

    def source_name(self) -> str:
        return self.meta['sourceName']

    def is_sdk_package(self) -> bool:
        return self.belong_to_packages() == 'SDK'

    def is_authoring_package(self) -> bool:
        return self.belong_to_packages() == 'Authoring'

    def belong_to_packages(self):
        return self._get_group_value_by_id('Packages')

    def deployment_platforms(self):
        return self._get_group_value_by_id('DeploymentPlatforms')

    def _get_group_value_by_id(self, group_id):
        for group in self.meta['groups']:
            if group['groupId'] == group_id:
                return group['groupValueId']


class Deployment:
    """
    Deploy or delete a plugin to a game project.
    """
    def __init__(self, args):
        self.args = args
        self.projectRoot = args.destProject
        self.pluginDeployDir = ''

    @staticmethod
    def create(args):
        if osp.isfile(osp.join(args.destProject, 'Authoring', 'x64', 'Release', 'bin', 'Wwise.exe')):
            print('Target: Wwise Authoring detected.')
            return AuthoringDeployment(args)
        if glob.glob(osp.join(args.destProject, '*.uproject')):
            print('Target: UE project detected.')
            return UEDeployment(args)
        raise NotImplementedError(f'Not implemented for this target, currently only supports UE.')

    def deploy(self):
        archive = self._lazy_find_archive()
        with zipfile.ZipFile(archive, 'r') as zip_ref:
            try:
                bundle_file = next(f for f in zip_ref.filelist if f.filename.endswith('bundle.json'))
            except StopIteration:
                raise FileNotFoundError('No bundle.json found in archive. Invalid archive?')
            with zip_ref.open(bundle_file) as f:
                content = f.read().decode('utf-8')
                bundle = json.loads(content)
                print(f'Deploying {bundle["name"]} (id: {bundle["id"]})...')
                for file in bundle['files']:
                    pkg = _Package(file)
                    self._deploy_package(zip_ref, pkg)

    def _deploy_package(self, zip_ref: zipfile.ZipFile, pkg: _Package):
        raise NotImplementedError('subclass it')

    def clean(self):
        name = self.args.name or PathMan().pluginName
        print(f"Cleaning {name}...")
        paths = glob.glob(rf'{self.pluginDeployDir}\**\*{name}*',
                       recursive=True)
        for p in paths:
            print(f'Removing {p}')
            wpe_util.remove_path(p)

    def _lazy_find_archive(self):
        if osp.isfile(self.args.archive):
            return self.args.archive
        pathman = PathMan()
        dist_dir = pathman.distDir
        plugin_name = pathman.pluginName
        wwise_version_code = self._current_wwise_version_code()
        archives = glob.glob(osp.join(dist_dir, '*.zip'))
        if not archives:
            raise FileNotFoundError(f'No archive found in dist directory: {dist_dir}')

        matching = []
        for archive in archives:
            parsed = self._parse_archive_name(archive)
            if not parsed:
                continue
            if parsed['plugin'] == plugin_name and parsed['wwise_version'] == wwise_version_code:
                matching.append(archive)

        if not matching:
            available = ', '.join(sorted(osp.basename(archive) for archive in archives))
            raise FileNotFoundError(
                f'No archive found for plugin "{plugin_name}" and Wwise {wwise_version_code} '
                f'in {dist_dir}. Available archives: {available}'
            )
        selected = max(matching, key=os.path.getmtime)
        print(f'Using archive: {osp.basename(selected)}')
        return selected

    @staticmethod
    def _current_wwise_version_code() -> str:
        wwise_root = os.getenv('WWISEROOT')
        if not wwise_root:
            raise EnvironmentError('WWISEROOT is not set')
        install_entry = util.load_json(osp.join(wwise_root, 'install-entry.json'))
        version = install_entry['bundle']['version']
        return f'{version["year"]}.{version["major"]}.{version["minor"]}'

    @staticmethod
    def _parse_archive_name(archive_path: str) -> Optional[dict[str, str]]:
        match = _ARCHIVE_NAME_RE.match(osp.basename(archive_path))
        if not match:
            return None
        return match.groupdict()

    @staticmethod
    def _get_plugin_name_from_archive(archive):
        parsed = Deployment._parse_archive_name(archive)
        if parsed:
            return parsed['plugin']
        return osp.basename(archive).split('_')[0]


class UEDeployment(Deployment):
    def __init__(self, args):
        super().__init__(args)
        self.pluginDeployDir = osp.join(self.projectRoot, 'Plugins', 'Wwise', 'ThirdParty')

    def _deploy_package(self, zip_ref: zipfile.ZipFile, pkg: _Package):
        if not pkg.is_sdk_package():
            return

        zip_info = next(f for f in zip_ref.filelist if f.filename.endswith(pkg.source_name()))
        with zip_ref.open(zip_info) as f:
            with lzma.open(f) as xz:
                with tarfile.open(fileobj=xz) as tar:
                    is_android = pkg.deployment_platforms() == 'Android'
                    for member in tar.getmembers():
                        new_name = member.name.removeprefix('SDK/')
                        if is_android:
                            for arch in ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'):
                                new_name = new_name.replace(f'Android_{arch}', f'Android/{arch}')
                        member.name = new_name
                    members = tar.getmembers()
                    parents = {m.name.split('/')[0] for m in members if m.name}
                    if any(osp.isdir(osp.join(self.pluginDeployDir, p)) for p in parents):
                        tar.extractall(self.pluginDeployDir)
                        print('\n'.join([extracted for member in members if osp.isfile(
                            extracted := osp.normpath(osp.join(self.pluginDeployDir, member.name)))]))
                    else:
                        print(f'Parent directory does not exist, skip: {", ".join(sorted(parents))}')


class AuthoringDeployment(Deployment):
    def __init__(self, args):
        super().__init__(args)
        self.pluginDeployDir = self.projectRoot

    def _deploy_package(self, zip_ref: zipfile.ZipFile, pkg: _Package):
        if not pkg.is_authoring_package():
            return

        zip_info = next(f for f in zip_ref.filelist if f.filename.endswith(pkg.source_name()))
        with zip_ref.open(zip_info) as f:
            with lzma.open(f) as xz:
                with tarfile.open(fileobj=xz) as tar:
                    tar.extractall(self.pluginDeployDir)
                    print('\n'.join([extracted for member in tar.getmembers() if osp.isfile(
                        extracted := osp.normpath(osp.join(self.pluginDeployDir, member.name)))]))
