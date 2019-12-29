from __future__ import absolute_import, print_function
from .common import *
from zipfile import ZipFile
import tarfile

__version__ = '0.2.0'

glew_ver = '2.1.0'

batch = '''
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Enterprise\\Common7\\Tools\\VsDevCmd.bat"
devenv /upgrade .\\build\\vc15\\glew.sln
msbuild .\\build\\vc15\\glew.sln /property:Configuration=Release /property:Platform={}
'''


def get_glew(cache, build_path, arch, package, output, download_only=False):
    url = ('http://jaist.dl.sourceforge.net/project/glew/glew/{}/glew-{}.zip'.
           format(glew_ver, glew_ver))
    url = 'http://jaist.dl.sourceforge.net/project/glew/glew/snapshots/glew-20190928.tgz'
    local_url = download_cache(cache, url, build_path)
    if download_only:
        return

    print('Extracting glew {}'.format(local_url))
    # with open(local_url, 'rb') as fd:
    #     ZipFile(fd).extractall(join(build_path, package))
    tar = tarfile.open(local_url)
    tar.extractall(join(build_path, package))
    tar.close()

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])

    data = []
    for fname in glob(join(z, 'include', 'GL', '*')):
        data.append((
            fname, fname.replace(z, '').strip(sep), join('include', 'GL'), True))

    target = 'x64' if arch == 'x64' else 'Win32'
    with open(join(base_dir, 'compile.bat'), 'w') as fh:
        fh.write(batch.format(target))
    exec_binary(
        '', [join(base_dir, 'compile.bat')], cwd=base_dir, shell=True)

    data.append((
        join(z, 'lib', 'Release', target, 'glew32.lib'), join('lib', 'glew32.lib'), 'libs', True))

    data.append((
        join(z, 'bin', 'Release', target, 'glew32.dll'), join('bin', 'glew32.dll'),
        join('share', package, 'bin'), False))

    make_package(join(build_path, 'project'), package, data, __version__, output, 'MIT')


if __name__ == '__main__':
    parse_args(get_glew)
