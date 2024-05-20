
extra_gitignore = '''
# premake-androidmk
*.mk
.xcode_development_team


# wp output logs
Output

external'''


rider_run_config = r'''
    <configuration name="run with wwise" type="CppProject" factoryName="C++ Project">
      <configuration_1>
        <option name="CONFIGURATION" value="Debug" />
        <option name="PLATFORM" value="x64" />
        <option name="PROJECT_FILE_PATH" value="$PROJECT_DIR$/WwisePlugin/MiaBinauralizer_Authoring_Windows_vc160.vcxproj" />
        <option name="CURRENT_LAUNCH_PROFILE" value="Local" />
        <option name="EXE_PATH" value="$(WWISEROOT)\Authoring\x64\Release\bin\Wwise.exe" />
        <option name="PROGRAM_PARAMETERS" value="&quot;D:\UE4TestProjs\PluginPlaygroundUE\PluginPlaygroundUE_WwiseProject\PluginPlaygroundUE_WwiseProject.wproj&quot;" />
        <option name="WORKING_DIRECTORY" value="$(ProjectDir)" />
        <option name="PASS_PARENT_ENVS" value="1" />
        <option name="USE_EXTERNAL_CONSOLE" value="0" />
      </configuration_1>
      <configuration_2>
        <option name="CONFIGURATION" value="Release" />
        <option name="PLATFORM" value="x64" />
        <option name="PROJECT_FILE_PATH" value="$PROJECT_DIR$/WwisePlugin/MiaBinauralizer_Authoring_Windows_vc160.vcxproj" />
        <option name="CURRENT_LAUNCH_PROFILE" value="Local" />
        <option name="EXE_PATH" value="$(WWISEROOT)\Authoring\x64\Release\bin\Wwise.exe" />
        <option name="PROGRAM_PARAMETERS" value="&quot;D:\UE4TestProjs\PluginPlaygroundUE\PluginPlaygroundUE_WwiseProject\PluginPlaygroundUE_WwiseProject.wproj&quot;" />
        <option name="WORKING_DIRECTORY" value="$(ProjectDir)" />
        <option name="PASS_PARENT_ENVS" value="1" />
        <option name="USE_EXTERNAL_CONSOLE" value="0" />
      </configuration_2>
      <configuration_3>
        <option name="CONFIGURATION" value="Debug" />
        <option name="PLATFORM" value="Win32" />
        <option name="PROJECT_FILE_PATH" value="$PROJECT_DIR$/WwisePlugin/MiaBinauralizer_Authoring_Windows_vc160.vcxproj" />
        <option name="CURRENT_LAUNCH_PROFILE" value="Local" />
        <option name="EXE_PATH" value="$(WWISEROOT)\Authoring\x64\Release\bin\Wwise.exe" />
        <option name="PROGRAM_PARAMETERS" value="&quot;D:\WwiseTestProjs\2021_3_plugin_test\2021_3_plugin_test.wproj&quot;" />
        <option name="WORKING_DIRECTORY" value="$(ProjectDir)" />
        <option name="PASS_PARENT_ENVS" value="1" />
        <option name="USE_EXTERNAL_CONSOLE" value="0" />
      </configuration_3>
      <configuration_4>
        <option name="CONFIGURATION" value="Release" />
        <option name="PLATFORM" value="Win32" />
        <option name="PROJECT_FILE_PATH" value="$PROJECT_DIR$/WwisePlugin/MiaBinauralizer_Authoring_Windows_vc160.vcxproj" />
        <option name="CURRENT_LAUNCH_PROFILE" value="Local" />
        <option name="EXE_PATH" value="$(WWISEROOT)\Authoring\x64\Release\bin\Wwise.exe" />
        <option name="PROGRAM_PARAMETERS" value="&quot;D:\WwiseTestProjs\2021_3_plugin_test\2021_3_plugin_test.wproj&quot;" />
        <option name="WORKING_DIRECTORY" value="$(ProjectDir)" />
        <option name="PASS_PARENT_ENVS" value="1" />
        <option name="USE_EXTERNAL_CONSOLE" value="0" />
      </configuration_4>
      <option name="DEFAULT_PROJECT_PATH" value="" />
      <method v="2" />
    </configuration>'''