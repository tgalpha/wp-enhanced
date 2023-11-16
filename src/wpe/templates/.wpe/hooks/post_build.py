import glob
import logging
import os.path as osp
import shutil


def copy_debug_authoring_plugin_to_release_dir(build_config, plugin_name):
    if build_config == 'Release':
        return

    wwise_root = osp.expandvars('%wwiseroot%')
    build_output_dir = osp.join(wwise_root, f'Authoring/x64/{build_config}/bin/Plugins')
    src_files = glob.glob(osp.join(build_output_dir, f'{plugin_name}.*'))
    dst_dir = osp.join(wwise_root, f'Authoring/x64/Release/bin/Plugins')
    logging.info(f'Copy authoring plugin "{src_files}", from "{build_output_dir}" to "{dst_dir}"')
    for src in src_files:
        dst = osp.join(dst_dir, osp.basename(src))
        shutil.copy(src, dst)


def main(**kwargs):
    """
    Will be called after build.
    kwargs:
        proj_root: project root path
        build_config: build configuration (Debug, Profile, Release)
        plugin_name: plugin name, which is used to glob plugin files
    """
    copy_debug_authoring_plugin_to_release_dir(kwargs['build_config'], kwargs['plugin_name'])


if __name__ == '__main__':
    _proj_root = osp.abspath(f'{__file__}/../../..')
    _plugin_name = osp.basename(_proj_root)
    # Just for manually run
    main(proj_root=_proj_root, build_config='Debug', plugin_name=_plugin_name)
