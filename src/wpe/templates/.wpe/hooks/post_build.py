import os.path as osp


def main(**kwargs):
    """
    Will be called after build.
    kwargs:
        proj_root: project root path
        build_config: build configuration (Debug, Profile, Release)
        plugin_name: plugin name, which is used to glob plugin files
    """


if __name__ == '__main__':
    _proj_root = osp.abspath(f'{__file__}/../../..')
    _plugin_name = osp.basename(_proj_root)
    # Just for manually run
    main(proj_root=_proj_root, build_config='Debug', plugin_name=_plugin_name)
