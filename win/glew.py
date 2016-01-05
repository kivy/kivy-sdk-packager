from __future__ import absolute_import, print_function
import sys
from os.path import join, sep
from os import walk
from .common import *

__version__ = '0.1.4'

glew_ver = '1.12.0'


def get_glew(cache, build_path, arch, pyver, package, output):
    url = ('http://iweb.dl.sourceforge.net/project/glew/glew/{0}/glew-{0}.zip'.
                         format(glew_ver))
    local_url = download_cache(cache, url, build_path)

    print('Extracting glew {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])
    exec_binary(
        'Compiling Glew',
        ['gcc', '-DGLEW_NO_GLU', '-O2', '-Wall', '-W', '-Iinclude', '-DGLEW_BUILD',
         '-o', 'src/glew.o', '-c', 'src/glew.c'], cwd=base_dir, shell=True)
    exec_binary(
        '',
        ['gcc', '-shared', '-Wl,-soname,libglew32.dll',
         '-Wl,--out-implib,lib/libglew32.dll.a', '-o', 'lib/glew32.dll',
         'src/glew.o', '-lglu32', '-lopengl32', '-lgdi32',
         '-luser32', '-lkernel32'], cwd=base_dir, shell=True)
    exec_binary(
        '', ['ar', 'cr', 'lib/libglew32.a', 'src/glew.o'], cwd=base_dir, shell=True)

    data = []
    for fname in glob(join(z, 'include', 'GL', '*')):
        data.append((
            fname, fname.replace(z, '').strip(sep), join('include', 'GL'), True))

    data.append((
        join(z, 'lib', 'libglew32.a'), join('lib', 'libglew32.a'), 'libs', True))
    data.append((
        join(z, 'lib', 'libglew32.dll.a'), join('lib', 'libglew32.dll.a'), 'libs', True))

    data.append((
        join(z, 'lib', 'glew32.dll'), join('bin', 'glew32.dll'),
        join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_glew)
