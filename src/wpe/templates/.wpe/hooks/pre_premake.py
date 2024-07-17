import subprocess
import os.path as osp


def fetch_git_repo(url, dst_dir, branch='master', keep_to_latest=True):
    if not osp.exists(dst_dir):
        print(f'Cloning {url} to {dst_dir}')
        subprocess.check_call(['git', 'clone', '-b', branch, url, dst_dir])
        return
    if keep_to_latest:
        print(f'Updating {dst_dir}')
        subprocess.check_call(['git', 'pull'], cwd=dst_dir)
        return


def main(**kwargs):
    external_repo_dir = osp.join(kwargs['proj_root'], 'external')
    # add external repo fetching here
    # fetch_git_repo('${REPO_URL}', osp.join(external_repo_dir, '&{REPO_NAME}'))
