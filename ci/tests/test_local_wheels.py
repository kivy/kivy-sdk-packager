"""Regression tests for the Windows CI helper, separate from Kivy's own suite.

Run from the repository root:
    python -m unittest discover -s ci/tests -p "test_local_wheels.py" -v

The ``Windows CI helper tests`` workflow runs this command on Python 3.9 with
pip >=25.3 and PowerShell. Tiny synthetic wheels and a self-contained build
backend exercise real pip resolution, including isolated build dependencies,
without building Kivy.
"""

import base64
from contextlib import redirect_stdout
import hashlib
from importlib.metadata import PackageNotFoundError
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import venv
import zipfile

from ci.check_wheel_origins import check_origins


ROOT = Path(__file__).resolve().parents[2]
PWSH = shutil.which('pwsh')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_pair(directory, target='glew', value='LOCAL', dotted=False):
    """Build installable fixture wheels whose payload identifies their origin."""
    directory.mkdir(parents=True, exist_ok=True)
    wheels = []
    for suffix in ('', '_dev'):
        name = 'kivy_deps.' + target + suffix
        stem = name.replace('.', '_') + '-1.0'
        info = stem + '.dist-info'
        files = {
            'kivy_deps/__init__.py': b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n",
            'kivy_deps/{}/__init__.py'.format(target + suffix):
                ('VALUE = {!r}\n'.format(value)).encode(),
            stem + '.data/data/' + ('include/fixture.h' if suffix else 'share/glew/bin/fixture.dll'):
                value.encode(),
            info + '/METADATA': ('Metadata-Version: 2.1\nName: {}\nVersion: 1.0\n'.format(name)).encode(),
            info + '/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: py3-none-any\n',
        }
        records = []
        for member, data in files.items():
            encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            records.append('{},{},{}'.format(member, 'sha256=' + encoded, len(data)))
        files[info + '/RECORD'] = ('\n'.join(records) + '\n' + info + '/RECORD,,\n').encode()
        filename = (name if dotted else name.replace('.', '_')) + '-1.0-py3-none-any.whl'
        archive = directory / filename
        with zipfile.ZipFile(archive, 'w') as stream:
            for member, data in files.items():
                stream.writestr(member, data)
        wheels.append(archive)
    return wheels


def write_constraints(path, wheels):
    path.write_text('\n'.join('kivy_deps.glew{} @ {}#sha256={}'.format(
        suffix, wheel.as_uri(), digest(wheel)) for suffix, wheel in zip(('', '_dev'), wheels)) + '\n',
        encoding='utf8')


class LocalWheelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='local wheels #ü ')
        self.addCleanup(temporary.cleanup)
        # Match PowerShell's long paths when Windows TEMP contains an 8.3 alias.
        self.root = Path(temporary.name).resolve()
        self.wheels = make_pair(self.root / 'dist')
        self.constraints = self.root / 'local-wheel-constraints.txt'
        write_constraints(self.constraints, self.wheels)

    def records(self):
        return {name: {'url': wheel.as_uri(), 'archive_info': {'hashes': {'sha256': digest(wheel)}}}
                for name, wheel in zip(('kivy_deps.glew', 'kivy_deps.glew_dev'), self.wheels)}

    def check_records(self, records):
        def package(name):
            if name not in records:
                raise PackageNotFoundError(name)
            return SimpleNamespace(version='1.0', read_text=lambda filename: json.dumps(records[name]))
        with patch('ci.check_wheel_origins.distribution', side_effect=package), redirect_stdout(io.StringIO()) as output:
            check_origins(self.constraints)
        return output.getvalue()

    def test_both_local_origins_and_legacy_hash_record(self):
        records = self.records()
        records['kivy_deps.glew_dev']['archive_info'] = {'hash': 'sha256=' + digest(self.wheels[1])}
        output = self.check_records(records)
        self.assertEqual(output.count('Verified local wheel:'), 2)
        self.assertIn('%23', output)
        self.assertIn('%C3%BC', output)

    def test_python39_underscore_metadata_lookup(self):
        records = {name.replace('.', '_'): record for name, record in self.records().items()}
        self.assertEqual(self.check_records(records).count('Verified local wheel:'), 2)

    def test_wrong_or_missing_origin_hash_and_changed_archive_fail(self):
        for case in ('published', 'other-file', 'missing', 'hash', 'changed-archive'):
            with self.subTest(case=case):
                records = self.records()
                record = records['kivy_deps.glew_dev']
                if case == 'published':
                    record['url'] = 'https://example.test/published.whl'
                elif case == 'other-file':
                    record['url'] = (self.root / 'other.whl').as_uri()
                elif case == 'missing':
                    record.clear()
                elif case == 'hash':
                    record['archive_info']['hashes']['sha256'] = '0' * 64
                else:
                    self.wheels[1].write_bytes(b'changed after selection')
                with self.assertRaises(RuntimeError):
                    self.check_records(records)

    def test_malformed_constraints_fail(self):
        for content in ('', 'one line\n', 'a @ file:///a#sha256=x\na @ file:///b#sha256=y\n',
                        'a @ https://example.test/a#sha256=x\nb @ file:///b#sha256=y\n'):
            with self.subTest(content=content):
                self.constraints.write_text(content, encoding='utf8')
                with self.assertRaises(ValueError):
                    check_origins(self.constraints)

    @unittest.skipUnless(PWSH, 'PowerShell is required for helper checks')
    def test_real_powershell_selection_and_failure_guards(self):
        """Record real helper calls to check constraints and origin-check ordering."""
        script = '''
            . $env:WHEEL_TEST_HELPER
            $script:pythonCalls = [System.Collections.Generic.List[object]]::new()
            function python {
                $script:pythonCalls.Add(@($args))
                $global:LASTEXITCODE = 0
                if ($args[-1] -eq '--help') {
                    $global:LASTEXITCODE = [int]$env:WHEEL_TEST_PIP_EXIT_CODE
                    $env:WHEEL_TEST_PIP_HELP
                } elseif ($args[0] -eq '-c' -and $args[1].StartsWith('import kivy.tests ')) {
                    $env:WHEEL_TEST_TESTS
                }
            }
            function git { $global:LASTEXITCODE = 0; 'fixture-commit' }
            try { Test-kivy -KivyTestTarget $env:WHEEL_TEST_PROFILE; exit 0 }
            catch { Write-Output $_.Exception.Message; exit 1 }
            finally {
                ConvertTo-Json -InputObject $script:pythonCalls.ToArray() -Depth 3 |
                    Set-Content -LiteralPath $env:WHEEL_TEST_CALLS -Encoding utf8
            }
        '''
        cases = [(target, 'valid') for target in ('angle', 'glew', 'gstreamer', 'sdl2', 'sdl3')]
        cases += [('glew', kind) for kind in
                  ('missing', 'ambiguous', 'version-mismatch', 'old-pip', 'pip-failure')]
        for target, kind in cases:
            with self.subTest(target=target, kind=kind):
                root = self.root / (target + kind)
                wheels = make_pair(root / 'dist', target, dotted=target == 'angle')
                (root / 'kivy_src').mkdir()
                (root / 'kivy_src/pyproject.toml').write_text('[build-system]\n')
                (root / 'installed-tests').mkdir()
                if kind == 'missing':
                    wheels[1].unlink()
                elif kind == 'ambiguous':
                    shutil.copyfile(wheels[0], wheels[0].with_name(
                        wheels[0].name.replace('-1.0-', '-1.0-1-')))
                elif kind == 'version-mismatch':
                    wheels[1].rename(wheels[1].with_name(wheels[1].name.replace('-1.0-', '-2.0-')))
                env = {**os.environ, 'PACKAGE_TARGET': target, 'PACKAGE_ARCH': 'x64',
                       'WHEEL_TEST_HELPER': str(ROOT / 'ci/windows_ci.ps1'),
                       'WHEEL_TEST_PROFILE': 'stable' if target == 'sdl2' else 'development',
                       'WHEEL_TEST_CALLS': str(root / 'python-calls.json'),
                       'WHEEL_TEST_TESTS': str(root / 'installed-tests'),
                       'WHEEL_TEST_PIP_HELP': '' if kind == 'old-pip' else '--build-constraint',
                       'WHEEL_TEST_PIP_EXIT_CODE': '1' if kind == 'pip-failure' else '0',
                       'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT': '1'}
                result = subprocess.run([PWSH, '-NoLogo', '-NoProfile', '-Command', script],
                                        env=env, cwd=root, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, timeout=30)
                self.assertEqual(result.returncode, 0 if kind == 'valid' else 1, result.stdout)
                calls = json.loads((root / 'python-calls.json').read_text(encoding='utf-8-sig'))
                installs = [call for call in calls if call[-1] == './kivy_src[full,dev]']
                if kind == 'valid':
                    constraints = root / 'local-wheel-constraints.txt'
                    self.assertEqual(constraints.read_text().splitlines(),
                                     ['kivy_deps.{}{} @ {}#sha256={}'.format(
                                         target, suffix, wheel.as_uri(), digest(wheel))
                                      for suffix, wheel in zip(('', '_dev'), wheels)])
                    self.assertEqual(len(installs), 1)
                    install = installs[0]
                    for option in ('--constraint', '--build-constraint'):
                        self.assertIn((option, str(constraints)), list(zip(install, install[1:])))
                    checks = [index for index, call in enumerate(calls) if call ==
                              [str(ROOT / 'ci/check_wheel_origins.py'), str(constraints)]]
                    self.assertEqual(len(checks), 2)
                    self.assertLess(calls.index(install), checks[0])
                    self.assertLess(checks[0], calls.index(['-m', 'pytest', '.']))
                    self.assertGreater(checks[1], calls.index(['-m', 'pytest', '.']))
                else:
                    self.assertFalse(installs)
                    if kind in ('old-pip', 'pip-failure'):
                        self.assertIn('requires pip >=25.3', result.stdout)
                        self.assertIn('python -m pip install --upgrade "pip>=25.3"', result.stdout)
                    else:
                        self.assertIn('do not match' if kind == 'version-mismatch' else
                                      'found 0' if kind == 'missing' else 'found 2', result.stdout)

    @unittest.skipUnless(PWSH, 'PowerShell is required for helper checks')
    def test_real_powershell_smoke_ordering_and_failure_guards(self):
        """Record real smoke-helper calls to check install, origin and smoke ordering."""
        script = '''
            . $env:WHEEL_TEST_HELPER
            $script:pythonCalls = [System.Collections.Generic.List[object]]::new()
            function python {
                $script:pythonCalls.Add(@($args))
                $global:LASTEXITCODE = 0
                if ($args[0] -eq $env:WHEEL_TEST_FAILING_SCRIPT) { $global:LASTEXITCODE = 1 }
            }
            try { Test-wheel-smoke; exit 0 }
            catch { Write-Output $_.Exception.Message; exit 1 }
            finally {
                ConvertTo-Json -InputObject $script:pythonCalls.ToArray() -Depth 3 |
                    Set-Content -LiteralPath $env:WHEEL_TEST_CALLS -Encoding utf8
            }
        '''
        checker = str(ROOT / 'ci/check_wheel_origins.py')
        smoke = str(ROOT / 'ci/smoke_test_wheels.py')
        cases = {'valid': ('sdl2', ''), 'unsupported': ('glew', ''), 'missing': ('sdl2', ''),
                 'origin-failure': ('sdl2', checker), 'smoke-failure': ('sdl2', smoke)}
        for kind, (target, failing) in cases.items():
            with self.subTest(kind=kind):
                root = self.root / ('smoke-' + kind)
                wheels = make_pair(root / 'dist', target)
                if kind == 'missing':
                    wheels[1].unlink()
                env = {**os.environ, 'PACKAGE_TARGET': target, 'PACKAGE_ARCH': 'x64',
                       'WHEEL_TEST_HELPER': str(ROOT / 'ci/windows_smoke.ps1'),
                       'WHEEL_TEST_CALLS': str(root / 'python-calls.json'),
                       'WHEEL_TEST_FAILING_SCRIPT': failing,
                       'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT': '1'}
                result = subprocess.run([PWSH, '-NoLogo', '-NoProfile', '-Command', script],
                                        env=env, cwd=root, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, timeout=30)
                self.assertEqual(result.returncode, 0 if kind == 'valid' else 1, result.stdout)
                calls = json.loads((root / 'python-calls.json').read_text(encoding='utf-8-sig'))
                constraints = str(root / 'local-wheel-constraints.txt')
                expected = [['-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall']
                            + [str(wheel) for wheel in wheels], [checker, constraints], [smoke, target]]
                if kind == 'valid':
                    self.assertEqual(calls, expected)
                elif kind == 'unsupported':
                    self.assertEqual(calls, [])
                    self.assertIn('only defined for PACKAGE_TARGET=sdl2', result.stdout)
                elif kind == 'missing':
                    self.assertEqual(calls, [])
                    self.assertIn('found 0', result.stdout)
                elif kind == 'origin-failure':
                    self.assertEqual(calls, expected[:2])
                    self.assertIn('Verifying the installed local dependency wheels failed', result.stdout)
                else:
                    self.assertEqual(calls, expected)
                    self.assertIn('The dependency smoke test failed', result.stdout)

    def test_real_isolated_build_constraints(self):
        """Local outer packages alone must not satisfy the isolated-build check."""
        help_result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--help'],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if '--build-constraint' not in help_result.stdout:
            self.skipTest('pip >=25.3 is required for the isolated-resolver regression')
        alternate = make_pair(self.root / 'alternate', value='PUBLISHED')
        environment = self.root / 'consumer environment'
        venv.EnvBuilder(with_pip=False).create(environment)
        executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('PIP_') and key not in ('PYTHONPATH', 'PYTHONHOME')}
        env.update({'PIP_CONFIG_FILE': os.devnull, 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
                    'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        pip_env = {**env, **({'PYTHONPATH': os.environ['PYTHONPATH']}
                            if 'PYTHONPATH' in os.environ else {})}

        def run(arguments, pip=False, success=True):
            command = ([sys.executable, '-m', 'pip', '--python', str(executable)] if pip else
                       [str(executable)]) + list(map(str, arguments))
            result = subprocess.run(command, env=pip_env if pip else env, cwd=self.root,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=120)
            self.assertEqual(result.returncode == 0, success, result.stdout)
            return result.stdout

        install = ['install', '--no-index', '--no-deps']
        checker = [ROOT / 'ci/check_wheel_origins.py', self.constraints]
        run(install + alternate, pip=True)
        run(checker, success=False)
        run(install + ['--force-reinstall'] + self.wheels, pip=True)
        run(checker)
        project = self.root / 'consumer source'
        project.mkdir()
        (project / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["kivy_deps.glew>=0", "kivy_deps.glew_dev>=0"]\n'
            'build-backend = "backend"\nbackend-path = ["."]\n')
        expected = {name: {'url': wheel.as_uri(), 'sha256': digest(wheel)} for name, wheel in
                    zip(('kivy_deps.glew', 'kivy_deps.glew_dev'), self.wheels)}
        (project / 'expected.json').write_text(json.dumps(expected))
        (project / 'backend.py').write_text(BACKEND)
        common = ['install', '--no-index', '--find-links', self.root / 'alternate',
                  '--no-cache-dir', '--constraint', self.constraints]
        run(common + ['--build-constraint', self.constraints, project], pip=True)
        run(checker)
        output = run(common + [project], pip=True, success=False)
        self.assertIn('wrong isolated origin', output)
        bad_hashes = self.constraints.read_text()
        for wheel in self.wheels:
            bad_hashes = bad_hashes.replace(digest(wheel), '0' * 64)
        self.constraints.write_text(bad_hashes, encoding='utf8')
        output = run(common + ['--build-constraint', self.constraints, project],
                     pip=True, success=False)
        self.assertIn('hash', output.lower())


BACKEND = '''\
import base64, hashlib, importlib, json
from importlib.metadata import distribution
from pathlib import Path
from zipfile import ZipFile

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    for name, expected in json.loads(Path('expected.json').read_text()).items():
        package = distribution(name.replace('.', '_'))
        direct = json.loads(package.read_text('direct_url.json') or '{}')
        assert direct.get('url') == expected['url'], 'wrong isolated origin'
        assert direct['archive_info']['hashes']['sha256'] == expected['sha256']
        assert importlib.import_module(name).VALUE == 'LOCAL'
        if name.endswith('_dev'):
            header = next(file for file in package.files if file.name == 'fixture.h')
            assert package.locate_file(header).read_bytes() == b'LOCAL'
    info = 'ci_fixture_consumer-1.0.dist-info'
    files = {info + '/METADATA': b'Metadata-Version: 2.1\\nName: ci-fixture-consumer\\nVersion: 1.0\\nRequires-Dist: kivy_deps.glew>=0\\nRequires-Dist: kivy_deps.glew_dev>=0\\n',
             info + '/WHEEL': b'Wheel-Version: 1.0\\nRoot-Is-Purelib: true\\nTag: py3-none-any\\n'}
    records = []
    for member, data in files.items():
        value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        records.append(member + ',sha256=' + value + ',' + str(len(data)))
    files[info + '/RECORD'] = ('\\n'.join(records) + '\\n' + info + '/RECORD,,\\n').encode()
    filename = 'ci_fixture_consumer-1.0-py3-none-any.whl'
    with ZipFile(Path(wheel_directory) / filename, 'w') as archive:
        for member, data in files.items():
            archive.writestr(member, data)
    return filename
'''


if __name__ == '__main__':
    unittest.main()
