from __future__ import absolute_import, print_function
from .common import *
from zipfile import ZipFile

__version__ = '0.3.0'

glew_ver = '2.2.0'


def get_glew(cache, build_path, arch, package, output, download_only=False):
    url = ('http://jaist.dl.sourceforge.net/project/glew/glew/{}/glew-{}-win32.zip'.
           format(glew_ver, glew_ver))
    local_url = download_cache(cache, url, build_path)
    if download_only:
        return

    print('Extracting glew {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])

    data = []
    for fname in glob(join(z, 'include', 'GL', '*')):
        data.append((
            fname, fname.replace(z, '').strip(sep), join('include', 'GL'), True))

    target = 'x64' if arch == 'x64' else 'Win32'

    data.append((
        join(z, 'lib', 'Release', target, 'glew32.lib'), join('lib', 'glew32.lib'), 'libs', True))

    data.append((
        join(z, 'bin', 'Release', target, 'glew32.dll'), join('bin', 'glew32.dll'),
        join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_glew)
