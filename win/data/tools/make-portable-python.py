'''Module that when called from the command line will go through all
files in the Scripts directory of the current python and will change the
python path hardcoded in these files from a full python path, to just
python.exe.
'''

import sys
import os
from os import listdir, remove, rename
from os.path import dirname, join, isfile
from re import compile, sub
from tempfile import mkstemp
from shutil import copystat

pypat = compile(b'#!(.+?)python.exe')


def make_portable():
    scripts = join(dirname(sys.executable), 'Scripts')
    for fname in listdir(scripts):
        f = join(scripts, fname)
        if not isfile(f):
            continue
        with open(f, 'rb') as fh:
            old = fh.read()
        new = sub(pypat, b'#!python.exe', old)
        if old == new:
            continue

        fd, tmp = mkstemp(prefix=fname, dir=scripts)
        os.close(fd)
        try:
            with open(tmp, 'wb') as fh:
                fh.write(new)
        except:
            print("Couldn't write {}".format(tmp))
            continue

        copystat(f, tmp)
        try:
            remove(f)
        except:
            print("Couldn't remove {}".format(f))
            continue
        rename(tmp, f)
        print('Updated {}'.format(f))


if __name__ == '__main__':
    make_portable()
