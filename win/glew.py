from __future__ import absolute_import, print_function
import sys
from os.path import join, sep
from os import walk
from .common import *

__version__ = '0.1.10'

glew_ver = '2.1.0'

batch = '''
"C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\Common7\\IDE\\devenv.exe" .\\build\\vc12\\glew.sln /upgrade
call "C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\vcvarsall.bat" {}
msbuild .\\build\\vc12\\glew.sln /property:Configuration=Release /property:Platform={}
'''


def get_glew(cache, build_path, arch, pyver, package, output, compiler='mingw'):
    url = ('http://jaist.dl.sourceforge.net/project/glew/glew/{}/glew-{}.zip'.
           format(glew_ver, glew_ver))
    local_url = download_cache(cache, url, build_path)

    print('Extracting glew {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])

    data = []
    for fname in glob(join(z, 'include', 'GL', '*')):
        data.append((
            fname, fname.replace(z, '').strip(sep), join('include', 'GL'), True))

    if compiler == 'mingw':
        exec_binary(
            'Compiling Glew',
            ['gcc', '-DGLEW_NO_GLU', '-O2', '-Wall', '-W', '-Iinclude', '-DGLEW_BUILD',
             '-o', 'src/glew.o', '-c', 'src/glew.c'], cwd=base_dir, shell=True)
        # -nostdlib b/c https://stackoverflow.com/questions/38673228
        exec_binary(
            '',
            ['gcc', '-nostdlib', '-shared', '-Wl,-soname,libglew32.dll',
             '-Wl,--out-implib,lib/libglew32.dll.a', '-o', 'lib/glew32.dll',
             'src/glew.o', '-lglu32', '-lopengl32', '-lgdi32',
             '-luser32', '-lkernel32'], cwd=base_dir, shell=True)
        exec_binary(
            '', ['ar', 'cr', 'lib/libglew32.a', 'src/glew.o'], cwd=base_dir, shell=True)

        data.append((
            join(z, 'lib', 'libglew32.a'), join('lib', 'libglew32.a'), 'libs', True))
        data.append((
            join(z, 'lib', 'libglew32.dll.a'), join('lib', 'libglew32.dll.a'), 'libs', True))

        data.append((
            join(z, 'lib', 'glew32.dll'), join('bin', 'glew32.dll'),
            join('share', package, 'bin'), False))
    else:
        src = 'amd64' if arch == '64' else 'amd64_x86'
        target = 'x64' if arch == '64' else 'Win32'
        with open(join(base_dir, 'compile.bat'), 'w') as fh:
            fh.write(batch.format(src, target))
        exec_binary(
            '', [join(base_dir, 'compile.bat')], cwd=base_dir, shell=True)

        data.append((
            join(z, 'lib', 'Release', target, 'glew32.lib'), join('lib', 'glew32.lib'), 'libs', True))

        data.append((
            join(z, 'bin', 'Release', target, 'glew32.dll'), join('bin', 'glew32.dll'),
            join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_glew)
