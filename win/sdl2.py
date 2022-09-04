from os import walk
from .common import *

__version__ = '0.4.6'

sdl2_ver = '2.24.0'
sdl2_mixer_ver = '2.6.2'
sdl2_ttf_ver = '2.20.1'
sdl2_image_ver = '2.6.2'


def get_sdl2(cache, build_path, arch, package, output, download_only=False):
    data = []

    paths = []
    for name, ver in (
        ('https://github.com/libsdl-org/SDL/releases/download/'
         'release-{0}/SDL2-devel-{0}-VC.zip',
         sdl2_ver),
        ('https://www.libsdl.org/projects/SDL_mixer/release/'
         'SDL2_mixer-devel-{}-VC.zip',
         sdl2_mixer_ver),
        ('https://github.com/libsdl-org/SDL_ttf/releases/download/'
         'release-{0}/SDL2_ttf-devel-{0}-VC.zip',
         sdl2_ttf_ver),
        ('http://www.libsdl.org/projects/SDL_image/release/'
         'SDL2_image-devel-{}-VC.zip',
         sdl2_image_ver)):
        url = name.format(ver)
        fname = url.split('/')[-1]
        paths.append(download_cache(cache, url, build_path, fname))

    if download_only:
        return

    for local_url in paths:
        exec_binary(
            'Extracting {}'.format(local_url),
            [zip7, 'x', '-y', local_url], cwd=build_path, shell=True,
            exclude=zip_q)

        base_dir = local_url.replace('-VC.zip', '').replace('-devel', '')

        sources = {
            'lib': join(base_dir, 'lib', arch),
            'include': join(base_dir, 'include')
            }

        for d, src in sources.items():
            # bin goes to python/share/kivy_package
            for dirpath, dirnames, filenames in walk(src):
                root = dirpath

                if d == 'bin':
                    base = join('share', package, 'bin')
                elif d == 'lib':
                    base = 'libs'
                elif d == 'include':
                    # sdl2 h files are in the root include, but need to be
                    # placed under sdl2 directory
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

    make_package(
        join(build_path, 'project'), package, data, __version__, output,
        'zlib')


if __name__ == '__main__':
    parse_args(get_sdl2)
