/*******************************************************************************
The content of this file includes portions of the AUDIOKINETIC Wwise Technology
released in source code form as part of the SDK installer package.

Commercial License Usage

Licensees holding valid commercial licenses to the AUDIOKINETIC Wwise Technology
may use this file in accordance with the end user license agreement provided
with the software or, alternatively, in accordance with the terms contained in a
written agreement between you and Audiokinetic Inc.

Apache License Usage

Alternatively, this file may be used under the Apache License, Version 2.0 (the
"Apache License"); you may not use this file except in compliance with the
Apache License. You may obtain a copy of the Apache License at
http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software distributed
under the Apache License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied. See the Apache License for
the specific language governing permissions and limitations under the License.

  Copyright (c) 2021 Audiokinetic Inc.
*******************************************************************************/
// [wp-enhanced template] **Do not delete this line**

#include "TestPluginPlugin.h"
#include "../SoundEnginePlugin/TestPluginFXFactory.h"

// [PropertyNames]
const char* const szBoolParamAsCheckbox = "BoolParamAsCheckbox";
const char* const szIntParamAsComboBox = "IntParamAsComboBox";
const char* const szFloatParamAsSlider = "FloatParamAsSlider";
// [/PropertyNames]

TestPluginPlugin::TestPluginPlugin()
{
}

TestPluginPlugin::~TestPluginPlugin()
{
}

bool TestPluginPlugin::GetBankParameters(const GUID & in_guidPlatform, AK::Wwise::Plugin::DataWriter& in_dataWriter) const
{
    // Write bank data here
    // [WriteBankData]
    in_dataWriter.WriteBool(m_propertySet.GetBool(in_guidPlatform, szBoolParamAsCheckbox));
    in_dataWriter.WriteInt32(m_propertySet.GetInt32(in_guidPlatform, szIntParamAsComboBox));
    in_dataWriter.WriteReal32(m_propertySet.GetReal32(in_guidPlatform, szFloatParamAsSlider));
    // [/WriteBankData]

    return true;
}

DEFINE_AUDIOPLUGIN_CONTAINER(TestPlugin);											// Create a PluginContainer structure that contains the info for our plugin
EXPORT_AUDIOPLUGIN_CONTAINER(TestPlugin);											// This is a DLL, we want to have a standardized name
ADD_AUDIOPLUGIN_CLASS_TO_CONTAINER(                                             // Add our CLI class to the PluginContainer
    TestPlugin,        // Name of the plug-in container for this shared library
    TestPluginPlugin,  // Authoring plug-in class to add to the plug-in container
    TestPluginFX       // Corresponding Sound Engine plug-in class
);
DEFINE_PLUGIN_REGISTER_HOOK

DEFINEDUMMYASSERTHOOK;							// Placeholder assert hook for Wwise plug-ins using AKASSERT (cassert used by default)
