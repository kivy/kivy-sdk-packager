from __future__ import absolute_import, print_function
from .common import *
from zipfile import ZipFile

__version__ = '0.1.12'

glew_ver = '2.1.0'

batch = '''
"C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\Common7\\IDE\\devenv.exe" .\\build\\vc12\\glew.sln /upgrade
call "C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\vcvarsall.bat" {}
msbuild .\\build\\vc12\\glew.sln /property:Configuration=Release /property:Platform={}
'''


def get_glew(cache, build_path, arch, pyver, package, output):
    url = ('http://jaist.dl.sourceforge.net/project/glew/glew/{}/glew-{}.zip'.
           format(glew_ver, glew_ver))
    local_url = download_cache(cache, url, build_path)

    print('Extracting glew {}'.format(local_url))
    with open(local_url, 'rb') as fd:
        ZipFile(fd).extractall(join(build_path, package))

    z = base_dir = join(build_path, package, list(listdir(join(build_path, package)))[0])

    data = []
    for fname in glob(join(z, 'include', 'GL', '*')):
        data.append((
            fname, fname.replace(z, '').strip(sep), join('include', 'GL'), True))

    src = 'amd64' if arch == '64' else 'amd64_x86'
    target = 'x64' if arch == '64' else 'Win32'
    with open(join(base_dir, 'compile.bat'), 'w') as fh:
        fh.write(batch.format(src, target))
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
