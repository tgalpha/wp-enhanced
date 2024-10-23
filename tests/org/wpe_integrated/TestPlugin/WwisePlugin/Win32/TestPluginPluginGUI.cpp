
#include "TestPluginPluginGUI.h"

TestPluginPluginGUI::TestPluginPluginGUI()
{
}

ADD_AUDIOPLUGIN_CLASS_TO_CONTAINER(
    TestPlugin,            // Name of the plug-in container for this shared library
    TestPluginPluginGUI,   // Authoring plug-in class to add to the plug-in container
    TestPluginFX           // Corresponding Sound Engine plug-in class
);
