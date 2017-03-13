from __future__ import absolute_import, print_function
import sys
from os.path import join, sep, split
from os import walk, environ
from glob import glob
from .common import *

__version__ = '0.1.6'

msvc_batch = '''
call "C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\vcvarsall.bat" {}
msbuild .\\src\\angle.sln /property:Configuration=Release /property:Platform={}
'''

mingw_batch = '''
set MSYSTEM=MINGW{}
set CHERE_INVOKING=1
C:\\msys64\\usr\\bin\\pacman --noconfirm --sync --refresh --refresh --sysupgrade --sysupgrade
C:\\msys64\\usr\\bin\\bash --login -c "pacman -S --noconfirm gyp-git git python2; \
makepkg --noconfirm --noprogressbar --skippgpcheck"
'''


def get_angle(cache, build_path, arch, pyver, package, output, compiler='mingw'):
    mingw = compiler == 'mingw'
    if mingw:
        url = 'https://github.com/matham/MINGW-packages/archive/patch-1.zip'
    else:
        url = 'https://github.com/Microsoft/angle/archive/ms-master.zip'
    local_url = download_cache(cache, url, build_path, force=True)

    print('Extracting {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])
    data = []

    if mingw:
        if arch == '64':
            mingw_arch = 'x86_64'
            mingw_bit = 'mingw64'
            win_arch = 'x64'
            bits = '64'
        else:
            mingw_arch = 'i686'
            mingw_bit = 'mingw32'
            win_arch = 'x86'
            bits = '32'

        batch = mingw_batch.format(bits)

        base_dir = join(base_dir, 'mingw-w64-angleproject-git')
        out_dir = join(
            base_dir, 'pkg', 'mingw-w64-{}-angleproject-git'.format(mingw_arch),
            mingw_bit, 'bin')
        d3d_out = join(
            environ['ProgramFiles(x86)'], 'Windows Kits', '8.1', 'Redist',
            'D3D', win_arch)

        for pat, b in (
                ('libwinpthread-*.dll', bits), ('libstdc++-*.dll', bits),
                ('libgcc_s_dw2-*.dll', '32')):
            root = join('C:\\msys64', 'mingw{}'.format(b), 'bin', pat)
            f = sorted(glob(root))[-1]
            name = split(f)[-1]
            data.append(
                (f, join('bin', name), join('share', package, 'bin'), False))
    else:
        src = 'x86_amd64' if arch == '64' else 'x86'
        target = 'x64' if arch == '64' else 'Win32'
        batch = msvc_batch.format(src, target)
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
