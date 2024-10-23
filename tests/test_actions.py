import glob
import io
import json
import os
import shutil
import os.path as osp
import sys
import zipfile
from types import SimpleNamespace
from typing import Optional
import pytest

import kkpyutil as util

from wpe import core
from wpe.pathman import PathMan
import wpe.util as wpe_util

## Globals
test_dir = osp.dirname(__file__)
org_dir = osp.join(test_dir, 'org')
test_plugin_name = 'TestPlugin'
pathman: Optional[PathMan] = None


def unload_wp_modules():
    """
    wp scripts has module level constants, which can cause issues when working with multiple test cases.
    """
    wp_modules = [v for v in sys.modules.values() if
                  (mod_file := getattr(v, '__file__', '')) and mod_file.startswith(os.getenv('WWISEROOT'))]
    for mod in wp_modules:
        del sys.modules[mod.__name__]


def copy_test_project(test_name, tmp_path):
    target_dir = osp.join(tmp_path, test_plugin_name)
    shutil.copytree(osp.join(org_dir, test_name, test_plugin_name), target_dir)
    global pathman
    pathman = PathMan(target_dir)


def setup_function():
    core.Session.current = None
    unload_wp_modules()


def teardown_function():
    args.destProject = os.getenv('WWISEROOT')
    args.name = test_plugin_name
    core.clean(args)


@pytest.fixture
def args(request, tmp_path):
    """
    Return a SimpleNamespace object with wpe global args.
    """
    return SimpleNamespace(
        root=osp.join(tmp_path, test_plugin_name),
        withHooks=[]
    )


def test_init_wpe(args, tmp_path):
    copy_test_project('pure_wp', tmp_path)
    core.init_wpe(args)
    assert osp.isfile(pathman.projConfig)
    assert osp.isfile(osp.join(pathman.hooksDir, 'pre_premake.py'))


def test_premake(args, tmp_path):
    copy_test_project('wpe_integrated', tmp_path)
    args.platforms = [
        'Authoring',
        'Windows_vc160',
        'Android'
    ]
    core.premake(args)

    project_files = ['TestPlugin_Authoring_Windows_vc160.sln',
                     'TestPlugin_Windows_vc160_shared.sln',
                     'TestPlugin_Windows_vc160_static.sln',
                     'SoundEnginePlugin\\TestPlugin_Windows_vc160_shared.vcxproj',
                     'SoundEnginePlugin\\TestPlugin_Windows_vc160_static.vcxproj',
                     'WwisePlugin\\TestPlugin_Authoring_Windows_vc160.vcxproj',
                     'TestPlugin_Android.mk',
                     'TestPlugin_Android_application.mk',
                     'SoundEnginePlugin\\TestPlugin_Android_shared.mk',
                     'SoundEnginePlugin\\TestPlugin_Android_static.mk']
    for f in project_files:
        assert osp.isfile(osp.join(pathman.root, f))


def test_generate_parameters(args, tmp_path):
    copy_test_project('wpe_integrated', tmp_path)
    args.force = False
    args.gui = True
    core.generate_parameters(args)

    expected_dir = osp.join(org_dir, 'wpe_integrated', 'generate_parameters_expected')
    expected_files = [path for path in glob.iglob(f'{expected_dir}\\**', recursive=True) if osp.isfile(path)]
    for expected in expected_files:
        relpath = osp.relpath(expected, expected_dir)
        actually = osp.join(pathman.root, relpath)
        assert osp.isfile(actually)
        assert util.compare_textfiles(actually, expected)


def test_build_pack_and_clean(args, tmp_path):
    copy_test_project('wpe_integrated', tmp_path)
    args.platforms = ['Authoring']
    args.configuration = 'Release'
    args.destProject = os.getenv('WWISEROOT')
    args.name = test_plugin_name
    args.force = False
    args.gui = True
    core.generate_parameters(args)
    core.premake(args)
    # build
    core.build(args)
    wwise_plugin_dir = osp.join(os.getenv('WWISEROOT'), 'Authoring', 'x64', 'Release', 'bin', 'Plugins')
    plugin_files = [
        'TestPlugin.dll',
        'TestPlugin.pdb',
        'TestPlugin.xml',
    ]
    for f in plugin_files:
        assert osp.isfile(osp.join(wwise_plugin_dir, f))

    # pack
    core.pack(args)
    archive = osp.join(pathman.distDir, 'TestPlugin_v2021.1.14_Build1.zip')
    assert osp.isfile(archive)
    with zipfile.ZipFile(archive, 'r') as zip_ref:
        bundle_file = next(f for f in zip_ref.filelist if f.filename.endswith('bundle.json'))
        with zip_ref.open(bundle_file) as f:
            content = f.read().decode('utf-8')
            bundle = json.loads(content)
            assert bundle['name'] == test_plugin_name
            assert len(bundle['files']) == 4
            file_ids = [f['id'] for f in bundle['files']]
            assert file_ids == [
                "TestPlugin_v2021.1.14_Build1_Authoring.Documentation.tar.xz",
                "TestPlugin_v2021.1.14_Build1_Authoring_Windows_Release.x64.tar.xz",
                "TestPlugin_v2021.1.14_Build1_SDK.Common.tar.xz",
                "TestPlugin_v2021.1.14_Build1_SDK.Windows_vc160.tar.xz"
            ]

    # clean
    core.clean(args)
    for f in plugin_files:
        assert not osp.isfile(osp.join(wwise_plugin_dir, f))


def test_bump(args, tmp_path):
    copy_test_project('wpe_integrated', tmp_path)
    proj_config = wpe_util.load_toml(pathman.projConfig)
    assert proj_config['project']['version'] == 1
    core.bump(args)
    proj_config = wpe_util.load_toml(pathman.projConfig)
    assert proj_config['project']['version'] == 2


def test_rename(args, tmp_path, monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO('y'))
    copy_test_project('wpe_integrated', tmp_path)
    args.newName = 'NewPlugin'
    core.rename(args)

    new_pathman = PathMan(osp.join(tmp_path, args.newName))

    project_files = ['NewPlugin_Authoring_Windows_vc160.sln',
                     'NewPlugin_Windows_vc160_shared.sln',
                     'NewPlugin_Windows_vc160_static.sln',
                     'SoundEnginePlugin\\NewPlugin_Windows_vc160_shared.vcxproj',
                     'SoundEnginePlugin\\NewPlugin_Windows_vc160_static.vcxproj',
                     'WwisePlugin\\NewPlugin_Authoring_Windows_vc160.vcxproj',
                     'NewPlugin_Android.mk',
                     'NewPlugin_Android_application.mk',
                     'SoundEnginePlugin\\NewPlugin_Android_shared.mk',
                     'SoundEnginePlugin\\NewPlugin_Android_static.mk']
    for f in project_files:
        assert osp.isfile(osp.join(new_pathman.root, f))

    org_proj_root = osp.join(org_dir, 'wpe_integrated', test_plugin_name)
    for path in glob.iglob(osp.join(org_proj_root, '**', '*'), recursive=True):
        if osp.isfile(path):
            content = util.load_text(path)
            if test_plugin_name in content:
                relpath = osp.relpath(path, org_proj_root).replace(test_plugin_name, args.newName)
                new_path = osp.join(new_pathman.root, relpath)
                assert osp.isfile(new_path)
                new_content = util.load_text(new_path)
                assert test_plugin_name not in new_content
                assert args.newName in new_content
