from __future__ import absolute_import, print_function
from .common import *

__version__ = "0.0.8"


def get_sdl3(cache, build_path, arch, package, output, download_only=False):
    data = []
    base_dll_dir = join(build_path, "bin")

    sources = {
            'bin': join(build_path, 'bin'),
            'lib': join(build_path, 'lib'),
            'include': join(build_path, 'include')
            }

    for d, src in sources.items():
        # bin goes to python/share/kivy_package
        for dirpath, dirnames, filenames in os.walk(src):
            root = dirpath

            if d == 'bin':
                base = join('share', package, 'bin')
            elif d == 'lib':
                base = 'libs'
            elif d == 'include':
                base = 'include'
            else:
                assert False

            dirpath = dirpath.replace(src, '')
            if dirpath and dirpath[0] == sep:
                dirpath = dirpath[1:]

            for filename in filenames:
                is_dev = d != 'bin'
                if d == 'lib':
                    if filename.endswith('lib'):
                        base = 'libs'
                    else:
                        base = join('share', package, 'bin')
                        is_dev = False
                data.append((
                    join(root, filename), join(d, dirpath, filename),
                    join(base, dirpath), is_dev))

    make_package(
        join(build_path, "project"), package, data, __version__, output, "MIT"
    )


if __name__ == "__main__":
    parse_args(get_sdl3)
