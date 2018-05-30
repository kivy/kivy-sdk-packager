from __future__ import absolute_import, print_function
import sys
from os.path import join, sep
from os import walk
from .common import *

__version__ = '0.1.18'

sdl2_ver = '2.0.8'
sdl2_mixer_ver = '2.0.2'
sdl2_ttf_ver = '2.0.14'
sdl2_image_ver = '2.0.3'


def get_sdl2(cache, build_path, arch, pyver, package, output, compiler='mingw'):
    data = []
    suffix = 'VC.zip' if compiler == 'msvc' else 'mingw.tar.gz'

    for name, ver in (
        ('https://www.libsdl.org/release/SDL2-devel-{}-{}',
         sdl2_ver),
        ('https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-devel-{}-{}',
         sdl2_mixer_ver),
        ('http://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-devel-{}-{}',
         sdl2_ttf_ver),
        ('http://www.libsdl.org/projects/SDL_image/release/SDL2_image-devel-{}-{}',
         sdl2_image_ver)):
        url = name.format(ver, suffix)
        fname = url.split('/')[-1]
        if 'ttf' in name and compiler == 'mingw':
            # see https://github.com/kivy/kivy/issues/3889 and
            # https://bugzilla.libsdl.org/show_bug.cgi?id=3241
            url = 'https://drive.google.com/uc?export=download&id=0B1_HB9J8mZepenN2YmtHSUZmb0U'
            local_url = download_cache(r'C:\kivy_no_cache', url, build_path, 'SDL2_ttf-devel-2.0.13-mingw.tar.gz')
        else:
            local_url = download_cache(cache, url, build_path, fname)

        exec_binary(
            'Extracting {}'.format(local_url),
            [zip7, 'x', '-y', local_url], cwd=build_path, shell=True, exclude=zip_q)
        if compiler == 'mingw':
            exec_binary(
                'Extracting {}'.format(local_url[:-3]),
                [zip7, 'x', '-y', local_url[:-3]], cwd=build_path, shell=True, exclude=zip_q)

        base_dir = local_url.replace('-{}'.format(suffix), '').replace('-devel', '')

        if compiler == 'mingw':
            if arch == '64':
                base_dir = join(base_dir, 'x86_64-w64-mingw32')
            else:
                base_dir = join(base_dir, 'i686-w64-mingw32')
            sources = {p: join(base_dir, p) for p in ('lib', 'include', 'bin')}
        else:
            sources = {
                'lib': join(base_dir, 'lib', 'x64' if arch == '64' else 'x86'),
                'include': join(base_dir, 'include')
                }

        for d in sources.keys():
            # bin goes to python/share/kivy_package
            src = sources[d]
            for dirpath, dirnames, filenames in walk(src):
                root = dirpath

                if d == 'bin':
                    base = join('share', package, 'bin')
                elif d == 'lib':
                    base = 'libs'
                elif d == 'include':
                    if compiler == 'mingw':
                        base = d
                    else:
                        base = join(d, 'SDL2')

                dirpath = dirpath.replace(src, '')
                if dirpath and dirpath[0] == sep:
                    dirpath = dirpath[1:]

                for filename in filenames:
                    is_dev = d != 'bin'
                    if compiler != 'mingw' and d == 'lib':
                        if filename.endswith('lib'):
                            base = 'libs'
                        else:
                            base = join('share', package, 'bin')
                            is_dev = False
                    data.append((
                        join(root, filename), join(d, dirpath, filename),
                        join(base, dirpath), is_dev))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'zlib')


if __name__ == '__main__':
    parse_args(get_sdl2)
