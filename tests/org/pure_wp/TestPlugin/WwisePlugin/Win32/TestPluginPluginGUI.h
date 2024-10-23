#pragma once

#include "../TestPluginPlugin.h"

class TestPluginPluginGUI final
	: public AK::Wwise::Plugin::PluginMFCWindows<>
	, public AK::Wwise::Plugin::GUIWindows
{
public:
	TestPluginPluginGUI();

};
