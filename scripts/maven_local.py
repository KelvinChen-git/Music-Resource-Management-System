#!/usr/bin/env python3
"""Optional isolated Maven launcher for environments with per-session HTTPS proxies.

No pom/lock changes, no TLS bypass, no persistent proxy endpoints or credentials.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.parse
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slot', choices=['a', 'b'], default='b')
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('maven_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    home = args.java_home.resolve()
    if not (home / 'bin/java').is_file() or not (home / 'bin/javac').is_file():
        raise SystemExit('A complete JDK is required; JRE/compiler shims are not used')
    state = ROOT / '.local' / args.slot / 'maven'
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    env = {**os.environ, 'JAVA_HOME': str(home), 'MAVEN_USER_HOME': str(state)}
    env['PATH'] = str(home / 'bin') + os.pathsep + env.get('PATH', '')
    extra = args.maven_args[1:] if args.maven_args[:1] == ['--'] else args.maven_args
    with tempfile.TemporaryDirectory(prefix='session-', dir=state) as temporary:
        temporary = Path(temporary)
        proxy = urllib.parse.urlparse(env.get('HTTPS_PROXY') or env.get('https_proxy') or '')
        options = []
        if proxy.hostname and proxy.port:
            settings = temporary / 'settings.xml'
            auth = ''
            if proxy.username:
                auth = '<username>' + escape(urllib.parse.unquote(proxy.username)) + '</username>'
                if proxy.password: auth += '<password>' + escape(urllib.parse.unquote(proxy.password)) + '</password>'
            settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"><proxies><proxy><id>session-egress</id><active>true</active><protocol>http</protocol><host>' + escape(proxy.hostname) + '</host><port>' + str(proxy.port) + '</port>' + auth + '<nonProxyHosts>localhost|127.*|[::1]</nonProxyHosts></proxy></proxies></settings>\n')
            settings.chmod(0o600)
            options += ['-s', str(settings)]
            certificate = env.get('CODEX_PROXY_CERT')
            if certificate and Path(certificate).is_file():
                trust = temporary / 'cacerts'
                shutil.copyfile(home / 'lib/security/cacerts', trust); trust.chmod(0o600)
                subprocess.run([str(home / 'bin/keytool'), '-importcert', '-noprompt', '-alias', 'platform-egress-proxy',
                                '-file', certificate, '-keystore', str(trust), '-storepass', 'changeit'],
                               check=True, capture_output=True, text=True)
                env['MAVEN_OPTS'] = env.get('MAVEN_OPTS', '') + ' -Djavax.net.ssl.trustStore=' + str(trust) + ' -Djavax.net.ssl.trustStorePassword=changeit'
        command = ['sh', str(ROOT / 'music/mvnw'), '-f', str(ROOT / 'music/pom.xml'),
                   '-Dmaven.repo.local=' + str(state / 'repository'), *options, *extra]
        # Inherit current proxy lifetime; never reuse endpoints from an earlier exec.
        return subprocess.run(command, cwd=ROOT, env=env).returncode


if __name__ == '__main__':
    raise SystemExit(main())
