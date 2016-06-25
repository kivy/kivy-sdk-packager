from __future__ import absolute_import, print_function
import sys
from os.path import join, sep
from os import walk
from .common import *

__version__ = '0.1.1'

batch = '''
call "C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\vcvarsall.bat" {}
msbuild .\\src\\angle.sln /property:Configuration=Release /property:Platform={}
'''


def get_angle(cache, build_path, arch, pyver, package, output, compiler='mingw'):
    url = 'https://github.com/Microsoft/angle/archive/ms-master.zip'
    local_url = download_cache(cache, url, build_path)

    print('Extracting angle {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])
    data = []

    if compiler == 'mingw':
        raise Exception('Cannot compile angle with mingw')

    src = 'x86_amd64' if arch == '64' else 'x86'
    target = 'x64' if arch == '64' else 'Win32'
    with open(join(base_dir, 'compile.bat'), 'w') as fh:
        fh.write(batch.format(src, target))

    exec_binary(
        '', [join(base_dir, 'compile.bat')], cwd=base_dir, shell=True)

    for dll in ('d3dcompiler_47.dll', 'libEGL.dll', 'libGLESv2.dll'):
        data.append((
            join(z, 'src', 'Release_{}'.format(target), dll), join('bin', dll),
            join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_angle)
