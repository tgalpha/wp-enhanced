import glob
import os
import os.path as osp
import subprocess

from wpe.pathman import PathMan
from wpe.project_config import ProjectConfig
import wpe.util as wutil


class Renamer:
    def __init__(self, new_name: str, pathman: PathMan, proj_config: ProjectConfig):
        self.oldName = pathman.pluginName
        self.newName = new_name
        self.pathMan = pathman
        self.projConfig = proj_config
        self.renameMethod = wutil.git_mv if wutil.path_is_under_git_repo(self.pathMan.root) else os.rename

    def main(self):
        self._delete_generated_files()
        self._migrate_sources()
        self._move_proj_folder()

    def _delete_generated_files(self):
        targets = [
            f'{self.oldName}*.xcworkspace',
            f'{self.oldName}*.mk',
            f'{self.oldName}*.sln',
            f'*/{self.oldName}*.aps',
            f'*/{self.oldName}*.xcodeproj',
            f'*/{self.oldName}*.mk',
            f'*/{self.oldName}*.vcxproj*',
        ]
        for target in targets:
            for path in glob.iglob(osp.join(self.pathMan.root, target)):
                wutil.remove_path(path)

    def _migrate_sources(self):
        targets = [
            'FactoryAssets/Manifest.xml',
            f'SoundEnginePlugin/{self.oldName}FX*',
            f'WwisePlugin/{self.oldName}*',
            f'WwisePlugin/Win32/{self.oldName}*',
            f'WwisePlugin/resource.h',
            'additional_artifacts.json',
            'bundle_template.json',
            f'{self.oldName}Config.h',
            'PremakePlugin.lua',
        ]
        for target in targets:
            for old_path in glob.iglob(osp.join(self.pathMan.root, target)):
                if not osp.exists(old_path):
                    continue
                if self.oldName in osp.basename(old_path):
                    new_path = wutil.replace_in_basename(osp.join(self.pathMan.root, old_path), self.oldName, self.newName, count=1)
                    self.renameMethod(old_path, new_path)
                else:
                    new_path = old_path
                wutil.replace_content_in_file(new_path, self.oldName, self.newName)

    def _move_proj_folder(self):
        new_proj_root = osp.join(osp.dirname(self.pathMan.root), self.newName)
        os.makedirs(new_proj_root, exist_ok=True)
        for item in os.listdir(self.pathMan.root):
            self.renameMethod(osp.join(self.pathMan.root, item), osp.join(new_proj_root, item))
        self.pathMan.refresh_paths(new_proj_root)
