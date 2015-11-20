from __future__ import absolute_import, print_function
import sys
from os.path import join
from os import walk
from .common import *

__version__ = '0.1.0'

sdl2_ver = '2.0.3'
sdl2_mixer_ver = '2.0.0'
sdl2_ttf_ver = '2.0.12'
sdl2_image_ver = '2.0.0'


def get_sdl2(build_path, arch, pyver, package, output):
    data = []
    for name, ver in (
        ('https://www.libsdl.org/release/SDL2-devel-{}-mingw.tar.gz',
         sdl2_ver),
        ('https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-devel-{}-mingw.tar.gz',
         sdl2_mixer_ver),
        ('http://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-devel-2.0.12-mingw.tar.gz',
         sdl2_ttf_ver),
        ('http://www.libsdl.org/projects/SDL_image/release/SDL2_image-devel-{}-mingw.tar.gz',
         sdl2_image_ver)):
        url = name.format(ver)
        local_url = join(build_path, url.split('/')[-1])

        print('\nGetting {}'.format(url))
        if not exists(local_url):
            print("Progress: 000.00%", end=' ')
            local_url, _ = urlretrieve(url, local_url,
                                       reporthook=report_hook)
            print(" [Done]")

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

    print('\nGetting patched SDL_platform.h')
    local_url = join(build_path, 'SDL_platform.h')
    if not exists(local_url):
        local_url, _ = urlretrieve(
        'https://hg.libsdl.org/SDL/raw-file/e217ed463f25/include/SDL_platform.h',
        local_url)
    copy2(local_url, join(base_dir, 'include', 'SDL2'))

    for d in ('lib', 'include', 'bin'):
        # bin goes to python/share/kivy_package
        for dirpath, dirnames, filenames in walk(join(base_dir, d)):
            root = join(base_dir, d, dirpath)
            base = d if d != 'bin' else join('share', 'kivy_{}'.format(package))

            for filename in filenames:
                data.append((
                    join(root, filename), join(d, dirpath, filename),
                    join(base, dirpath, filename), d != 'bin'))


    make_package(join(build_path, 'project'), package, data, __version__, output)


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) % 2:
        raise Exception('Unmatched args')
    get_sdl2(**dict(zip(args[0::2], args[1::2])))
