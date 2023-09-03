import copy
import os.path as osp
from typing import Any
from dataclasses import dataclass, field

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
    displayName: str = ''
    enumeration: list[str] = field(default_factory=list)
    userInterface: dict = field(default_factory=dict)
    id: int = 0

    def __post_init__(self):
        self.propertyName = util.convert_compound_cases(self.name)
        self.cppVariableName = _type_prefix_map[self.type_] + self.propertyName
        self.paramIDName = f'PARAM_{self.name.upper()}_ID'
        self.typeName = _wwise_type_name_map[self.type_]
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
            minValue=dict_define['min_value'],
            maxValue=dict_define['max_value'],
            description=dict_define.get('description', []),
            displayName=dict_define.get('display_name', ''),
            enumeration=dict_define.get('enumeration', []),
            userInterface=dict_define.get('user_interface', {})
        )

    def generate_param_id(self) -> str:
        return f'static const AkPluginParamID {self.paramIDName} = {self.id};'

    def generate_declaration(self) -> str:
        return f'    {self.typeName} {self.cppVariableName};'

    def generate_init(self) -> str:
        return f'        {self.struct}.{self.cppVariableName} = {self.defaultValue};'

    def generate_read_bank_data(self) -> str:
        return f'    {self.struct}.{self.cppVariableName} = READBANKDATA({self.typeName}, pParamsBlock, in_ulBlockSize);'

    def generate_set_parameter(self) -> str:
        interpret_pointer = 'static_cast<AkInt32>(*((AkReal32*)in_pValue))' if self.type_ == 'int' else f'*(({self.typeName}*)in_pValue)'
        return f'''    case {self.paramIDName}:
        {self.struct}.{self.cppVariableName} = {interpret_pointer};
        m_paramChangeHandler.SetParamChange({self.paramIDName});
        break;'''

    def generate_write_bank_data(self) -> str:
        writer = 'Write' + util.convert_compound_cases(self.typeName.lstrip('Ak'))
        getter = 'Get' + util.convert_compound_cases(self.typeName.lstrip('Ak'))
        return f'    in_dataWriter.{writer}(m_propertySet.{getter}(in_guidPlatform, "{self.propertyName}"));'

    def generate_parameter_gui(self) -> list[str]:
        xml_type_name = self.typeName.lstrip('Ak')
        support_rtpc_type = 'SupportRTPCType="Exclusive"' if self.rtpc else ''
        # TODO: support enumeration and userInterface
        return f'''<Property Name="{self.propertyName}" Type="{xml_type_name}" {support_rtpc_type} DisplayName="{self.displayName}">
<UserInterface Step="0.1" Fine="0.001" Decimals="3" UIMax="{self.maxValue}" />
  <DefaultValue>{self.defaultValue}</DefaultValue>
  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>
  <Restrictions>
    <ValueRestriction>
      <Range Type="{xml_type_name}">
        <Min>{self.minValue}</Min>
        <Max>{self.maxValue}</Max>
      </Range>
    </ValueRestriction>
  </Restrictions>
</Property>'''.splitlines()

    def dump_parameter_doc(self, docs_dir: str):
        for lang in self.description:
            output_path = osp.join(docs_dir, f'{lang["language"]}', f'{self.propertyName}.md')
            doc_str = f'''##{self.displayName}

{lang['text']}

Range: {self.minValue} - {self.maxValue} <br/>'''
            util.save_text(output_path, doc_str)


class ParameterGenerator:
    def __init__(self, path_man):
        self.pathMan = path_man
        self.parameters: list[Parameter] = []

    def main(self):
        self._load()
        self._generate()

    def _load(self):
        if not osp.isfile(self.pathMan.parameterConfig):
            raise FileNotFoundError(f'Parameter config not found: {self.pathMan.parameterConfig}')
        content = load_toml(self.pathMan.parameterConfig)
        for name, define in content['parameters']['defines'].items():
            self.parameters.append(Parameter.create(name, define))
        for instance in content['parameters']['from_templates']:
            template = copy.deepcopy(content['templates'][instance['template']])
            for key, value in instance.get('override', {}).items():
                template[key] = value
            self.parameters.append(Parameter.create(f"{instance['template']}_{instance['suffix']}", template))

        for i, param in enumerate(self.parameters):
            param.assign_id(i)

    def _generate(self):
        def _copy_template(relative):
            src = osp.join(self.pathMan.templatesDir, relative)
            dst = replace_in_basename(osp.join(self.pathMan.root, relative), 'ProjectName', self.pathMan.pluginName)
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
                                          '// [/ParameterInitialization]', withindent=False)
            util.substitute_lines_in_file(self.__generate_read_bank_data(), dst, '// [ReadBankData]',
                                          '// [/ReadBankData]', withindent=False)
            util.substitute_lines_in_file(self.__generate_set_parameter(), dst, '// [SetParameters]',
                                          '// [/SetParameters]', withindent=False)

        def _generate_wwise_params_cpp():
            target = 'WwisePlugin/ProjectNamePlugin.cpp'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_write_bank_data(), dst, '// [WriteBankData]',
                                          '// [/WriteBankData]', withindent=False)

        def _generate_wwise_xml():
            target = 'WwisePlugin/ProjectName.xml'
            dst = _copy_template(target)
            util.substitute_lines_in_file(self.__generate_parameter_gui(), dst, '<!-- [ParameterGui] -->', '<!-- [/ParameterGui] -->')

        def _generate_doc():
            for param in self.parameters:
                param.dump_parameter_doc(self.pathMan.docsDir)

        _generate_fx_params_cpp()
        _generate_fx_params_h()
        _generate_wwise_params_cpp()
        _generate_wwise_xml()
        _generate_doc()

    def __generate_ids(self):
        lines = []
        for i, param in enumerate(self.parameters):
            lines.append(param.generate_param_id())
        lines.append(f'static const AkUInt32 NUM_PARAMS = {len(self.parameters)};')
        return auto_add_line_end(lines)

    def __generate_declarations(self, rtpc=True):
        lines = []
        for param in self.parameters:
            if param.rtpc == rtpc:
                lines.append(param.generate_declaration())
        return auto_add_line_end(lines)

    def __generate_init(self):
        lines = []
        for param in self.parameters:
            lines.append(param.generate_init())
        return auto_add_line_end(lines)

    def __generate_read_bank_data(self):
        lines = []
        for param in self.parameters:
            lines.append(param.generate_read_bank_data())
        return auto_add_line_end(lines)

    def __generate_set_parameter(self):
        lines = []
        for param in self.parameters:
            lines.append(param.generate_set_parameter())
        return auto_add_line_end(lines)

    def __generate_write_bank_data(self):
        lines = []
        for param in self.parameters:
            lines.append(param.generate_write_bank_data())
        return auto_add_line_end(lines)

    def __generate_parameter_gui(self):
        lines = []
        for param in self.parameters:
            lines.extend(param.generate_parameter_gui())
        return auto_add_line_end(lines)
