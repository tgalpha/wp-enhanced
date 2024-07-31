import glob
import json
import os
import os.path as osp
import zipfile
import tarfile
import lzma

from wpe.pathman import PathMan


class _Package:
    def __init__(self, meta_dict):
        self.meta = meta_dict

    def should_deploy(self, target_dir):
        return self.source_name().endswith('.tar.xz') and self.is_sdk_package()

    def source_name(self) -> str:
        return self.meta['sourceName']

    def is_sdk_package(self) -> bool:
        return self.belong_to_packages() == 'SDK'

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
                    if pkg.should_deploy(self.projectRoot):
                        self._deploy_package(zip_ref, pkg)

    def _deploy_package(self, zip_ref: zipfile.ZipFile, pkg: _Package):
        raise NotImplementedError('subclass it')

    def clean(self):
        name = self.args.name or PathMan().pluginName
        print(f"Cleaning {name}...")
        fs = glob.glob(rf'{self.pluginDeployDir}\**\*{name}*',
                       recursive=True)
        for f in fs:
            print(f'Removing {f}')
            os.remove(f)

    def _lazy_find_archive(self):
        if osp.isfile(self.args.archive):
            return self.args.archive
        pathman = PathMan()
        dist_dir = pathman.distDir
        # find the latest archive
        archives = glob.glob(osp.join(dist_dir, '*.zip'))
        if not archives:
            raise FileNotFoundError('No archive found in dist directory.')
        return max(archives, key=os.path.getctime)

    @staticmethod
    def _get_plugin_name_from_archive(archive):
        return osp.basename(archive).split('_')[0]


class UEDeployment(Deployment):
    def __init__(self, args):
        super().__init__(args)
        self.pluginDeployDir = osp.join(self.projectRoot, 'Plugins', 'Wwise', 'ThirdParty')

    def _deploy_package(self, zip_ref: zipfile.ZipFile, pkg: _Package):
        zip_info = next(f for f in zip_ref.filelist if f.filename.endswith(pkg.source_name()))
        with zip_ref.open(zip_info) as f:
            with lzma.open(f) as xz:
                with tarfile.open(fileobj=xz) as tar:
                    is_android = pkg.deployment_platforms() == 'Android'
                    for member in tar.getmembers():
                        new_name = member.name.lstrip('SDK/')
                        if is_android:
                            for arch in ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'):
                                new_name = new_name.replace(f'Android_{arch}', f'Android/{arch}')
                        member.name = new_name
                    parent = member.name.split('/')[0]
                    if osp.isdir(osp.join(self.pluginDeployDir, parent)):
                        tar.extractall(self.pluginDeployDir)
                        print('\n'.join([osp.normpath(osp.join(self.pluginDeployDir, member.name)) for member in tar.getmembers()]))
                    else:
                        print(f'Parent directory dose not exist, skip: {parent}')
