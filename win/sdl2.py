from __future__ import absolute_import, print_function
from os import walk
from .common import *

__version__ = '0.2.0'

sdl2_ver = '2.0.10'
sdl2_mixer_ver = '2.0.4'
sdl2_ttf_ver = '2.0.15'
sdl2_image_ver = '2.0.5'


def get_sdl2(cache, build_path, arch, package, output, download_only=False):
    data = []

    paths = []
    for name, ver in (
        ('https://www.libsdl.org/release/SDL2-devel-{}-VC.zip',
         sdl2_ver),
        ('https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-devel-{}-VC.zip',
         sdl2_mixer_ver),
        ('http://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-devel-{}-VC.zip',
         sdl2_ttf_ver),
        ('http://www.libsdl.org/projects/SDL_image/release/SDL2_image-devel-{}-VC.zip',
         sdl2_image_ver)):
        url = name.format(ver)
        fname = url.split('/')[-1]
        paths.append(download_cache(cache, url, build_path, fname))

    if download_only:
        return

    for local_url in paths:
        exec_binary(
            'Extracting {}'.format(local_url),
            [zip7, 'x', '-y', local_url], cwd=build_path, shell=True, exclude=zip_q)

        base_dir = local_url.replace('-VC.zip', '').replace('-devel', '')

        sources = {
            'lib': join(base_dir, 'lib', arch),
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
                    base = join(d, 'SDL2')
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

    make_package(join(build_path, 'project'), package, data, __version__, output, 'zlib')


if __name__ == '__main__':
    parse_args(get_sdl2)
