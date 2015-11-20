from __future__ import print_function
import subprocess
import sys
import os
from os import makedirs, listdir, remove, rename
from os.path import exists, join, abspath, isdir, isfile, splitext, dirname
from os.path import basename, split as path_split
import argparse
from subprocess import Popen, PIPE
from shutil import rmtree, copytree, copy2
from glob import glob
from collections import defaultdict
import hashlib
import re
from re import match
import csv
import platform
from zipfile import ZipFile
try:
    from ConfigParser import ConfigParser
    import urlparse
    from urllib import urlretrieve as pyurlretrieve
except ImportError:
    from configparser import ConfigParser
    from urllib import parse as urlparse
    from urllib.request import urlretrieve as pyurlretrieve
import ssl
from functools import partial
import inspect
from time import sleep

zip_q = re.compile('^Extracting .*')

if 'context' in inspect.getargspec(pyurlretrieve)[0]:
    pyurlretrieve = partial(pyurlretrieve, context=ssl._create_unverified_context())

zip7 = r'C:\Program Files\7-Zip\7z.exe'


def urlretrieve(*largs, **kwargs):
    for i in range(5):
        try:
            return pyurlretrieve(*largs, **kwargs)
        except IOError:
            sleep(60)


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


def report_hook(block_count, block_size, total_size):
    p = block_count * block_size * (100.0 / total_size if total_size else 1)
    print("\b\b\b\b\b\b\b\b\b", "%06.2f%%" % p, end=' ')


def exec_binary(status, cmd, env=None, cwd=None, shell=True, exclude=None):
    print(status)
    print(' '.join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, cwd=cwd, shell=shell)
    a, b = proc.communicate()
    if a:
        if exclude is not None:
            a = '\n'.join(
                [l for l in a.splitlines() if match(exclude, l) is None])
        print(a, end='')
    if b:
        if exclude is not None:
            b = '\n'.join(
                [l for l in b.splitlines() if match(exclude, l) is None])
        print(b, end='')


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
from os import environ
if environ.get('KIVY_USE_SETUPTOOLS'):
    from setuptools import setup
else:
    from distutils.core import setup

data = [
    {}
]

setup(
    name='{}',
    version={},
    author='Kivy Crew',
    author_email='kivy-dev@googlegroups.com',
    url='http://kivy.org/',
    license='MIT',s
    packages=[{}],
    data_files=data)
'''

def make_package(build_path, name, files, version, output):
    setup_path = join(build_path, name)
    if exists(setup_path):
        raise IOError('{} already exists'.format(name))

    makedirs(setup_path)
    data = defaultdict(list)
    data_dev = defaultdict(list)
    for src, dst, target, is_dev in files:
        dst_full = join(setup_path, dst)
        dst_dir = path_split(dst_full)[0]
        if not exists(dst_dir):
            makedirs(dst_dir)

        copy2(src, dst_full)
        if is_dev:
            data_dev[target].append(dst)
        else:
            data[target].append(dst)

    for dev, package_data in ((True, data_dev), (False, data)):
        package_name = 'kivy_{}_dev' if dev else 'kivy_{}'
        package_name = package_name.format(name)

        makedirs(join(setup_path, package_name))
        with open(join(setup_path, package_name, '__init__.py'), 'wb'):
            pass

        for k, v in package_data.items():
            package_data[k] = "[\n        r'{}'\n    ]".format("',\n        r'".join(v))
        data_files = ',\n    '.join((map(lambda x: "('{}', {})".format(*x), package_data.items())))
        setup_f = setup.format(data_files, package_name, version, package_name)

        with open(join(setup_path, 'setup.py'), 'wb') as fh:
            fh.write(setup_f)

        exec_binary(
            'Making wheel',
            ['python', 'setup.py', 'bdist_wheel', '-d', output], cwd=setup_path,
            shell=True)
