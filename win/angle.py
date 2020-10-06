from __future__ import absolute_import, print_function
from .common import *

__version__ = '0.3.0'


def get_angle(cache, build_path, arch, package, output, download_only=False):
    data = []
    base_dir = join(build_path, 'Release_{}'.format(arch))
    for dll in ('libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_47.dll'):
        data.append((join(base_dir, dll), join('bin', dll),
                     join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_angle)
