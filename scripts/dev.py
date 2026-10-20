#!/usr/bin/env python3
"""Isolated local setup and fresh-database bootstrap. Python 3.9+, stdlib only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / 'music/src/main/resources/db/baseline/V001__development.sql'


def read_env(slot):
    path = ROOT / '.local' / slot / 'config.json'
    if not path.is_file():
        raise RuntimeError(f'Run setup --slot {slot} first.')
    return json.loads(path.read_text())


def setup(slot):
    state = ROOT / '.local' / slot
    if state.exists():
        raise RuntimeError(f'{state} already exists; existing credentials were preserved.')
    state.mkdir(parents=True, mode=0o700)
    offset = 0 if slot == 'a' else 1
    values = {
        'SPRING_PROFILES_ACTIVE': 'local',
        'MUSIC_DB_HOST': '127.0.0.1', 'MUSIC_DB_PORT': str(3307 + offset),
        'MUSIC_DB_NAME': f'music_dev_{slot}', 'MUSIC_DB_USER': f'music_dev_{slot}',
        'MUSIC_DB_PASSWORD': secrets.token_hex(24),
        'MUSIC_DB_ROOT_PASSWORD': secrets.token_hex(24),
        'MUSIC_SERVER_PORT': str(8080 + offset),
        'MUSIC_JWT_SECRET': secrets.token_hex(64),
        'MUSIC_UPLOAD_PATH': str(state / 'uploads'),
        'MUSIC_UPLOAD_TEMP_PATH': str(state / 'chunks'),
        'MUSIC_SMTP_PORT': str(1025 + offset),
        'VITE_DEV_PORT': str(5173 + offset),
        'VITE_PROXY_TARGET': f'http://127.0.0.1:{8080 + offset}',
        'VITE_API_BASE_URL': f'http://127.0.0.1:{8080 + offset}',
    }
    for directory in ['uploads', 'chunks', 'indexes', 'logs']:
        (state / directory).mkdir(mode=0o700)
    files = {
        'config.json': json.dumps(values, indent=2) + '\n',
        'env.sh': ''.join(f'export {k}={shlex.quote(v)}\n' for k, v in values.items()),
        'compose.env': ''.join(f'{k}={v}\n' for k, v in values.items()
                               if k.startswith('MUSIC_DB_')),
    }
    for name, content in files.items():
        with (state / name).open('x') as output:
            output.write(content)
        (state / name).chmod(0o600)
    print(f'Created slot {slot}. Source .local/{slot}/env.sh in each terminal.')
    print(f'Backend {8080 + offset}; frontend {5173 + offset}; MySQL {3307 + offset}.')


def database_query(slot, mysql):
    values = read_env(slot)
    from baseline import validate
    validate(slot, values)
    # A whitelist guards the generated fresh-database workflow against wrong targets.
    if values['MUSIC_DB_NAME'] != f'music_dev_{slot}':
        raise RuntimeError('Refusing to initialize a database outside the selected dev slot.')
    if mysql:
        command = [mysql, '--host=' + values['MUSIC_DB_HOST'],
                   '--port=' + values['MUSIC_DB_PORT'],
                   '--user=' + values['MUSIC_DB_USER'],
                   '--database=' + values['MUSIC_DB_NAME'], '--batch', '--skip-column-names']
        environment = {**os.environ, 'MYSQL_PWD': values['MUSIC_DB_PASSWORD']}
    else:
        command = ['docker', 'compose', '--env-file', str(ROOT / '.local' / slot / 'compose.env'),
                   '-p', f'music-{slot}', '-f', str(ROOT / 'compose.dev.yml'), 'exec', '-T',
                   'mysql', 'sh', '-c', 'export MYSQL_PWD="$MYSQL_PASSWORD"; '
                   'exec mysql --user="$MYSQL_USER" --database="$MYSQL_DATABASE" '
                   '--batch --skip-column-names']
        environment = os.environ.copy()
    def query(sql):
        return subprocess.run(command, cwd=ROOT, input=sql, text=True, env=environment,
                              check=True, capture_output=True).stdout.strip()
    return query


def init_db(slot, mysql):
    query = database_query(slot, mysql)
    values = read_env(slot)
    count = query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();')
    if count != '0':
        raise RuntimeError(f'Refusing nonempty {values["MUSIC_DB_NAME"]} ({count} tables). '
                           'No DROP, overwrite, or repair was attempted.')
    query(SQL.read_text())
    from upload_ownership_migration import migrate
    migrate(lambda sql: query(sql).splitlines())
    print(f'Initialized {values["MUSIC_DB_NAME"]}; SQL SHA256={hashlib.sha256(SQL.read_bytes()).hexdigest()}')
    print(query('SELECT version, description FROM development_schema_version;'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'init-db', 'migrate-uploads'])
    parser.add_argument('--slot', choices=['a', 'b'], required=True)
    parser.add_argument('--mysql', help='Native MySQL client executable; otherwise use Compose.')
    args = parser.parse_args()
    try:
        if args.action == 'setup':
            setup(args.slot)
        elif args.action == 'init-db':
            init_db(args.slot, args.mysql)
        else:
            from upload_ownership_migration import migrate
            query = database_query(args.slot, args.mysql)
            print(json.dumps(migrate(lambda sql: query(sql).splitlines()), indent=2))
    except subprocess.CalledProcessError as exc:
        print(f'ERROR: MySQL command failed (exit {exc.returncode}). {exc.stderr.strip()}', file=sys.stderr)
        return 1
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
