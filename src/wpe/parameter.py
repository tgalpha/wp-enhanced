import copy
import logging
import os.path as osp
from typing import Any, Optional
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET

import kkpyutil as util

# project
from wpe.util import *

_type_prefix_map = {
    'float': 'f',
    'int': 'i',
    'bool': 'b',
}

_wwise_type_name_map = {
    'float': 'AkReal32',
    'int': 'AkInt32',
    'bool': 'bool',
}


def auto_add_line_end(lines: list[str]):
    for i, line in enumerate(lines):
        if not line.endswith('\n'):
            lines[i] += '\n'
    return lines


@dataclass
class Parameter:
    name: str
    type_: str
    rtpc: bool
    defaultValue: Any
    minValue: Any
    maxValue: Any
    description: list[dict] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    displayName: str = ''
    enumeration: list[str] = field(default_factory=list)
    userInterface: dict = field(default_factory=dict)
    id: int = 0

    def __post_init__(self):
        if self.type_ == 'bool':
            self.defaultValue = str(self.defaultValue).lower()
            self.minValue = 'false'
            self.maxValue = 'true'
        self.propertyName = util.convert_compound_cases(self.name)
        self.cppVariableName = _type_prefix_map[self.type_] + self.propertyName
        self.paramIDName = f'PARAM_{self.name.upper()}_ID'
        self.typeName = _wwise_type_name_map[self.type_]
        self.xmlTypeName = self.typeName.lstrip('Ak')
        self.struct = 'RTPC' if self.rtpc else 'NonRTPC'
        self.displayName = self.displayName or util.convert_compound_cases(self.name, style='title')

    def assign_id(self, _id: int):
        self.id = _id

    @staticmethod
    def create(name, dict_define: dict[str, Any]):
        return Parameter(
            name=name,
            type_=dict_define['type'],
            rtpc=dict_define['rtpc'],
            defaultValue=dict_define['default_value'],
            minValue=dict_define.get('min_value', None),
            maxValue=dict_define.get('max_value', None),
            description=dict_define.get('description', []),
            dependencies=dict_define.get('dependencies', []),
            displayName=dict_define.get('display_name', ''),
            enumeration=dict_define.get('enumeration', []),
            userInterface=dict_define.get('user_interface', {})
        )

    def generate_param_id(self) -> str:
        return f'static const AkPluginParamID {self.paramIDName} = {self.id};'

    def generate_declaration(self) -> str:
        return f'{self.typeName} {self.cppVariableName};'

    def generate_init(self) -> str:
        return f'{self.struct}.{self.cppVariableName} = {self.defaultValue};'

    def generate_read_bank_data(self) -> str:
        return f'{self.struct}.{self.cppVariableName} = READBANKDATA({self.typeName}, pParamsBlock, in_ulBlockSize);'

    def generate_set_parameter(self) -> str:
        need_reinterpret = self.typeName != 'AkReal32' and self.rtpc
        interpret_pointer = f'static_cast<{self.typeName}>(*(AkReal32*)in_pValue)' if need_reinterpret else f'*(({self.typeName}*)in_pValue)'
        return f'''    case {self.paramIDName}:
        {self.struct}.{self.cppVariableName} = {interpret_pointer};
        m_paramChangeHandler.SetParamChange({self.paramIDName});
        break;'''

    def generate_property_name_declaration(self) -> str:
        return f'extern const char* const sz{self.propertyName};'

    def generate_property_name_definition(self) -> str:
        return f'const char* const sz{self.propertyName} = "{self.propertyName}";'

    def generate_write_bank_data(self) -> str:
        writer = 'Write' + util.convert_compound_cases(self.typeName.lstrip('Ak'))
        getter = 'Get' + util.convert_compound_cases(self.typeName.lstrip('Ak'))
        return f'in_dataWriter.{writer}(m_propertySet.{getter}(in_guidPlatform, sz{self.propertyName}));'

    def generate_parameter_gui(self) -> list[str]:
        def _generate_dependencies():
            if not self.dependencies:
                return ''
            dependencies_element = ET.Element('Dependencies')
            for dep in self.dependencies:
                property_dep = ET.SubElement(dependencies_element, 'PropertyDependency')
                property_dep.attrib['Name'] = dep['obj'].propertyName
                property_dep.attrib['Action'] = 'Enable'
                condition = ET.SubElement(property_dep, 'Condition')
                if (condition_value := dep['condition']) == 'Enumeration':
                    enumeration = ET.SubElement(condition, condition_value)
                    enumeration.attrib['Type'] = dep['obj'].xmlTypeName
                    for value in dep['values']:
                        value_tag = ET.SubElement(enumeration, 'Value')
                        value_tag.text = str(value)
                if (condition_value := dep['condition']) == 'Range':
                    range_ = ET.SubElement(condition, condition_value)
                    range_.attrib['Type'] = dep['obj'].xmlTypeName
                    min_value = ET.SubElement(range_, 'Min')
                    min_value.text = str(dep['min'])
                    max_value = ET.SubElement(range_, 'Max')
                    max_value.text = str(dep['max'])
            ET.indent(dependencies_element)
            return '\n' + ET.tostring(dependencies_element).decode(util.TXT_CODEC)
        support_rtpc_type = 'SupportRTPCType="Exclusive"' if self.rtpc else ''
        # TODO: support enumeration and userInterface
        if self.type_ == 'bool':
            return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} DisplayName="{self.displayName}">
  <DefaultValue>{self.defaultValue}</DefaultValue>
  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>{_generate_dependencies()}
</Property>'''.splitlines()

        return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} DisplayName="{self.displayName}">
<UserInterface Step="0.1" Fine="0.001" Decimals="3" UIMax="{self.maxValue}" />
  <DefaultValue>{self.defaultValue}</DefaultValue>
  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>
  <Restrictions>
    <ValueRestriction>
      <Range Type="{self.xmlTypeName}">
        <Min>{self.minValue}</Min>
        <Max>{self.maxValue}</Max>
      </Range>
    </ValueRestriction>
  </Restrictions>{_generate_dependencies()}
</Property>'''.splitlines()

    def dump_parameter_doc(self, docs_dir: str):
        for lang in self.description:
            output_path = osp.join(docs_dir, f'{lang["language"]}', f'{self.propertyName}.md')
            doc_str = f'''##{self.displayName}

{lang['text']}

Range: {self.minValue} - {self.maxValue} <br/>'''
            util.save_text(output_path, doc_str)


class PluginInfo:
    def __init__(self, info_dict: dict):
        self.infoDict = info_dict
        self.defaultPlatformSupport = '''<Platform Name="Any">
  <CanBeInsertOnBusses>true</CanBeInsertOnBusses>
  <CanBeInsertOnAudioObjects>true</CanBeInsertOnAudioObjects>
  <CanBeRendered>true</CanBeRendered>
</Platform>'''

    def generate_platform_support(self) -> list[str]:
        if not self.infoDict['platform_support']:
            return self.defaultPlatformSupport.splitlines()
        lines = []
        for platform, config in self.infoDict['platform_support'].items():
            can_be_insert_on_busses = str(config.get('CanBeInsertOnBusses', True)).lower()
            can_be_insert_on_audio_objects = str(config.get('CanBeInsertOnAudioObjects', True)).lower()
            can_be_rendered = str(config.get('CanBeRendered', True)).lower()
            lines.extend(f'''<Platform Name="{platform}">
  <CanBeInsertOnBusses>{can_be_insert_on_busses}</CanBeInsertOnBusses>
  <CanBeInsertOnAudioObjects>{can_be_insert_on_audio_objects}</CanBeInsertOnAudioObjects>
  <CanBeRendered>{can_be_rendered}</CanBeRendered>
</Platform>'''.splitlines())
        return lines


class ParameterGenerator:
    def __init__(self, path_man, is_forced=False):
        self.pathMan = path_man
        self.isForced = is_forced
        self.parameters: dict[str, Parameter] = {}
        self.pluginInfo: Optional[PluginInfo] = None

    def main(self):
        self._load()
        self._generate()

    def _load(self):
        if not osp.isfile(self.pathMan.parameterConfig):
            raise FileNotFoundError(f'Parameter config not found: {self.pathMan.parameterConfig}')
        content = load_toml(self.pathMan.parameterConfig)

        # load plugin info
        self.pluginInfo = PluginInfo(content['plugin_info'])

        # load parameters
        for name, define in content['parameters']['defines'].items():
            self.parameters[name] = Parameter.create(name, define)
        for instance in content['parameters']['from_templates']:
            template = copy.deepcopy(content['templates'][instance['template']])
            for key, value in instance.get('override', {}).items():
                template[key] = value
            if 'dependencies' in template:
                for dep in template['dependencies']:
                    dep['name'] = dep['name'] % {'suffix': instance['suffix']}

            name = f"{instance['template']}_{instance['suffix']}"
            self.parameters[name] = Parameter.create(name, template)

        for i, param in enumerate(self.parameters.values()):
            param.assign_id(i)
            for dep in param.dependencies:
                dep['obj'] = self.parameters[dep['name']]

    def _generate(self):
        def _copy_template(relative):
            def _need_overwrite(_dst):
                if self.isForced:
                    return True
                if osp.isfile(_dst):
                    content = util.load_text(_dst)
                    return '[wp-enhanced template]' not in content
                return True

            src = osp.join(self.pathMan.templatesDir, relative)
            dst = replace_in_basename(osp.join(self.pathMan.root, relative), 'ProjectName', self.pathMan.pluginName)
            if not _need_overwrite(dst):
                logging.info(f'Skip copying template "{osp.basename(src)}". Use -f to force overwrite.')
                return dst
            if osp.isfile(src):
                overwrite_copy(src, dst)
                util.substitute_keywords_in_file(dst,
                                                 {
                                                     'name': self.pathMan.pluginName,
                                                     'display_name': self.pathMan.pluginName,
                                                     'plugin_id': self.pathMan.pluginId,
                                                 })
                return dst
            else:
                raise FileNotFoundError(f'File not found: {src}')

        def _generate_fx_params_h():
            target = 'SoundEnginePlugin/ProjectNameFXParams.h'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_ids(), dst, '// [ParameterID]', '// [/ParameterID]')
            util.substitute_lines_in_file(self.__generate_declarations(rtpc=True), dst, '// [RTPCDeclaration]',
                                          '// [/RTPCDeclaration]')
            util.substitute_lines_in_file(self.__generate_declarations(rtpc=False), dst, '// [NonRTPCDeclaration]',
                                          '// [/NonRTPCDeclaration]')

        def _generate_fx_params_cpp():
            target = 'SoundEnginePlugin/ProjectNameFXParams.cpp'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_init(), dst, '// [ParameterInitialization]',
                                          '// [/ParameterInitialization]')
            util.substitute_lines_in_file(self.__generate_read_bank_data(), dst, '// [ReadBankData]',
                                          '// [/ReadBankData]')
            util.substitute_lines_in_file(self.__generate_set_parameter(), dst, '// [SetParameters]',
                                          '// [/SetParameters]', withindent=False)

        def _generate_wwise_plugin_h():
            target = 'WwisePlugin/ProjectNamePlugin.h'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_property_name_declaration(), dst, '// [PropertyNames]',
                                          '// [/PropertyNames]')

        def _generate_wwise_plugin_cpp():
            target = 'WwisePlugin/ProjectNamePlugin.cpp'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_property_name_definition(), dst, '// [PropertyNames]',
                                          '// [/PropertyNames]')
            util.substitute_lines_in_file(self.__generate_write_bank_data(), dst, '// [WriteBankData]',
                                          '// [/WriteBankData]')

        def _generate_wwise_xml():
            target = 'WwisePlugin/ProjectName.xml'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_parameter_gui(), dst, '<!-- [ParameterGui] -->',
                                          '<!-- [/ParameterGui] -->')
            util.substitute_lines_in_file(self.__generate_platform_support(), dst, '<!-- [PlatformSupport] -->',
                                          '<!-- [/PlatformSupport] -->')

        def _generate_doc():
            for param in self.parameters.values():
                param.dump_parameter_doc(self.pathMan.docsDir)

        _generate_fx_params_h()
        _generate_fx_params_cpp()
        _generate_wwise_plugin_h()
        _generate_wwise_plugin_cpp()
        _generate_wwise_xml()
        _generate_doc()

    def __generate_ids(self):
        lines = []
        for i, param in enumerate(self.parameters.values()):
            lines.append(param.generate_param_id())
        lines.append(f'static const AkUInt32 NUM_PARAMS = {len(self.parameters)};')
        return auto_add_line_end(lines)

    def __generate_declarations(self, rtpc=True):
        lines = []
        for param in self.parameters.values():
            if param.rtpc == rtpc:
                lines.append(param.generate_declaration())
        return auto_add_line_end(lines)

    def __generate_init(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_init())
        return auto_add_line_end(lines)

    def __generate_read_bank_data(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_read_bank_data())
        return auto_add_line_end(lines)

    def __generate_set_parameter(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_set_parameter())
        return auto_add_line_end(lines)

    def __generate_property_name_declaration(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_property_name_declaration())
        return auto_add_line_end(lines)

    def __generate_property_name_definition(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_property_name_definition())
        return auto_add_line_end(lines)

    def __generate_write_bank_data(self):
        lines = []
        for param in self.parameters.values():
            lines.append(param.generate_write_bank_data())
        return auto_add_line_end(lines)

    def __generate_parameter_gui(self):
        lines = []
        for param in self.parameters.values():
            lines.extend(param.generate_parameter_gui())
        return auto_add_line_end(lines)

    def __generate_platform_support(self):
        return auto_add_line_end(self.pluginInfo.generate_platform_support())
