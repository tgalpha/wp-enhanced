import os.path as osp
import glob
import xml.etree.ElementTree as ET

import kkpyutil as util

from wpe.pathman import PathMan


class JbRunManager:
    def __init__(self, pathman: PathMan):
        self.pathMan = pathman
        self.workspaceXmlPaths = []
        self.runConfigXml = None

    def lazy_add_run_config(self):
        if self._find_workspace_xml():
            self._load_template()
            self._add_run_config()
        else:
            print('Workspace xml not found. Run config was not added. Please open Authoring solution with JetBrains IDE first.')

    def _find_workspace_xml(self) -> bool:
        expected = osp.join(self.pathMan.root, '.idea', f'.idea.{self.pathMan.pluginName}_Authoring_*', '.idea', 'workspace.xml')
        self.workspaceXmlPaths = glob.glob(expected)
        return bool(self.workspaceXmlPaths)

    def _load_template(self):
        template = osp.join(self.pathMan.templatesDir, '_idea', 'JetBrainsRunConfig.xml')
        content = util.load_text(template) % {
            'name': self.pathMan.pluginName,
        }
        self.runConfigXml = ET.fromstring(content)

    def _add_run_config(self):
        for workspaceXmlPath in self.workspaceXmlPaths:
            self._lazy_add_run_config_to_workspace_xml(workspaceXmlPath)
            print(f'Run configuration added to {workspaceXmlPath}')

    def _lazy_add_run_config_to_workspace_xml(self, workspace):
        """
        - Find component with name 'RunManager'
        - Check configuration with name 'run with wwise' exists
        - Add template run configuration if not exists
        """
        workspace_xml = ET.parse(workspace)
        root = workspace_xml.getroot()
        run_manager = root.find('component[@name="RunManager"]')

        if run_manager is None:
            run_manager = ET.Element('component', name='RunManager')
            root.append(run_manager)

        run_wwise_config = run_manager.find('configuration[@name="run with wwise"]')
        if run_wwise_config is None:
            run_manager.append(self.runConfigXml)

        workspace_xml.write(workspace, encoding='utf-8', xml_declaration=True)
