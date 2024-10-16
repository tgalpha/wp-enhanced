import copy
from typing import Any, Optional
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from collections import OrderedDict


# project
from wpe.util import *
from wpe.project_config import ProjectConfig, PluginInfo

_type_prefix_map = {
    'float': 'f',
    'int': 'i',
    'uint': 'u',
    'bool': 'b',
}

_wwise_type_name_map = {
    'float': 'AkReal32',
    'int': 'AkInt32',
    'uint': 'AkUInt32',
    'bool': 'bool',
}

_xml_type_name_map = {
    'float': 'Real32',
    'int': 'int32',
    'uint': 'Uint32',
    'bool': 'bool',
}

_supported_rtpc_types = {'Additive', 'Multiplicative', 'Exclusive', 'Boolean'}


@dataclass
class InnerType:
    name: str
    fields: list['Parameter']

    def __post_init__(self):
        self.structName = util.convert_compound_cases(self.name)

    @staticmethod
    def create(name, dict_define: dict[str, Any]):
        instance = InnerType(
            name=name,
            fields=[Parameter.create(name, defines) for name, defines in dict_define.items()],
        )
        return instance

    def generate_struct_defines(self):
        return f'''struct {self.structName}
{{
    {self.__generate_field_lines()}
}};'''

    def __generate_field_lines(self):
        lines = []
        for type_field in self.fields:
            type_field.generate_names()
            lines.append(type_field.generate_declaration())
        return '\n    '.join(lines)


@dataclass
class Parameter:
    name: str
    type_: str
    rtpc_type: str
    defaultValue: Any
    minValue: Any
    maxValue: Any
    data_meaning: str = ''
    description: list[dict] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    displayName: str = ''
    enumeration: list[dict] = field(default_factory=list)
    userInterface: str = ''
    id: int = 0
    parent: Optional[InnerType] = None
    basename: str = ''
    suffix: str = ''

    def __post_init__(self):
        if self.type_ not in _wwise_type_name_map:
            raise ValueError(f'Unsupported type: {self.type_} in parameter "{self.name}". Expected one of {_wwise_type_name_map.keys()}.')

        if self.rtpc_type and self.rtpc_type not in _supported_rtpc_types:
            raise ValueError(f'Unsupported rtpc type: {self.rtpc_type} in parameter "{self.name}". Expected one of {_supported_rtpc_types}.')

    def generate_names(self):
        if self.type_ == 'bool':
            self.defaultValue = str(self.defaultValue).lower()
            self.minValue = 'false'
            self.maxValue = 'true'
        self.propertyName = util.convert_compound_cases(self.name)
        self.cppVariableName = _type_prefix_map[self.type_] + util.convert_compound_cases(self.basename or self.propertyName)
        self.paramIDName = f'PARAM_{self.name.upper()}_ID'
        self.typeName = _wwise_type_name_map[self.type_]
        self.xmlTypeName = _xml_type_name_map[self.type_]
        self.struct = 'InnerType' if self.parent else ('RTPC' if self.rtpc_type else 'NonRTPC')
        self.displayName = self.displayName or util.convert_compound_cases(self.name, style='title')
        self.nameSpace = f'{self.struct}.{self.parent.name}{self.suffix}' if self.parent else self.struct

    def assign_id(self, _id: int):
        self.id = _id

    @staticmethod
    def create(name, dict_define: dict[str, Any]):
        return Parameter(
            name=name,
            type_=dict_define['type'],
            rtpc_type=dict_define.get('rtpc_type', 'Exclusive' if dict_define.get('rtpc') else ''),
            defaultValue=dict_define['default_value'],
            minValue=dict_define.get('min_value', None),
            maxValue=dict_define.get('max_value', None),
            data_meaning=dict_define.get('data_meaning', ''),
            description=dict_define.get('description', []),
            dependencies=copy.deepcopy(dict_define.get('dependencies', [])),
            displayName=dict_define.get('display_name', ''),
            enumeration=dict_define.get('enumeration', []),
            userInterface=dict_define.get('user_interface', '')
        )

    def generate_param_id(self) -> str:
        return f'static constexpr AkPluginParamID {self.paramIDName} = {self.id};'

    def generate_declaration(self) -> str:
        if self.parent:
            return f'{self.parent.structName} {self.parent.name}{self.suffix};'
        return f'{self.typeName} {self.cppVariableName};'

    def generate_init(self) -> str:
        return f'{self.nameSpace}.{self.cppVariableName} = {self.defaultValue};'

    def generate_read_bank_data(self) -> str:
        return f'{self.nameSpace}.{self.cppVariableName} = READBANKDATA({self.typeName}, pParamsBlock, in_ulBlockSize);'

    def generate_set_parameter(self) -> str:
        need_reinterpret = self.typeName != 'AkReal32' and bool(self.rtpc_type)
        interpret_pointer = f'static_cast<{self.typeName}>(*(AkReal32*)in_pValue)' if need_reinterpret else f'*(({self.typeName}*)in_pValue)'
        return f'''    case {self.paramIDName}:
        {self.nameSpace}.{self.cppVariableName} = {interpret_pointer};
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

    def generate_xml_property(self) -> list[str]:
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
        support_rtpc_type = f'SupportRTPCType="{self.rtpc_type}"' if self.rtpc_type else ''
        data_meaning = f'DataMeaning="{self.data_meaning}"' if self.data_meaning else ''

        def _generate_bool_gui_lines():
            return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} {data_meaning} DisplayName="{self.displayName}">
  <DefaultValue>{self.defaultValue}</DefaultValue>
  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>{_generate_dependencies()}
</Property>'''.splitlines()

        def _generate_float_gui_lines():
            user_interface = self.userInterface or f'Step="0.1" Fine="0.001" Decimals="3" UIMax="{self.maxValue}"'
            return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} {data_meaning} DisplayName="{self.displayName}">
  <UserInterface {user_interface} />
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

        def _generate_int_gui_lines():
            user_interface = self.userInterface
            if not self.enumeration:
                if self.minValue is not None and self.maxValue is not None:
                    return _generate_float_gui_lines()
                return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} {data_meaning} DisplayName="{self.displayName}">
                  <UserInterface {user_interface} />
                  <DefaultValue>{self.defaultValue}</DefaultValue>
                  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>
                </Property>'''.splitlines()
            options = '\n        '.join(['<Value DisplayName="{}">{}</Value>'.format(opt['displayName'], opt['value']) for opt in self.enumeration])
            return f'''<Property Name="{self.propertyName}" Type="{self.xmlTypeName}" {support_rtpc_type} {data_meaning} DisplayName="{self.displayName}">
  <UserInterface {user_interface} />
  <DefaultValue>{self.defaultValue}</DefaultValue>
  <AudioEnginePropertyID>{self.id}</AudioEnginePropertyID>
  <Restrictions>
    <ValueRestriction>
      <Enumeration Type="{self.xmlTypeName}"> 
        {options}
      </Enumeration>
    </ValueRestriction>
  </Restrictions>{_generate_dependencies()}
</Property>'''.splitlines()

        if self.type_ == 'bool':
            return _generate_bool_gui_lines()

        if self.type_ == 'int' or self.type_ == 'uint':
            return _generate_int_gui_lines()

        if self.type_ == 'float':
            return _generate_float_gui_lines()

        raise NotImplementedError(f'Parameter type "{self.type_}" not supported.')

    def dump_parameter_doc(self, docs_dir: str):
        for lang in self.description:
            output_path = osp.join(docs_dir, f'{lang["language"]}', f'{self.propertyName}.md')
            doc_str = f'''##{self.displayName}

{lang['text']}

Range: {self.minValue} - {self.maxValue} <br/>'''
            util.save_text(output_path, doc_str)

    def generate_win32_controls(self) -> list[str]:
        row_height = 18
        vertical_pos = row_height * self.id + 6
        title = f'LTEXT "{self.displayName}",IDC_STATIC,0,{vertical_pos + 2},48,10'
        control_pos = f'48,{vertical_pos},64,12'
        if self.type_ == 'bool':
            control = f'CONTROL "{self.propertyName}",IDC_{self.propertyName},"Button",BS_AUTOCHECKBOX | WS_TABSTOP,' + control_pos
        elif self.type_ == 'int':
            if self.enumeration:
                options = ', '.join([f'{opt["value"]}:{opt["displayName"]}' for opt in self.enumeration])
                control = f'LTEXT "Class=Combo;Prop={self.propertyName};Options={options}",IDC_{self.propertyName},' + control_pos
            else:
                control = f'LTEXT "Class=Spinner;Prop={self.propertyName};Min={self.minValue};Max={self.maxValue}",IDC_{self.propertyName},' + control_pos
        elif self.type_ == 'float':
            control = f'LTEXT "Class=SuperRange;Prop={self.propertyName}",IDC_{self.propertyName},' + control_pos
        else:
            raise ValueError(f'Unknown type: {self.type_}')
        return [title, control]


class ParameterGenerator:
    def __init__(self, path_man, is_forced=False, generate_gui_resource=False):
        self.pathMan = path_man
        self.isForced = is_forced
        self.generateGuiResource = generate_gui_resource
        self.innerTypes: dict[str, InnerType] = {}
        self.parameters: dict[str, Parameter] = {}
        self.pluginInfo: Optional[PluginInfo] = None
        self.libSuffix = ''

    def main(self):
        self.load_parameter_config()
        self._generate()

    def load_parameter_config(self):
        proj_config = ProjectConfig(self.pathMan)

        # load plugin info
        self.pluginInfo = proj_config.plugin_info()

        # load parameters
        if not proj_config.has_parameters():
            return
        for name, define in proj_config.parameter_defines().items():
            self.parameters[name] = Parameter.create(name, define)
        for instance in proj_config.parameter_from_templates():
            self.__load_with_template(instance, proj_config.parameter_templates())
        self.innerTypes = {name: InnerType.create(name, dict_define) for name, dict_define in proj_config.parameter_inner_types().items()}
        for instance in proj_config.parameter_from_inner_types():
            self.__load_with_inner_type(instance)

        for i, param in enumerate(self.parameters.values()):
            param.assign_id(i)
            param.generate_names()
            # link parameter dependency
            for dep in param.dependencies:
                dep['obj'] = self.parameters[dep['name']]

        self._get_lib_suffix()

    def _get_lib_suffix(self):
        if not self.libSuffix:
            plugin_table = parse_premake_lua_table(self.pathMan.premakePluginLua)
            self.libSuffix = plugin_table['sdk']['static']['libsuffix']

    def _generate(self):
        def _generate_params_h(template_name='ProjectNameParams'):
            target = f'SoundEnginePlugin/{template_name}.h'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix, add_suffix_after_project_name=True):
                util.substitute_lines_in_file(self.__generate_ids(), dst, '// [ParameterID]', '// [/ParameterID]')
                util.substitute_lines_in_file(self.__generate_inner_types(), dst, '// [InnerTypes]', '// [/InnerTypes]')
                util.substitute_lines_in_file(self.__generate_declarations(struct='InnerType'), dst, '// [InnerTypeDeclaration]',
                                              '// [/InnerTypeDeclaration]')
                util.substitute_lines_in_file(self.__generate_declarations(struct='RTPC'), dst, '// [RTPCDeclaration]',
                                              '// [/RTPCDeclaration]')
                util.substitute_lines_in_file(self.__generate_declarations(struct='NonRTPC'), dst, '// [NonRTPCDeclaration]',
                                              '// [/NonRTPCDeclaration]')

        def _generate_params_cpp(template_name='ProjectNameParams'):
            target = f'SoundEnginePlugin/{template_name}.cpp'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix, add_suffix_after_project_name=True):
                util.substitute_lines_in_file(self.__generate_init(), dst, '// [ParameterInitialization]',
                                              '// [/ParameterInitialization]')
                util.substitute_lines_in_file(self.__generate_read_bank_data(), dst, '// [ReadBankData]',
                                              '// [/ReadBankData]')
                util.substitute_lines_in_file(self.__generate_set_parameter(), dst, '// [SetParameters]',
                                              '// [/SetParameters]', withindent=False)

        def _generate_wwise_plugin_h():
            target = 'WwisePlugin/ProjectNamePlugin.h'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix):
                util.substitute_lines_in_file(self.__generate_property_name_declaration(), dst, '// [PropertyNames]',
                                              '// [/PropertyNames]')

        def _generate_wwise_plugin_cpp():
            target = 'WwisePlugin/ProjectNamePlugin.cpp'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix):
                util.substitute_lines_in_file(self.__generate_property_name_definition(), dst, '// [PropertyNames]',
                                              '// [/PropertyNames]')
                util.substitute_lines_in_file(self.__generate_write_bank_data(), dst, '// [WriteBankData]',
                                              '// [/WriteBankData]')

        def _generate_wwise_xml():
            if dst := osp.join(self.pathMan.root, f'WwisePlugin/{self.pathMan.pluginName}.xml'):
                util.substitute_lines_in_file(self.__generate_xml_properties(), dst, '<Properties>',
                                              '</Properties>')
                util.substitute_lines_in_file(self.__generate_xml_plugin_info(), dst, '<PluginInfo',
                                              '</PluginInfo>', removecues=True)

        def _generate_doc():
            for param in self.parameters.values():
                param.dump_parameter_doc(self.pathMan.docsDir)

        def _generate_win32_gui_resource():
            target = 'WwisePlugin/Win32/ProjectNamePluginGUI.cpp'
            dst = copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix)
            if not self.generateGuiResource:
                return
            if dst:
                util.substitute_lines_in_file(self.__generate_win32_property_table(), dst, '// [PropertyTable]', '// [/PropertyTable]')

            target = 'WwisePlugin/ProjectName.rc'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix):
                util.substitute_lines_in_file(self.__generate_win32_controls(), dst, '// [Controls]', '// [/Controls]')

            target = 'WwisePlugin/resource.h'
            if dst := copy_template(target, self.pathMan, self.isForced, lib_suffix=self.libSuffix):
                util.substitute_lines_in_file(self.__generate_win32_idc(), dst, '// [IDC]', '// [/IDC]')

        _generate_params_h()
        _generate_params_cpp()
        # For MetaData plugin, which use ProjectNameMeta as file name
        # 'Mete' suffix will be added so that template name don't contain 'Meta'
        _generate_params_h(template_name='ProjectName')
        _generate_params_cpp(template_name='ProjectName')
        _generate_wwise_plugin_h()
        _generate_wwise_plugin_cpp()
        _generate_wwise_xml()
        _generate_doc()
        _generate_win32_gui_resource()

    def __generate_ids(self):
        lines = []
        for i, param in enumerate(self.parameters.values()):
            lines.append(param.generate_param_id())
        lines.append(f'static constexpr AkUInt32 NUM_PARAMS = {len(self.parameters)};')
        return auto_add_line_end(lines)

    def __generate_inner_types(self):
        lines = []
        for i, inner_type in enumerate(self.innerTypes.values()):
            lines.append(inner_type.generate_struct_defines())
        return auto_add_line_end(lines)

    def __load_with_template(self, instance, templates):
        template = copy.deepcopy(templates[instance['template']])
        for key, value in instance.get('override', {}).items():
            template[key] = value
        for dep in template.get('dependencies', []):
            dep['name'] = dep['name'] % {'suffix': instance['suffix']}

        name = f"{instance['template']}_{instance['suffix']}"
        self.parameters[name] = Parameter.create(name, template)

    def __load_with_inner_type(self, define):
        inner_type = self.innerTypes[define['inner_type']]
        overrides = define.get('overrides', {})

        for type_field in inner_type.fields:
            field_name = type_field.name
            instance = copy.deepcopy(type_field)
            if field_name in overrides:
                instance.defaultValue = overrides[field_name]
            for dep in instance.dependencies:
                dep['name'] = f"{inner_type.name}_{dep['name'] % {'suffix': define['suffix']}}"

            instance.name = f"{inner_type.name}_{field_name}_{define['suffix']}"
            instance.basename = field_name
            instance.parent = inner_type
            instance.suffix = define['suffix']
            self.parameters[instance.name] = instance

    def __generate_declarations(self, struct):
        lines = []
        for param in self.parameters.values():
            if param.struct == struct:
                lines.append(param.generate_declaration())
        # remove duplicate lines(when inner type is used)
        lines = list(OrderedDict.fromkeys(lines).keys())
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

    def __generate_xml_properties(self):
        lines = []
        for param in self.parameters.values():
            lines.extend(add_indent(param.generate_xml_property(), 2))
        return auto_add_line_end(lines)

    def __generate_xml_plugin_info(self):
        return auto_add_line_end(self.pluginInfo.generate_plugin_info())

    def __generate_win32_controls(self):
        lines = []
        for param in self.parameters.values():
            lines.extend(param.generate_win32_controls())
        return auto_add_line_end(lines)

    def __generate_win32_idc(self):
        lines = []
        for i, param in enumerate(self.parameters.values()):
            lines.append(f'#define IDC_{param.propertyName} {i + 1001}')
        return auto_add_line_end(lines)

    def __generate_win32_property_table(self):
        lines = []
        for param in self.parameters.values():
            if param.type_ != 'bool':
                continue
            lines.append(f'AK_WWISE_PLUGIN_GUI_WINDOWS_POP_ITEM(IDC_{param.propertyName}, sz{param.propertyName})')
        return auto_add_line_end(lines)
