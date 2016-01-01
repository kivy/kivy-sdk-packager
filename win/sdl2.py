from __future__ import absolute_import, print_function
import sys
from os.path import join, sep
from os import walk
from .common import *

__version__ = '0.1.3'

sdl2_ver = '2.0.3'
sdl2_mixer_ver = '2.0.0'
sdl2_ttf_ver = '2.0.12'
sdl2_image_ver = '2.0.0'

drive_map = {
    'SDL2-devel-{}-mingw.tar.gz'.format(sdl2_ver): '0B1_HB9J8mZepUXlqeDFPd0oybk0',
    'SDL2_mixer-devel-{}-mingw.tar.gz'.format(sdl2_mixer_ver): '0B1_HB9J8mZepQ1l4WlUyT0t2ODQ',
    'SDL2_ttf-devel-{}-mingw.tar.gz'.format(sdl2_ttf_ver): '0B1_HB9J8mZepdjRSdVVZdjBjWFE',
    'SDL2_image-devel-{}-mingw.tar.gz'.format(sdl2_image_ver): '0B1_HB9J8mZepOXNoSWJCYlI3QW8',
    'SDL_platform.h': '0B1_HB9J8mZepNmZjcVFtRklINzA'
}


def get_gdrive_link(fname):
    gid = drive_map[fname]
    url = 'https://drive.google.com/uc?export=download&id={}'.format(gid)
    return url


def get_sdl2(cache, build_path, arch, pyver, package, output):
    data = []

    for name, ver in (
        ('https://www.libsdl.org/release/SDL2-devel-{}-mingw.tar.gz',
         sdl2_ver),
        ('https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-devel-{}-mingw.tar.gz',
         sdl2_mixer_ver),
        ('http://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-devel-{}-mingw.tar.gz',
         sdl2_ttf_ver),
        ('http://www.libsdl.org/projects/SDL_image/release/SDL2_image-devel-{}-mingw.tar.gz',
         sdl2_image_ver)):
        url = name.format(ver)
        fname = url.split('/')[-1]
        url = get_gdrive_link(fname)
        local_url = download_cache(cache, url, build_path, fname)

        exec_binary(
            'Extracting {}'.format(local_url),
            [zip7, 'x', '-y', local_url], cwd=build_path, shell=True, exclude=zip_q)
        exec_binary(
            'Extracting {}'.format(local_url[:-3]),
            [zip7, 'x', '-y', local_url[:-3]], cwd=build_path, shell=True, exclude=zip_q)

        base_dir = local_url.replace('-mingw.tar.gz', '').replace('-devel', '')
        if arch == '64':
            base_dir = join(base_dir, 'x86_64-w64-mingw32')
        else:
            base_dir = join(base_dir, 'i686-w64-mingw32')

        if fname.startswith('SDL2-'):
            url = 'https://hg.libsdl.org/SDL/raw-file/e217ed463f25/include/SDL_platform.h'
            url = get_gdrive_link('SDL_platform.h')
            local_url = download_cache(cache, url, join(base_dir, 'include', 'SDL2'),
                                       'SDL_platform.h')

        for d in ('lib', 'include', 'bin'):
            # bin goes to python/share/kivy_package
            src = join(base_dir, d)
            for dirpath, dirnames, filenames in walk(src):
                root = dirpath

                if d == 'bin':
                    base = join('share', package, 'bin')
                elif d == 'lib':
                    base = 'libs'
                else:
                    base = d

                dirpath = dirpath.replace(src, '')
                if dirpath and dirpath[0] == sep:
                    dirpath = dirpath[1:]

                for filename in filenames:
                    data.append((
                        join(root, filename), join(d, dirpath, filename),
                        join(base, dirpath), d != 'bin'))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'zlib')


if __name__ == '__main__':
    parse_args(get_sdl2)
