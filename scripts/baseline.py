#!/usr/bin/env python3
"""Run one isolated Java/Vue development baseline from an ordinary local terminal.

Uses native MySQL. Never clears a database or changes existing credentials.
A and B must run in separate clones/worktrees; this is not cross-account approval.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dev import ROOT, init_db, read_env, setup


def validate(slot, env):
    if env.get('MUSIC_DB_NAME') != f'music_dev_{slot}' or env.get('MUSIC_DB_USER') != f'music_dev_{slot}':
        raise RuntimeError('Refusing a database/user outside the selected development slot.')
    if env.get('MUSIC_DB_HOST') != '127.0.0.1' or env.get('SPRING_PROFILES_ACTIVE') != 'local':
        raise RuntimeError('Only the local profile and loopback database are supported.')
    offset = 0 if slot == 'a' else 1
    for key, value in [('MUSIC_DB_PORT', 3307 + offset), ('MUSIC_SERVER_PORT', 8080 + offset),
                       ('VITE_DEV_PORT', 5173 + offset)]:
        if str(env.get(key)) != str(value):
            raise RuntimeError(f'{key} must match isolated slot {slot} ({value}).')
    if env.get('VITE_PROXY_TARGET') != f'http://127.0.0.1:{8080 + offset}':
        raise RuntimeError('Frontend proxy does not match this slot backend.')
    state = (ROOT / '.local' / slot).resolve()
    for key, child in [('MUSIC_UPLOAD_PATH', 'uploads'), ('MUSIC_UPLOAD_TEMP_PATH', 'chunks')]:
        if Path(env[key]).resolve() != state / child:
            raise RuntimeError(f'{key} belongs to another checkout; regenerate config in an independent clone.')


def network_preflight():
    # Fail before starting or initializing any service when socket use is prohibited.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
    with socket.socket() as probe:
        probe.settimeout(2)
        code = probe.connect_ex(('127.0.0.1', 9))
        if code in (1, 13):
            raise PermissionError(code, 'Loopback connections are not permitted')


def port_open(port):
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(('127.0.0.1', int(port))) == 0


def free_port(port):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', int(port)))


def schema_action(count, versions, migrate=False):
    if count == 0:
        return 'initialize_empty'
    if count == 11 and versions == ['1']:
        if migrate:
            return 'migrate_upload_ownership'
        raise RuntimeError('V001 uploads require explicit --migrate-upload-ownership; data preserved.')
    if count != 11 or versions != ['1', '2']:
        raise RuntimeError('Existing database is incomplete or unexpected; preserved without repair or overwrite.')
    return 'reuse_existing'


def discover(args, env):
    tools = ROOT.parent / '.music-tools'
    environment = {**os.environ, **env}
    java = Path(environment.get('JAVA_HOME', '/nonexistent'))
    if not (java / 'bin/javac').is_file():
        java = tools / 'jdk-17.0.20.1+1/Contents/Home'
    if not (java / 'bin/javac').is_file():
        raise RuntimeError('JDK 17 is missing; set JAVA_HOME to a JDK first.')
    environment['JAVA_HOME'] = str(java)
    node = tools / 'node-v22.23.3-darwin-arm64/bin'
    if node.is_dir():
        environment['PATH'] = str(node) + os.pathsep + environment.get('PATH', '')
    if not shutil.which('npm', path=environment.get('PATH')):
        raise RuntimeError('Node/npm are missing; install the project Node version first.')
    mysql_base = Path(args.mysql_base).resolve() if args.mysql_base else tools / 'mysql-8.0.41-macos15-arm64'
    client = mysql_base / 'bin/mysql'
    server = mysql_base / 'bin/mysqld'
    if not client.is_file():
        found = shutil.which('mysql', path=environment.get('PATH'))
        if found:
            client = Path(found).resolve()
            mysql_base = client.parent.parent
            server = mysql_base / 'bin/mysqld'
    if not client.is_file():
        raise RuntimeError('Native mysql client missing; supply --mysql-base /path/to/mysql.')
    return environment, mysql_base, client, server


class Baseline:
    def __init__(self, args):
        self.args = args
        self.state = ROOT / '.local' / args.slot
        self.env = read_env(args.slot)
        self.logdir = self.state / 'logs' / ('baseline-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
        self.logdir.mkdir(mode=0o700)
        self.children = []
        self.socketdir = None
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        self.result = {'slot': args.slot, 'checkout': str(ROOT), 'code_sha': revision, 'status': 'running', 'checks': [],
                       'limits': ['Synthetic fixtures; no production readiness or independent account review.',
                                  'Not an independent confirmation from the other account.']}

    def command(self, command, label, cwd=None, input_text=None, environment=None, timeout=300):
        path = self.logdir / (label + '.log')
        with path.open('w') as output:
            completed = subprocess.run(command, cwd=cwd or ROOT, env=environment or self.environment,
                                       input=input_text, text=True, stdout=output, stderr=subprocess.STDOUT,
                                       timeout=timeout)
        if completed.returncode:
            raise RuntimeError(f'{label} failed (exit {completed.returncode}); see {path}')
        return path

    def start(self, command, label, cwd=None):
        path = self.logdir / (label + '.log')
        with path.open('w') as output:
            process = subprocess.Popen(command, cwd=cwd or ROOT, env=self.environment,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        self.children.append(process)
        return process

    def wait(self, process, ready, label, seconds=90):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'{label} exited early ({process.returncode}); see {self.logdir}')
            if ready():
                return
            time.sleep(0.5)
        raise RuntimeError(f'{label} readiness timed out; see {self.logdir}')

    def query(self, sql, root_socket=None, password=None):
        command = [str(self.client), '--batch', '--skip-column-names', '--connect-timeout=5']
        if root_socket:
            command += ['--protocol=SOCKET', '--socket=' + root_socket, '--user=root']
        else:
            command += ['--protocol=TCP', '--host=127.0.0.1', '--port=' + self.env['MUSIC_DB_PORT'],
                        '--user=' + self.env['MUSIC_DB_USER'], '--database=' + self.env['MUSIC_DB_NAME']]
        environment = {**self.environment, 'MYSQL_PWD': self.env['MUSIC_DB_PASSWORD'] if password is None else password}
        completed = subprocess.run(command, cwd=ROOT, env=environment, input=sql, text=True,
                                   capture_output=True, timeout=15)
        if completed.returncode:
            # SQL/passwords never enter the command line, console or evidence JSON.
            raise RuntimeError('Database authentication/query failed; existing credentials were preserved.')
        return completed.stdout.strip().splitlines()

    def database(self):
        if not port_open(self.env['MUSIC_DB_PORT']):
            if not self.server.is_file():
                raise RuntimeError('No MySQL server is listening and native mysqld is missing.')
            data = self.state / 'mysql-data'
            fresh = not data.exists()
            common = [str(self.server), '--no-defaults', '--basedir=' + str(self.mysql_base), '--datadir=' + str(data)]
            if fresh:
                data.mkdir(mode=0o700)
                self.command(common + ['--initialize-insecure'], 'mysql-initialize', timeout=180)
            elif not (data / 'mysql').is_dir():
                raise RuntimeError('Existing MySQL data directory is incomplete; preserved without reinitializing.')
            self.socketdir = Path(tempfile.mkdtemp(prefix='music-' + self.args.slot + '-', dir='/tmp'))
            address = str(self.socketdir / 'mysql.sock')
            process = self.start(common + ['--bind-address=127.0.0.1', '--port=' + self.env['MUSIC_DB_PORT'],
                                          '--mysqlx=0', '--skip-name-resolve', '--socket=' + address,
                                          '--pid-file=' + str(self.state / 'mysql-baseline.pid')], 'mysql')
            self.wait(process, lambda: port_open(self.env['MUSIC_DB_PORT']), 'mysql')
            if fresh:
                def literal(value):
                    # Setup uses hex secrets. Never interpolate untrusted SQL values.
                    if not value or any(c not in '0123456789abcdef' for c in value):
                        raise RuntimeError('Fresh native bootstrap requires setup-generated hexadecimal secrets.')
                    return "'" + value + "'"
                name = self.env['MUSIC_DB_NAME']  # strictly validated identifier above
                password = literal(self.env['MUSIC_DB_PASSWORD'])
                root_password = literal(self.env['MUSIC_DB_ROOT_PASSWORD'])
                sql = (f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;'
                       f"CREATE USER '{name}'@'127.0.0.1' IDENTIFIED BY {password};"
                       f"GRANT ALL ON `{name}`.* TO '{name}'@'127.0.0.1';"
                       f"ALTER USER 'root'@'localhost' IDENTIFIED BY {root_password};")
                self.query(sql, root_socket=address, password='')
        count = int(self.query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();')[0])
        versions = self.query('SELECT version FROM development_schema_version ORDER BY version;') if count else []
        action = schema_action(count, versions, self.args.migrate_upload_ownership)
        if action == 'initialize_empty':
            # dev.init_db independently checks emptiness again and never drops existing tables.
            init_db(self.args.slot, str(self.client))
        from upload_ownership_migration import migrate, validate_structure
        if action == 'migrate_upload_ownership':
            self.result['checks'].append({'upload_ownership_migration': migrate(self.query)})
        validate_structure(self.query)
        count = int(self.query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();')[0])
        if count != 11:
            raise RuntimeError('Development baseline requires exactly 11 tables.')
        self.result['checks'].append({'database': action, 'tables': count})

    @staticmethod
    def http_ready(url, expected):
        try:
            with urlopen(url, timeout=2) as response:
                return response.status == expected
        except HTTPError as error:
            return error.code == expected
        except (URLError, OSError):
            return False

    def run(self):
        validate(self.args.slot, self.env)
        network_preflight()
        self.environment, self.mysql_base, self.client, self.server = discover(self.args, self.env)
        for key in ['MUSIC_SERVER_PORT', 'VITE_DEV_PORT']:
            free_port(self.env[key])  # never hijack another running development service
        self.result['checks'].append('local socket permission and isolated configuration')
        if self.args.check:
            self.result['status'] = 'preflight_passed'
            return
        maven = ['sh', './mvnw', '-B', '-ntp'] + (['-o'] if self.args.offline else [])
        agent = Path.home() / '.m2/repository/net/bytebuddy/byte-buddy-agent/1.15.11/byte-buddy-agent-1.15.11.jar'
        test_args = ['-DargLine=-javaagent:' + str(agent)] if agent.is_file() else []
        self.command(maven + test_args + ['test'], 'java-tests', cwd=ROOT / 'music')
        if not (ROOT / 'web/node_modules').is_dir():
            self.command(['npm', 'ci'] + (['--offline'] if self.args.offline else []), 'npm-ci', cwd=ROOT / 'web')
        self.command(['npm', 'run', 'build'], 'frontend-build', cwd=ROOT / 'web')
        self.result['checks'].append('Java tests and frontend production build')
        self.database()
        backend = self.start(maven + ['spring-boot:run'], 'backend', cwd=ROOT / 'music')
        api = 'http://127.0.0.1:' + self.env['MUSIC_SERVER_PORT'] + '/api/auth/profile'
        self.wait(backend, lambda: self.http_ready(api, 401), 'backend', seconds=180)
        frontend = self.start(['npm', 'run', 'dev'], 'frontend', cwd=ROOT / 'web')
        web = 'http://127.0.0.1:' + self.env['VITE_DEV_PORT']
        self.wait(frontend, lambda: self.http_ready(web, 200), 'frontend')
        for via_proxy, label in [(False, 'smoke-direct'), (True, 'smoke-proxy')]:
            command = [sys.executable, 'scripts/smoke.py', '--slot', self.args.slot]
            if via_proxy:
                command.append('--via-proxy')
            path = self.command(command, label, timeout=180)
            evidence = json.loads(path.read_text())
            if len(evidence['functional_checks']) != 13:
                raise RuntimeError(label + ' did not finish all 13 checks.')
            self.result['checks'].append({label: evidence})
        media_test = ROOT / 'scripts/media_access_smoke.py'
        if media_test.is_file():
            path = self.command([sys.executable, str(media_test), '--slot', self.args.slot,
                                 '--mysql', str(self.client)], 'media-access', timeout=180)
            evidence = json.loads(path.read_text())
            if evidence.get('matrix_cases') != 144:
                raise RuntimeError('Media access matrix did not complete all 144 cases.')
            self.result['checks'].append({'media-access': evidence})
        ownership_test = ROOT / 'scripts/upload_ownership_smoke.py'
        if ownership_test.is_file():
            path = self.command([sys.executable, str(ownership_test), '--slot', self.args.slot,
                                 '--mysql', str(self.client)], 'upload-ownership', timeout=180)
            evidence = json.loads(path.read_text())
            if evidence.get('check_count', 0) < 60:
                raise RuntimeError('Upload ownership checks did not complete.')
            self.result['checks'].append({'upload-ownership': evidence})
        self.result['status'] = 'passed'
        self.result['urls'] = {'frontend': web, 'backend': api.rsplit('/auth/profile', 1)[0]}

    def stop(self):
        # Only signal process groups created by this invocation, never discovered services.
        for process in reversed(self.children):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
                except ProcessLookupError:
                    pass
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
        if self.socketdir:
            try:
                self.socketdir.rmdir()
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['a', 'b'], required=True)
    parser.add_argument('--mysql-base', help='Native MySQL directory containing bin/mysql and bin/mysqld')
    parser.add_argument('--offline', action='store_true', help='Use cached Maven/npm dependencies')
    parser.add_argument('--check', action='store_true', help='Preflight only; do not start or initialize services')
    parser.add_argument('--migrate-upload-ownership', action='store_true', help='Explicitly apply additive V002 to an existing isolated V001 database')
    parser.add_argument('--keep-running', action='store_true', help='Keep owned services running until Ctrl+C after checks')
    args = parser.parse_args()
    state = ROOT / '.local' / args.slot
    if not state.exists():
        if args.check:
            parser.error('Slot configuration missing; run scripts/dev.py setup first.')
        setup(args.slot)
    runner = Baseline(args)
    # One checkout may only host one active invocation; other accounts need independent checkouts.
    lock = ROOT / '.local' / 'baseline.lock'
    owned_lock = False
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        owned_lock = True
        with os.fdopen(fd, 'w') as output:
            json.dump({'pid': os.getpid(), 'slot': args.slot}, output)
        runner.run()
        result_path = runner.logdir / 'result.json'
        result_path.write_text(json.dumps(runner.result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(runner.result, ensure_ascii=False, indent=2), flush=True)
        print('Evidence: ' + str(result_path), flush=True)
        if args.keep_running and not args.check:
            print('Services are running. Ctrl+C stops only services started by this command.', flush=True)
            while True:
                if any(child.poll() is not None for child in runner.children):
                    raise RuntimeError('An owned service exited; inspect private logs.')
                time.sleep(1)
        return 0
    except KeyboardInterrupt:
        return 0 if runner.result['status'] == 'passed' else 130
    except Exception as error:
        runner.result.update(status='blocked', error=str(error))
        (runner.logdir / 'result.json').write_text(json.dumps(runner.result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(runner.result, ensure_ascii=False, indent=2), file=sys.stderr)
        print('Evidence: ' + str(runner.logdir / 'result.json'), file=sys.stderr)
        return 1
    finally:
        try:
            runner.stop()
        finally:
            if owned_lock:
                lock.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
