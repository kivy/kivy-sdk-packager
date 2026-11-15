"""Check that a rebuilt dependency wheel packages the same files as a reference wheel.

Compares every member except ``*.dist-info/`` metadata. Data files are matched
by their path inside the ``<name>-<version>.data/`` directory, and the
``__version__`` assignment in package modules is ignored, so a patch release
that only bumps ``__version__`` compares equal to the release it repackages.
"""

import argparse
import hashlib
from pathlib import Path
import re
import zipfile

VERSION_LINE = re.compile(rb"^__version__ = '[^']*'$", re.MULTILINE)


def wheel_contents(path):
    """Map comparable member paths to SHA-256 digests of their normalized bytes."""
    contents = {}
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            top = member.split('/', 1)[0]
            if top.endswith('.dist-info') or member.endswith('/'):
                continue
            data = archive.read(member)
            if top.endswith('.data'):
                member = member.split('/', 1)[1]
            elif member.endswith('.py'):
                data = VERSION_LINE.sub(b"__version__ = ''", data)
            contents[member] = hashlib.sha256(data).hexdigest()
    return contents


def compare_wheels(reference, candidate):
    expected, actual = wheel_contents(reference), wheel_contents(candidate)
    problems = ['missing ' + name for name in sorted(expected.keys() - actual.keys())]
    problems += ['unexpected ' + name for name in sorted(actual.keys() - expected.keys())]
    problems += ['changed ' + name for name in sorted(expected.keys() & actual.keys())
                 if expected[name] != actual[name]]
    if problems:
        raise RuntimeError('{} does not match {}:\n  {}'.format(
            Path(candidate).name, Path(reference).name, '\n  '.join(problems)))
    print('Matched {} files: {} == {}'.format(
        len(expected), Path(candidate).name, Path(reference).name), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    compare_wheels(args.reference, args.candidate)
