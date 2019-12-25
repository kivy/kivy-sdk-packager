from __future__ import print_function
import sys
import os
from os import makedirs, listdir, remove, rename, environ
from os.path import exists, join, abspath, isdir, isfile, splitext, dirname
from os.path import basename, split as path_split, sep
from subprocess import Popen, PIPE
from shutil import rmtree, copytree, copy2
from glob import glob
from collections import defaultdict
import hashlib
import re
from re import match
from urllib.request import urlretrieve as pyurlretrieve
from time import sleep

zip_q = re.compile('^Extracting .*')

zip7 = r'C:\Program Files\7-Zip\7z.exe'


def urlretrieve(*largs, **kwargs):
    for i in range(5):
        try:
            return pyurlretrieve(*largs, **kwargs)
        except IOError as e:
            print('{} failed "{}"'.format(largs[0], e))
            if i != 4:
                print('Trying again')
                sleep(10)
            else:
                raise


def sha1OfFile(filename):
    sha = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            block = f.read(2 ** 10) # Magic number: one-megabyte blocks.
            if not block:
                break
            sha.update(block)
        return sha.hexdigest()


def get_duplicates(basepath, min_size=0):
    d = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(basepath):
        for f in filenames:
            f = join(basepath, dirpath, f)
            s = os.stat(f).st_size
            if s >= min_size:
                d[s].append(f)
    d = {k:v for k, v in d.items() if len(v) > 1}

    dsha1 = defaultdict(list)
    for fnames in d.values():
        for f in fnames:
            dsha1[sha1OfFile(f)].append(f)
    return [v for v in dsha1.values() if len(v) > 1]


def get_file_duplicates(filename):
    sha1 = sha1OfFile(filename)
    basepath = dirname(filename)
    fname = basename(filename)
    files = []
    for f in listdir(basepath):
        if f == fname:
            continue
        full_f = join(basepath, f)
        if isfile(full_f) and sha1OfFile(full_f) == sha1:
            files.append(f)
    return files


def remove_from_dir(basepath, files):
    if not files:
        return
    d = defaultdict(list)
    for f in files:
        d[f[0]].append(f[1:])

    for f in listdir(basepath):
        if f not in d:
            f = join(basepath, f)
            if isdir(f):
                rmtree(f)
            else:
                remove(f)
        else:
            f_full = join(basepath, f)
            if isdir(f_full):
                remove_from_dir(f_full, [elems for elems in d[f] if elems])


def move_by_ext(root, ext, dest):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(ext):
                files.append((join(dirpath, filename), join(dest, filename)))

    for src, dest in files:
        rename(src, dest)


def report_hook(block_count, block_size, total_size):
    p = block_count * block_size * (100.0 / total_size if total_size else 1)
    print("\b\b\b\b\b\b\b\b\b", "%06.2f%%" % p, end=' ')


def exec_binary(status, cmd, env=None, cwd=None, shell=True, exclude=None):
    print(status)
    print(' '.join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, cwd=cwd, shell=shell)

    lines = iter(proc.stdout.readline, '')
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()

        if not exclude or not match(exclude, line):
            print(line, end=u'')

        retval = proc.poll()
        if retval is not None:
            break

    stdout, stderr = proc.communicate()

    if stdout:
        if isinstance(stdout, bytes):
            stdout = stdout.decode()
        if exclude:
            stdout = u'\n'.join(
                [l for l in stdout.splitlines() if not match(exclude, l)])
        print(stdout)

    if stderr:
        if isinstance(stderr, bytes):
            stderr = stderr.decode()
        if exclude:
            stderr = u'\n'.join(
                [l for l in stderr.splitlines() if not match(exclude, l)])
        print(stderr)

    ret_code = proc.returncode
    if ret_code:
        raise Exception(str(ret_code))


def copy_files(src, dst):
    if not exists(dst):
        makedirs(dst)
    for item in listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copy_files(s, d)
        else:
            copy2(s, d)


setup = '''
import os
from setuptools import setup
from setuptools.dist import Distribution

class BinaryDistribution(Distribution):
    def is_pure(self):
        return False

    def has_ext_modules(self):
        return True

data = [
    {}
]

setup(
    name='{}',
    version='{}',
    author='Kivy Crew',
    author_email='kivy-dev@googlegroups.com',
    description='Repackaged binary dependency of Kivy.',
    url='http://kivy.org/',
    license='{}',
    distclass=BinaryDistribution,
    packages=['kivy_deps', '{}'],
    data_files=data)
'''

dep_init = '''
"""The following code is required to make the dependency binaries available to
kivy when it imports this package.
"""

import sys
import os
from os.path import join, isdir, dirname

__all__ = ('dep_bins', )

__version__ = '{}'

{}

dep_bins = []
"""A list of paths that contain the binaries of this distribution.
Can be used e.g. with pyinstaller to ensure it copies all the binaries.
"""

_root = sys.prefix
dep_bins = [join(_root, 'share', '{}', 'bin')]
if isdir(dep_bins[0]):
    os.environ["PATH"] = dep_bins[0] + os.pathsep + os.environ["PATH"]
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(dep_bins[0])
else:
    dep_bins = []

{}
'''

dep_init_dev = '''
"""The following code is required to make the dependency binaries available to
kivy when it imports this package.
"""
__version__ = '{}'

'''


def make_package(build_path, name, files, version, output, license,
                 loader=('', '')):
    setup_path = join(build_path, name)
    if exists(setup_path):
        raise IOError('{} already exists'.format(name))

    makedirs(setup_path)
    data = defaultdict(list)
    data_dev = defaultdict(list)
    for src, dst, target, is_dev in files:
        target = target.rstrip(sep)
        dst_full = join(setup_path, dst)
        dst_dir = path_split(dst_full)[0]
        if not exists(dst_dir):
            makedirs(dst_dir)

        copy2(src, dst_full)
        if is_dev:
            data_dev[target].append(dst)
        else:
            data[target].append(dst)

    initial_files = list(listdir(setup_path))
    for dev, package_data in ((True, data_dev), (False, data)):
        package_name = '{}_dev' if dev else '{}'
        mod_name = package_name = package_name.format(name)
        package_name = 'kivy_deps.{}'.format(mod_name)

        # remove any additional files from before
        for fname in list(listdir(setup_path)):
            if fname in initial_files:
                continue

            full_fname = join(setup_path, fname)
            if isfile(full_fname):
                remove(full_fname)
            else:
                rmtree(full_fname, ignore_errors=True)

        makedirs(join(setup_path, 'kivy_deps', mod_name))
        readme = '''Binary dependency distribution of Kivy on Windows.

This package is a distribution of the kivy binary dependency {0}. To use,
just install it with `pip install kivy_deps.{0}`.\n'''.format(mod_name)

        with open(join(setup_path, 'README'), 'wb') as fh:
            fh.write(readme.encode('ascii'))

        with open(join(setup_path, 'kivy_deps', '__init__.py'), 'w') as fh:
            fh.write("__path__ = __import__('pkgutil').extend_path(__path__, __name__)")

        if not dev:
            deps_text = dep_init.format(version, loader[0], mod_name, loader[1])
        else:
            deps_text = dep_init_dev.format(version)
        with open(join(setup_path, 'kivy_deps', mod_name, '__init__.py'), 'wb') as fh:
            fh.write(deps_text.encode('ascii'))

        if package_data:
            for k, v in package_data.items():
                package_data[k] = "[\n        r'{}'\n    ]".format("',\n        r'".join(v))
            data_files = ',\n    '.join((map(lambda x: "(r'{}', {})".format(*x), package_data.items())))
        else:
            data_files = ''

        setup_f = setup.format(data_files, package_name, version, license, package_name)
        with open(join(setup_path, 'setup.py'), 'wb') as fh:
            fh.write(setup_f.encode('ascii'))

        exec_binary(
            'Making wheel',
            ['python', 'setup.py', 'bdist_wheel', '-d', output],
            cwd=setup_path, shell=True)

        setup_f = setup.format('', package_name, version, license, package_name)
        with open(join(setup_path, 'setup.py'), 'wb') as fh:
            fh.write(setup_f.encode('ascii'))

        exec_binary(
            'Making wheel',
            ['python', 'setup.py', 'sdist', '-d', output],
            cwd=setup_path, shell=True)


def parse_args(func):
    args = sys.argv[1:]
    if len(args) % 2:
        raise Exception('Unmatched args')
    func(**dict(zip(args[0::2], args[1::2])))


def download_cache(cache, url, local_dir, fname=None, force=False):
    if not isdir(cache):
        makedirs(cache)

    if fname is None:
        fname = url.split('/')[-1]
    cache_path = join(cache, fname)
    local_path = join(local_dir, fname)

    if not exists(cache_path) or force:
        print("Getting {}\nProgress: 000.00%".format(url), end=' ')
        urlretrieve(url, cache_path, reporthook=report_hook)
        print(" [Done]")

    copy2(cache_path, local_path)
    return local_path
