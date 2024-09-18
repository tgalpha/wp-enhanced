import os
import os.path as osp
import logging
import requests
from pprint import pformat

import kkpyutil as util

_build_agent_host = 'YOUR_BUILD_AGENT_HOST_HERE'
_build_agent_account = 'YOUR_BUILD_AGENT_ACCOUNT_HERE'
_proj_root_on_build_agent = 'YOUR_PROJECT_ROOT_ON_BUILD_AGENT_HERE'


def rpc_call(method: str, args: dict):
    logging.info(f'RPC call: {method} with args: {args}')
    response = requests.post(f'http://{_build_agent_host}:5000/{method}',
                             json=args)
    if response.status_code != 200:
        raise RuntimeError(f'Error: {response.status_code}, {response.text}')
    response_json = response.json()
    if response_json['retcode'] != 0:
        raise RuntimeError(pformat(response_json))
    logging.info(pformat(response_json))
    return response


def get_local_branch_name():
    res = util.run_cmd(['git', 'branch', '--show-current'])
    return res.stdout.strip().decode('utf-8')


def check_worktree_clean():
    def need_push():
        local_branch_name = get_local_branch_name()
        _res = util.run_cmd(['git', 'log', f'origin/{local_branch_name}..HEAD'])
        return _res.stdout.strip() != b''

    # Check if worktree is clean
    res = util.run_cmd(['git', 'status', '--porcelain'])
    if res.stdout.strip() != b'':
        res = input('There are uncommitted changes, continue anyway? [y/n]')
        if res.lower() != 'y':
            raise RuntimeError('Worktree is not clean, please commit all changes before remote build.')
    if need_push():
        res = input('There are unpushed commits, continue anyway? [y/n]')
        if res.lower() != 'y':
            raise RuntimeError('Please push all commits before remote build.')


def build_ios_plugin(plugin_name: str):
    local_branch_name = get_local_branch_name()
    rpc_call('git_sync', {'root': _proj_root_on_build_agent, 'branch': local_branch_name})
    rpc_call('premake', {'root': _proj_root_on_build_agent, 'platform': 'iOS'})
    for build_config in ('Debug', 'Profile', 'Release'):
        rpc_call('build', {'root': _proj_root_on_build_agent, 'platform': 'iOS', 'build_config': build_config})


def copy_binaries_from_build_machine(plugin_name: str):
    build_machine_sdk_root = util.run_cmd(
        ['ssh', f'{_build_agent_account}@{_build_agent_host}', 'source ~/.bash_profile && echo $WWISESDK']
    ).stdout.strip().decode('utf-8')
    res = util.run_cmd([
        'ssh',
        f'{_build_agent_account}@{_build_agent_host}',
        f'source ~/.bash_profile && find \"${{WWISESDK}}\" -type f -name *{plugin_name}* | grep -v dSYM'
    ])
    build_stuffs = res.stdout.strip().decode('utf-8').split('\n')
    for item in build_stuffs:
        relative_path = osp.relpath(item, start=build_machine_sdk_root)
        target_path = osp.join(os.getenv('WWISESDK'), relative_path)
        os.makedirs(osp.dirname(target_path), exist_ok=True)
        util.run_cmd([
            'scp',
            # disable filename check: https://stackoverflow.com/a/54599326/19741036
            '-T',
            f'{_build_agent_account}@{_build_agent_host}:"{item}"',
            target_path
        ])


def main(**kwargs):
    check_worktree_clean()
    build_ios_plugin(kwargs['plugin_name'])
    copy_binaries_from_build_machine(kwargs['plugin_name'])
