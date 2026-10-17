"""Verify installed dependency wheel origins against generated local constraints."""

import argparse
import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname


def check_origins(constraints):
    """Verify the runtime/development pair selected by ``windows_ci.ps1``.

    A published wheel can have the same name/version as a local build. Compare
    installed PEP 610 (direct_url.json) origins and archive hashes with the
    generated two-entry constraints to prove installation kept this job's wheels.
    CI calls this before and after the installed Kivy test suite.
    """
    requirements = [line.split(' @ ', 1) for line in
                    Path(constraints).read_text(encoding='utf-8-sig').splitlines()]
    if (len(requirements) != 2 or any(len(row) != 2 for row in requirements) or
            len({row[0] for row in requirements}) != 2):
        raise ValueError('Expected two distinct named local wheel constraints')
    for name, reference in requirements:
        verify_installed_wheel_origin(name, reference)


def verify_installed_wheel_origin(name, reference):
    """Match one installed distribution and its local archive to a pinned URL/hash."""
    url = urlparse(reference)
    if url.scheme != 'file' or url.netloc or not url.fragment.startswith('sha256='):
        raise ValueError('Expected a hash-bound local wheel reference: ' + name)
    archive = Path(url2pathname(url.path)).resolve(strict=True)
    expected_hash = url.fragment.removeprefix('sha256=')
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    package = distribution(name)
    record = json.loads(package.read_text('direct_url.json') or '{}')
    installed = urlparse(record.get('url', ''))
    if (installed.scheme != 'file' or installed.netloc or
            os.path.normcase(os.path.realpath(url2pathname(installed.path))) !=
            os.path.normcase(str(archive))):
        raise RuntimeError('Installed wheel origin mismatch: ' + name)
    info = record.get('archive_info', {})
    recorded_hash = (info.get('hashes', {}).get('sha256') or
                     info.get('hash', '').removeprefix('sha256='))
    if recorded_hash != expected_hash or digest.hexdigest() != expected_hash:
        raise RuntimeError('Installed wheel archive hash mismatch: ' + name)
    print('Verified local wheel: {} {} {}#sha256={}'.format(
        name, package.version, archive.as_uri(), expected_hash), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('constraints', type=Path)
    check_origins(parser.parse_args().constraints)
