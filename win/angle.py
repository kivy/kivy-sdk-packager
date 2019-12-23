from __future__ import absolute_import, print_function
from .common import *
from zipfile import ZipFile

__version__ = '0.2.0'

msvc_batch = '''
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Enterprise\\Common7\\Tools\\VsDevCmd.bat"
devenv /upgrade .\\src\\angle.sln
msbuild .\\src\\angle.sln /property:Configuration=Release /property:Platform={}
'''


def get_angle(cache, build_path, arch, package, output, download_only=False):
    url = 'https://github.com/microsoft/angle/archive/' \
          'c61d0488abd9663e0d4d2450db7345baa2c0dfb6.zip'
    local_url = download_cache(cache, url, build_path)
    if download_only:
        return

    print('Extracting {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])
    data = []

    target = 'x64' if arch == 'x64' else 'Win32'
    batch = msvc_batch.format(target)
    d3d_out = out_dir = join(base_dir, 'src', 'Release_{}'.format(target))

    with open(join(base_dir, 'compile.bat'), 'w') as fh:
        fh.write(batch)
    exec_binary(
        '', [join(base_dir, 'compile.bat')], cwd=base_dir, shell=True)

    for dll in ('libEGL.dll', 'libGLESv2.dll'):
        data.append((join(out_dir, dll), join('bin', dll),
                     join('share', package, 'bin'), False))
    data.append((
        join(d3d_out, 'd3dcompiler_47.dll'), join('bin', 'd3dcompiler_47.dll'),
        join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_angle)
