import subprocess
import logging

import kkpyutil as util
from flask import Flask, request, jsonify


class _CommandResult:
    def __init__(self):
        self.succeeded = True
        self.command = []
        self.stdout = ''
        self.stderr = ''

    @staticmethod
    def from_completed_process(completed_process: subprocess.CompletedProcess):
        result = _CommandResult()
        result.parse_completed_process(completed_process)
        return result

    def parse_completed_process(self, completed_process: subprocess.CompletedProcess):
        self.succeeded = completed_process.returncode == 0
        self.command = completed_process.args
        self.stdout = util.safe_decode_bytes(completed_process.stdout).strip()
        self.stderr = util.safe_decode_bytes(completed_process.stderr).strip()

    def __str__(self):
        return f'''succeeded: {self.succeeded}
        args: {self.command}
        stdout: {self.stdout}
        stderr: {self.stderr}'''

    def to_json(self):
        return {'succeeded': self.succeeded,
                'args': self.command,
                'stdout': self.stdout,
                'stderr': self.stderr}

class BuildAgent:
    def __init__(self):
        self._app = Flask('BuildAgent', static_folder=None)

    def start(self, port: int):
        self._app.add_url_rule('/git_sync', 'git_sync', self.git_sync, methods=['POST'])
        self._app.add_url_rule('/build', 'build', self.build, methods=['POST'])
        self._app.run(host='0.0.0.0', port=port)

    @staticmethod
    def run_command(command) -> _CommandResult:
        try:
            logging.info(f'Running command: {command}')
            proc = subprocess.run(command, shell=True, capture_output=True, text=True)
            result = _CommandResult.from_completed_process(proc)
            logging.info(result)
            return result
        except Exception as e:
            result = _CommandResult()
            result.command = command
            result.succeeded = False
            result.stdout = 'Run command failed with exception.'
            result.stderr = str(e)
            return result

    def git_sync(self):
        data = request.get_json()
        root = data.get('root')
        branch = data.get('branch')
        fetch_result = self.run_command(f'git -C {root} fetch origin')
        reset_result = self.run_command(f'git -C {root} reset --hard origin/{branch}')
        succeeded = fetch_result.succeeded and reset_result.succeeded
        retcode = 200 if succeeded else 500
        return jsonify({'succeeded': succeeded,
                        'git fetch': fetch_result.to_json(),
                        'git reset': reset_result.to_json()}), retcode

    def premake(self):
        data = request.get_json()
        root = data.get('root')
        platform = data.get('platform')
        result = self.run_command(f'wpe -p -r {root} -plt {platform}')
        retcode = 200 if result.succeeded else 500
        return jsonify(result.to_json()), retcode

    def build(self):
        data = request.get_json()
        root = data.get('root')
        build_config = data.get('build_config')
        platform = data.get('platform')
        result = self.run_command(f'wpe -b -r {root} -c {build_config} -plt {platform}')
        retcode = 200 if result.succeeded else 500
        return jsonify(result.to_json()), retcode
