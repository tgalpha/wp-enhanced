import subprocess
import os.path as osp


def fetch_git_repo(url, dst_dir, branch='master'):
    if osp.exists(dst_dir):
        print(f'Updating {dst_dir}')
        subprocess.check_call(['git', 'pull'], cwd=dst_dir)
        return
    print(f'Cloning {url} to {dst_dir}')
    subprocess.check_call(['git', 'clone', '-b', branch, url, dst_dir])


def main(**kwargs):
    external_repo_dir = osp.join(kwargs['proj_root'], 'external')
    # add external repo fetching here
    # fetch_git_repo('${REPO_URL}', osp.join(external_repo_dir, '&{REPO_NAME}'))
