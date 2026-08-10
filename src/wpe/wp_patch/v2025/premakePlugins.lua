--[[----------------------------------------------------------------------------
The content of this file includes portions of the AUDIOKINETIC Wwise Technology
released in source code form as part of the SDK installer package.

Commercial License Usage

Licensees holding valid commercial licenses to the AUDIOKINETIC Wwise Technology
may use this file in accordance with the end user license agreement provided
with the software or, alternatively, in accordance with the terms contained in a
written agreement between you and Audiokinetic Inc.

  Copyright (c) 2026 Audiokinetic Inc.
------------------------------------------------------------------------------]]

-- This premake is a meta-premake, calling both the SDK premake as well as the Authoring premake.
if not _AK_PREMAKE then
	error('You must use the custom Premake5 scripts by adding the following parameter: --scripts="Scripts\\Premake"', 1)
end

_AK_TOP_CWD = os.getcwd() .. '/'
_AK_TARGETS = {}

if not premake.option.get("authoring") then
	newoption {
		trigger     = "authoring",
		description = "'yes' if authoring needs to be built, 'no' otherwise",
		default     = "no",
	}
end

if not premake.option.get("plugindir") then
	newoption
	{
		trigger = "plugindir",
		description = "Path to the premake script of a plugin. Plugin script MUST be named like so: PremakePlugin.lua"
	}
end

if not premake.option.get("codesign") then
	newoption
	{
		trigger = "codesign",
		description = "'yes' to add post-build step when PremakePlugin.lua specifies it, 'no' to disable it",
		default     = "yes",
	}
end

if not premake.option.get("signtool-path") then
	newoption
	{
		trigger = "signtool-path",
		description = "Path to the SignTool.exe executable to use for codesigning on Windows",
		default     = "SignTool.exe"
	}
end

-- Building Plugins
require ("Premake5PathHelpers")
require ("PremakePlatforms")
require ("Premake5Helper")

-- [wp-enhanced patch]
_AK_SDK_ROOT = os.getenv('WWISESDK') .. '/'
_AK_WWISE_ROOT = os.getenv('WWISEROOT') .. '/'
_AK_ROOT_DIR = AkMakeAbsolute(_AK_SDK_ROOT .. 'source/Build/')
-- [/wp-enhanced patch]

if _OPTIONS["plugindir"] == nil then
	error('Missing plugin script. Use --plugindir')
	os.exit(0)
end

local plugin = require (_OPTIONS["plugindir"] .. '/PremakePlugin')
local platform = AK.Platform
local projectPath = _WORKING_DIR .. "/"
local PremakePlugins = {}

local actionsuffix = GetSuffixFromCurrentAction()

local currentPlatform = string.lower(os.target() .. '_' .. _ACTION)

local ActionToFolderName = function(action)
	local result
	if action == "vs2015" or action == "vs2017" or action == "vs2019" or action == "vs2022" then
		result = "x64"
	elseif action == "gmake" then
		result = currentPlatform
	else
		error("We are currently not supporting " .. action .. " plugins for Authoring")
	end
	return result
end

if _OPTIONS["authoring"] == "yes" then
	authoringPath = AkRelativeToCwd(_AK_WWISE_ROOT .. "Authoring/")
	wwisetarget_base = authoringPath .. ActionToFolderName(_ACTION) .. '/'
	wa_debug_targetdir = wwisetarget_base .. "Debug/bin/Plugins"
	wa_release_targetdir = wwisetarget_base .. "Release/bin/Plugins"
	wa_debug_objdir = wwisetarget_base .. "Debug/obj/"
	wa_release_objdir = wwisetarget_base .. "Release/obj/"
end

function PremakePlugins.Create()
	print("Generating solutions for " .. plugin.name .. "...")

	if type(plugin.configurations) ~= "table" then
		plugin.configurations = platform.configurations
	end

	if table.find(platform.validActions, _ACTION) then
		print("Premaking for ".. platform.name)
		print("Project path: " .. projectPath)
		local SDKlocation = AkRelativeToCwd(projectPath) .. "SoundEnginePlugin/"
		local SDKTestLocation = AkRelativeToCwd(projectPath) .. "SoundEnginePluginTest/"
		local SDKOutput = _AK_SDK_ROOT
		if plugin.sdk.outputdir ~= nil then
			SDKOutput = AkRelativeToCwd(projectPath) .. plugin.sdk.outputdir
		end

		local SDKFileName = plugin.name.. "_" .. platform.name .. actionsuffix
		local staticSDKFileName = SDKFileName .. "_static"
		local staticSDKTestFileName = plugin.name.. "Test_" .. platform.name .. actionsuffix .. "_static"
		local staticAuthoringSDKFileName = SDKFileName .. "_staticauthoring"
		local sharedSDKFileName = SDKFileName .. "_shared"
		local staticSDKProjectName = plugin.name .. plugin.sdk.static.libsuffix
		local staticSDKTestProjectName = plugin.name .. "Test"
		local staticAuthoringSDKProjectName = plugin.name .. "Authoring" .. plugin.sdk.static.libsuffix
		local staticCRTconfigurations = {}
		local sharedconfigurations = {}
		for _, value in pairs(plugin.configurations) do
			if string.find(value, "StaticCRT") then
				table.insert(staticCRTconfigurations, value)
			else
				table.insert(sharedconfigurations, value)
			end
		end

		--
		--Create static sdk
		--
		local staticSolutionFilename = SDKFileName
		if #staticCRTconfigurations > 0 then
			staticSolutionFilename = staticSDKFileName --If there are StaticCRT configs, we need two independent solutions for static and shared
		end
		CreateSolution(staticSolutionFilename, projectPath, platform.name, plugin.configurations, actionsuffix, {})
		if _ACTION == "xcode4" then
			workspace(staticSolutionFilename)
				local AkAppleCommon = require "Apple"
				AkAppleCommon.CreateXcscheme("All")
		end
		PremakePlugins.CreateProject(staticSDKProjectName, staticSDKFileName, plugin.sdk.static, SDKlocation, "StaticLib", SDKOutput, "lib")
		
		--
		--Create static sdk test on supported platforms
		--
		if platform.name == "Windows" or platform.name == "Mac" or platform.name == "Linux" then
			if plugin.sdk.test ~= nil then
				local platformSupported = false
				if plugin.sdk.test.platforms == nil then
					platformSupported = true
				else
					for i,v in ipairs(plugin.sdk.test.platforms) do
						if platform.name == v then
							platformSupported = true
							break
						end
					end
				end

				if platformSupported then
					local testProject = PremakePlugins.CreateProject(staticSDKTestProjectName, staticSDKTestFileName, plugin.sdk.test, SDKTestLocation, "ConsoleApp", SDKOutput, "bin")
					ApplyPlatformExceptions("ExternalPluginTest", testProject)

					filter {}
						links { staticSDKProjectName }
				end
			end
		end

		--
		--Create shared sdk
		--
		if (plugin.sdk.shared ~= nil) then
			if #staticCRTconfigurations > 0 then
				CreateSolution(sharedSDKFileName, projectPath, platform.name, sharedconfigurations, actionsuffix, {})
				workspace()
					importproject(staticSDKFileName .. ":" .. staticSDKProjectName)
						wconfigmap
						{
							Debug = { "Debug(StaticCRT)", staticSDKProjectName },
							Profile = { "Profile(StaticCRT)", staticSDKProjectName },
							Release = { "Release(StaticCRT)", staticSDKProjectName },
						}
			end
			local prj = PremakePlugins.CreateProject(plugin.name, sharedSDKFileName, plugin.sdk.shared, SDKlocation, "SharedLib", SDKOutput, "bin")

			filter {}
			flags{ "NoImportLib" }
			symbols "On"

			ApplyPlatformExceptions('SoundEngineDllProject', prj)

			xcodebuildsettings {
				CODE_SIGN_ENTITLEMENTS = "../plugin.entitlements"
			}

			if _ACTION == "xcode4" then
				premake.generate({location = AkRelativeToCwd(projectPath) .. "/plugin"}, ".entitlements", function(_)
					premake.out("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
					premake.out("<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n")
					premake.out("<plist version=\"1.0\">\n")
					premake.out("<dict/>\n")
					premake.out("</plist>\n")
				end)
			end

			filter {}
				links { staticSDKProjectName }
		end

		--
		--Create Authoring
		--
		if _OPTIONS["authoring"] == "yes" then
			--Create static authoring sdk
			--Some Authoring plug-ins need to use a different Sound Engine plug-in, with some added features, such as a monitoring or callback or error verification layer.
			if plugin.sdk.staticauthoring ~= nil then
				CreateSolution(staticAuthoringSDKFileName, projectPath, platform.name, plugin.configurations, actionsuffix, {})
				PremakePlugins.CreateProject(staticAuthoringSDKProjectName, staticAuthoringSDKFileName, plugin.sdk.staticauthoring, SDKlocation, "StaticLib", SDKOutput, "lib")
			end
			local SDKProjectName
			local SDKFileName = SDKFileName
			if platform.name == "Windows" then
				SDKProjectName = plugin.sdk.staticauthoring and staticAuthoringSDKProjectName or staticSDKProjectName
				SDKFileName = plugin.sdk.staticauthoring and staticAuthoringSDKFileName or staticSDKFileName
			else
				SDKProjectName = plugin.sdk.staticauthoring and staticAuthoringSDKProjectName or staticSDKProjectName
				SDKFileName = plugin.sdk.staticauthoring and staticAuthoringSDKFileName or SDKFileName
			end
			_AK_BUILD_AUTHORING = true
			CreateSolution(plugin.name .. "_Authoring_" .. platform.name .. actionsuffix,projectPath,platform.name, {"Debug", "Release"},actionsuffix,{})
			workspace()
				importproject(SDKFileName .. ":" .. SDKProjectName)
				wconfigmap {
					Release = { "Profile", SDKProjectName }
				}
			PremakePlugins.CreateAuthoring()
			filter {}
				links { SDKProjectName }
		end
	end
end

function PremakePlugins.CreateAuthoring()
	local platform = AK.Platform
	local authoringLocation = AkRelativeToCwd(projectPath) .. "WwisePlugin/"
	local authoringOutput = AkRelativeToCwd(_AK_WWISE_ROOT .. "Authoring/")
	local authoringFileName = plugin.name .. "_Authoring_" .. platform.name .. actionsuffix
-- 	[wp-enhanced patch] Always output to release dir for authoring
	local targetDir = authoringOutput .. "$(Platform)/Release/" .. "bin/Plugins"
-- 	[/wp-enhanced patch]

	PremakePlugins.CreateProject(plugin.name, authoringFileName, plugin.authoring, authoringLocation, "SharedLib")

	filter { "system:windows" }
		for _,cfg in pairs(plugin.configurations) do
			filter (cfg)
				targetdir (targetDir)
				objdir ("!" .. authoringOutput .. "$(Platform)/$(Configuration)/obj/$(ProjectName)")
		end

		if type(plugin.legalfiles) == "table" then
			local legalDir = targetDir .. '/' .. plugin.name
			postbuildcommands
			{
				'if not exist "' .. path.translate(legalDir) .. '" mkdir "' .. path.translate(legalDir) ..'"',
			}
			for _,legalfile in pairs(plugin.legalfiles) do
				postbuildcommands
				{
					'copy /y "' .. path.translate(AkRelativeToCwd(legalfile)) .. '" "' .. path.translate(legalDir) .. '"'
				}
			end
		end

	filter { "system:not windows", "Debug" }
		targetdir(wa_debug_targetdir)
		objdir(wa_debug_objdir .. plugin.name)

	filter { "system:not windows", "Release" }
		targetdir(wa_release_targetdir)
		objdir(wa_release_objdir .. plugin.name)

	filter "system:linux or system:macosx"
		if type(plugin.legalfiles) == "table" then
			postbuildcommands
			{
				'\"mkdir\" -p "' .. '%{cfg.targetdir}' .. '/' .. plugin.name .. '"'
			}
			for _,legalfile in pairs(plugin.legalfiles) do
				postbuildcommands
				{
					'cp "' .. path.translate(AkRelativeToCwd(legalfile)) .. '" "' .. '%{cfg.targetdir}' .. '/' .. plugin.name .. '/"'
				}
			end
		end

	filter {}
		flags{ "NoImportLib" }
		cppdialect "c++17"

	if type(plugin.factoryheader) == "string" then
		filter "system:windows"
			postbuildcommands
			{
				'copy /y "' .. path.translate(AkRelativeToCwd(plugin.factoryheader)) .. '" "' .. path.translate(_AK_SDK_ROOT .. 'include/AK/Plugin') .. '"'
			}
		filter "system:linux or system:macosx"
			postbuildcommands
			{
				-- Copy factory header file from the project location to the SDK includes of the Wwise target installation.
				-- %{cfg.targetdir} refers to the plugin bin folder (ex.: Authoring/linux_gmake/Debug/bin/plugins).
				'cp "' .. path.translate(AkRelativeToCwd(plugin.factoryheader)) .. '" "' .. '%{cfg.targetdir}/../../../../../SDK/include/AK/Plugin/"'
			}
	end

	-- Copy XML
	filter { "system:windows", "files:**.xml" }
		buildmessage 'Copying "%(Filename)%(Extension)"...'
		buildcommands
		{
			'if not exist \"$(OutDir)\" mkdir \"$(OutDir)\"',
			'if exist \"$(OutDir)%(Filename).xml\" del /F /Q \"$(OutDir)%(Filename).xml\"',
			'copy /y \"%(FullPath)\" \"$(OutDir)%(Filename).xml\"'
		}
		buildoutputs
		{
			"$(OutDir)%(Filename)%(Extension)",
			"%(Outputs)"
		}

	filter "system:linux or system:macosx"
		prebuildcommands
		{
			'mkdir -p %{cfg.targetdir}',
			'cp *.xml %{cfg.targetdir}'
		}

	filter { "system:linux" }
		toolset("clang")
		platforms { "x64" }

	filter { "system:macosx" }
		toolset("clang")
		platforms { "universal" }


	filter { "system:windows", "configurations:Debug" }
		libdirs { _AK_SDK_ROOT .. "$(Platform)" .. actionsuffix .. "/$(Configuration)/lib/" }
	filter { "system:windows", "configurations:Release" }
		libdirs { _AK_SDK_ROOT .. "$(Platform)" .. actionsuffix .. "/Profile/lib/" }
		defines { "AK_ENABLE_ASSERTS"}
end

function PremakePlugins.CreateProject(in_projectName, in_fileName, pluginData, in_location, in_kind, in_outputDir, in_outputSubdir)
	local prj = platform.CreateProject(in_fileName, in_projectName, in_location, actionsuffix, nil, in_kind)

	ApplyPlatformExceptions("ExternalPlugin", prj)

	includedirs { AkRelativeToCwd(_AK_SDK_ROOT .. "include/")}

	-- Include dirs
	if type(pluginData.includedirs) == "table" then
		for _,dir in pairs(pluginData.includedirs) do
			if path.isabsolute(dir) then
				includedirs { dir }
			else
				includedirs { AkRelativeToCwd(in_location .. dir)}
			end
		end
	end
	-- files
	if type(pluginData.files) == "table" then
		for _,file in pairs(pluginData.files) do
			if path.isabsolute(file) then
				files { file }
			else
				files { AkRelativeToCwd(in_location .. file)}
			end
		end
	end
	-- excludes
	if type(pluginData.excludes) == "table" then
		for _,exclude in pairs(pluginData.excludes) do
			if path.isabsolute(exclude) then
				excludes { exclude }
			else
				excludes { AkRelativeToCwd(in_location .. exclude)}
			end
		end
	end

	-- links
	if type(pluginData.links) == "table" then
		for _,link in pairs(pluginData.links) do
			links { link }
		end
	end
	-- Lib dirs
	if type(pluginData.libdirs) == "table" then
		for _,libdir in pairs(pluginData.libdirs) do
			if path.isabsolute(libdir) then
				libdirs { libdir }
			else
				libdirs { AkRelativeToCwd(in_location .. libdir) }
			end
		end
	end
	-- defines
	if type(pluginData.defines) == "table" then
		for _,define in pairs(pluginData.defines) do
			defines { define }
		end
	end
	-- custom project configuration
	if pluginData.custom ~= nil then
		pluginData.custom()
	end

	if in_outputSubdir ~= nil then
		for _,cfg in pairs(plugin.configurations) do
			filter (cfg)
				AK.Platform.SetOutputDirectory(in_outputDir,cfg,actionsuffix,in_outputSubdir)
		end
	end

	filter "system:not windows"
		excludes { AkRelativeToCwd(in_location .. "Win32/*"),
					AkRelativeToCwd(in_location .. "*.def"),
					AkRelativeToCwd(in_location .. "*.rc") }

	filter "system:not linux"
		excludes { AkRelativeToCwd(in_location .. "Linux/*") }

	filter "system:not macosx"
		excludes { AkRelativeToCwd(in_location .. "MacOS/*") }

	if type(plugin.appleteamid) == "string" then
		filter "action:xcode4"
			xcodebuildsettings { DEVELOPMENT_TEAM = plugin.appleteamid }
	end
	filter()

	if _OPTIONS["codesign"] == "yes" then
		-- Skip codesign when there is no development team id
		if plugin.appleteamid == "" then
			filter "action:xcode4"
				xcodebuildsettings { CODE_SIGNING_ALLOWED = "NO" }
		end
		filter()

		if type(plugin.signtoolargs) == "table" and next(plugin.signtoolargs) ~= nil then
			filter {"system:windows", "kind:SharedLib"}
				postbuildcommands
				{
					_OPTIONS["signtool-path"] .. ' ' .. table.concat(plugin.signtoolargs, ' ') .. ' $(TargetPath)'
				}
		end
		filter()
	else
		filter "action:xcode4"
			xcodebuildsettings { CODE_SIGNING_ALLOWED = "NO" }
	end

	filter()

	return prj
end

PremakePlugins.Create()
