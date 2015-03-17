from __future__ import print_function
import subprocess
import sys
import os
from os import makedirs, listdir, remove, rename
from os.path import exists, join, abspath, isdir, isfile, splitext, dirname, basename
import argparse
from subprocess import Popen, PIPE
from shutil import rmtree, copytree, copy2
from glob import glob
import hashlib
import re
import csv
import platform
from zipfile import ZipFile
import urlparse
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


def report_hook(block_count, block_size, total_size):
    p = block_count * block_size * (100.0 / total_size if total_size else 1)
    print("\b\b\b\b\b\b\b\b\b", "%06.2f%%" % p, end=' ')


def exec_binary(status, cmd, env=None, cwd=None, shell=True):
    print(status)
    print(' '.join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, cwd=cwd, shell=shell)
    a, b = proc.communicate()
    if a:
        print(a, end='')
    if b:
        print(b, end='')


class WindowsPortablePythonBuild(object):
    '''Custom build command that builds portable win32 python
    and kivy deps.
    '''

    pip_deps = ['cython', 'docutils', 'pygments', 'requests', 'plyer',
                'kivy-garden', 'wheel']

    dist_dir = None
    temp_dir = ''
    build_pythons = []
    mingw = ''
    no_mingw = False
    mingw64 = ''
    clean = False
    strip_py = False
    strip_tk = False
    kivy_zip = ''
    zip7 = ''

    def parse_args(self):
        py_curr = 'py{}.{}.{}_x{}:{}'.format(
            sys.version_info.major, sys.version_info.minor,
            sys.version_info.micro,
            '64' if platform.machine().endswith('64') else '86',
            sys.executable)
        parser = argparse.ArgumentParser(description='Generates portable package'
            ' for usage with kivy. It includes python and MinGW for 64 and 32 bit '
            'platforms. To use, you specify the python versions to build, paths '
            'to MinGW')
        parser.add_argument("--dir", help='path of dist directory to use '
            'for building the portable python, the end result will be output '
            'to this directory. Defaults to cwd ({}).'.format(os.getcwd()),
            default=os.getcwd())

        parser.add_argument("--pythons", help='Comma separated list of the '
        'pythons to generate, in the format of `pyversion_arch,pyversion_arch\
        ...`, where version is e.g. 2.7.6 and arch is either x86 or x64. For example: '
        'py2.7.8_x86.\nDownload links will automatically be generated from '
        "https://www.python.org/ftp/python/."
        'One can also directly specify the binary link using '
        '`pyversion_arch:link:MD5,pyversion_arch:link,pyversion_arch...`, \
        where link can be remote or local (MD5 is optional).\n. If the local \
        link is a python exe, it will be installed to that previously \
        installed python, otherwise it must be a .msi file. if not specified, \
        the current python process exe will be used ({}).'.format(py_curr),
        default=py_curr)

        mingw_default='http://iweb.dl.sourceforge.net\
/project/mingw/Installer/mingw-get/mingw-get-0.6.2-beta-20131004-1\
/mingw-get-0.6.2-mingw32-beta-20131004-1-bin.zip'
        parser.add_argument("--mingw", help='''Path to MinGW.
It is either a local path to a mingw installation (directory), a url path to download
the mingw-get zip, or a local path to the mingw-get zip file. If not specified it will
download mingw-get (from {}) and use it to install mingw, unless --no-mingw is
specified.'''.format(mingw_default),
        default=mingw_default)
        parser.add_argument(
            "--no-mingw",
            help='Whether mingw (and/or mingw-w64) should be downloaded.'
            'Defaults to False.', action="store_true",
            dest='no_mingw')

        mingw64_default=r'http://iweb.dl.sourceforge.net\
/project/mingw-w64/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-\
builds/4.9.2/threads-win32/seh/x86_64-4.9.2-release-win32-seh-rt_v3-rev1.7z'
        parser.add_argument("--mingw64", help='''Path to MinGW-w64. \
It is either a local path to a mingw-w64 installation, a url path to download \
mingw-w64, or a local path to the mingw-w64 .7z file. If not supplied it will \
download mingw-w64 (from {}) and install it, unless --no-mingw is \
specified.'''.format(mingw64_default.replace('%', '%%')),
        default=mingw64_default)

        pywin_default='http://iweb.dl.sourceforge.net/project/pywin32/pywin32/Build%20219/'
        parser.add_argument("--pywin", help='Initial path of the pywin '
            'binaries url on sourceforge. The url must end with "Build number",'
            ' where number is the build number. '
            'Defaults to {}'.format(pywin_default.replace('%', '%%')),
            default=pywin_default)
        parser.add_argument("--clean", help='Whether to remove the python '
            'and MinGW builds if it already exists in --dir', action="store_true")
        parser.add_argument(
            "--strip-python", help='Whether to strip the tests and other files'
            ' from python', action="store_true", dest='strip_py')
        parser.add_argument(
            "--strip-tk", help='Whether to remove all tk/tcl files when '
            'strip-python is True.', action="store_true", dest='strip_tk')
        parser.add_argument(
            "--kivy-ver", help='The version of kivy to install.'
            'Could be a kivy git tag (e.g. 1.8.0), or a kivy git branch name '
            '(e.g. master). Defaults to master.', default='master', dest='kivy_ver')
        zip7 = r'C:\Program Files\7-Zip\7z.exe'
        parser.add_argument(
            "--7zip", help='The path to the 7-zip binary. Only required for x64 '
            'installations when mingw is downloaded. Defaults to {}'.format(zip7),
            default=zip7, dest='zip7')

        args = parser.parse_args()
        self.dist_dir = base = abspath(args.dir)
        self.temp_dir = join(base, 'python-kivy_temp')

        self.mingw = args.mingw
        self.mingw64 = args.mingw64
        self.no_mingw = args.no_mingw
        self.strip_py = args.strip_py
        self.strip_tk = args.strip_tk
        self.clean = args.clean
        self.kivy_zip = 'https://github.com/kivy/kivy/archive/{}.zip'.format(args.kivy_ver)
        self.zip7 = args.zip7

        pywin_base = args.pywin
        m = re.match('.+Build(?: |%20)([0-9]+)/?', pywin_base)
        if m is None:
            raise Exception('pywin url does not end with "Build number"')
        pywin = '{}/pywin32-{}.win{}-py{}.exe'.format(pywin_base, m.group(1), '{}', '{}')

        py_pat = re.compile('py([0-9])\.([0-9])\.?(.*?)?_x([0-9]+)')
        build_py = []
        for py in args.pythons.split(','):
            py = py.strip().split(':')
            md5 = None
            name = py[0]

            m = re.match(py_pat, name)
            if m is None:
                raise Exception('{} does not match the pyversion_arch pattern'.
                                format(name))
            pyver = '.'.join([g for g in m.groups()[:3] if g is not None])
            arch = m.group(4)
            pywin_url = pywin.format(
                '-amd64' if arch == '64' else '32',
                '.'.join([g for g in m.groups()[:2] if g is not None]))


            if len(py) == 1:  # download from url
                fname = 'python-{}'.format(pyver)
                if arch == '64':
                    fname += '.amd64'
                fname += '.msi'
                link = '/'.join(
                    ['https://www.python.org/ftp/python', pyver, fname])
            else:
                link = py[1]
                if len(py) > 2:
                    md5 = py[2]

            build_py.append((name, pyver, arch, link, md5, pywin_url))
        self.build_pythons = build_py

    def run(self):
        self.parse_args()
        width = self.width = 30

        print("-" * width)
        print("Generating python distribution")
        print("-" * width)
        print("\nPreparing Build...")
        print("-" * width)
        dist_dir = self.dist_dir
        print('Working in {}'.format(dist_dir))

        temp = self.temp_dir
        if exists(temp):
            print('Using temp directory {}'.format(temp))
        else:
            print('Creating temp directory {}'.format(temp))
            makedirs(temp)

        for pyname, pyver, arch, link, md5, pywin_url in self.build_pythons:
            print('\n')
            print("-" * width)
            print("Preparing python {}".format(pyname))
            print("-" * width)
            name = pyname.replace('.', '')
            build_path = join(dist_dir, name)
            patch_py = False
            if link.endswith('.exe'):  # already existing python
                pydir = dirname(link)
            else:
                pydir = join(build_path, 'Python')

            if self.clean and exists(build_path):
                print("*Cleaning old build dir, {}".format(build_path))
                rmtree(build_path, ignore_errors=True)
            if not exists(build_path):
                print("*Creating build directory: {}".format(build_path))
                makedirs(build_path)
            self.get_python(width, pydir, link, md5)
            print('Done installing Python')
            patch_py = arch == '64'

            mingw = join(build_path, 'MinGW')
            if not self.no_mingw:
                if arch == '64':
                    mingw = self.do_mingw64(mingw, os.environ)
                else:
                    mingw = self.do_mingw(mingw, os.environ)

            env = os.environ.copy()
            env['PATH'] = '{};{};{};{}'.format(pydir, join(mingw, 'bin'),
                join(pydir, 'Scripts'), env['PATH'])
            env['PYTHONPATH'] = ''

            if patch_py:
                print('Patching python')
                self.patch_python_x64(pydir, env, pyver)

            self.get_glew(pydir, mingw, arch, env)

            self.get_pip_deps(pydir, env, pywin_url)

        print('Done')

    def get_python(self, width, pydir, url, md5):
        if url.endswith('.msi'):
            local_url = join(self.temp_dir, url.split('/')[-1])
            if not exists(local_url) and not exists(url):
                print("*Downloading: {}".format(url))
                print("Progress: 000.00%", end=' ')
                f, _ = urlretrieve(url, local_url, reporthook=report_hook)
                print(" [Done]")

                if md5:
                    print("Verifying MD5", end=' ')
                    with open(f, 'rb') as fd:
                        md5_read = hashlib.md5(fd.read()).hexdigest()
                        if md5_read != md5:
                            raise Exception(
                                'MD5 not verified. Gotten: {}, expected: {}'.
                                format(md5_read, md5))
                    print(" Done")
            elif exists(local_url):
                f = local_url
            elif exists(url):
                f = url

            if not exists(pydir):
                makedirs(pydir)
            print('Removing old python {}'.format(pydir))
            rmtree(pydir, ignore_errors=True)
            exec_binary(
                "*Extracting python to {}".format(pydir),
                ['msiexec', '/a', f, '/qb', 'TARGETDIR={}'.format(pydir)],
                shell=False)
            try:
                print('Removing {}'.format(join(pydir, basename(f))))
                remove(join(pydir, basename(f)))
            except:
                pass

        f = join(pydir, 'Lib', 'distutils', 'distutils.cfg')
        print('Writing {}'.format(f))
        if exists(f):
            raise Exception('{} already exists'.format(f))
        with open(f, 'w') as fd:
            fd.write('[build]\ncompiler=mingw32\n')
        if not exists(join(pydir, 'Scripts')):
            makedirs(join(pydir, 'Scripts'))

        if not self.clean:
            return

        print("\nCleaning python")
        print("-" * width)

        dirs = ['Doc', join('Lib', 'test'), join('Lib', 'idlelib')]
        if self.strip_tk:
            dirs += ['tcl', join('Lib', 'lib-tk')]
        for d in dirs:
            print('Removing {}'.format(d))
            rmtree(join(pydir, d), ignore_errors=True)

        ignore_list = ()
        for f in listdir(join(pydir, 'Lib')):
            if f in ignore_list:
                continue
            f = join(pydir, 'Lib', f)
            if not isdir(f):
                continue

            dirs = os.listdir(f)
            if 'test' in dirs and isdir(join(f, 'test')):
                f = join(f, 'test')
            elif 'tests' in dirs and isdir(join(f, 'tests')):
                f = join(f, 'tests')
            else:
                continue
            print('Removing {}'.format(f))
            rmtree(f, ignore_errors=True)

        if self.strip_tk:
            for f in listdir(join(pydir, 'DLLs')):
                if (f.startswith('tcl') or f.startswith('tk') or
                    f.startswith('_tkinter')):
                    f = join(pydir, 'DLLs', f)
                    print('Removing {}'.format(f))
                    remove(f)

    def patch_python_x64(self, pydir, env, pyver):
        libs = join(pydir, 'libs')
        py = 'python{}'.format(pyver.replace('.', '')[:2])
        pylib = py + '.lib'
        pydll = join(pydir, py + '.dll')
        pydef = join(libs, py + '.def')

        # see http://bugs.python.org/issue4709 and
        # http://ascend4.org/Setting_up_a_MinGW-w64_build_environment
        remove(join(libs, 'old_' + pylib))
        rename(join(libs, pylib), join(libs, 'old_' + pylib))
        exec_binary('Gendefing ' + pydll, ['gendef.exe', pydll], env, libs)
        exec_binary('Generating libpython.a',
                    ['dlltool', '--dllname', pydll, '--def', pydef,
                     '--output-lib', 'lib' + py + '.a'], env, libs, shell=True)
        remove(pydef)

        print('Getting python pyconfig.h patch')
        url = 'http://bugs.python.org/file12411/mingw-w64.patch'
        include = join(pydir, 'include')
        patch_name = url.split('/')[-1]
        patch = join(include, patch_name)
        if not exists(patch):
            patch, _ = urlretrieve(url, patch)
        exec_binary('Patching {}\\pyconfig.h'.format(include),
                    ['git', 'apply', patch_name], env, include, shell=True)
        remove(patch)

        # see http://bugs.python.org/issue16472
        print('Patching cygwinccompiler.py')
        cyg = join(pydir, 'Lib', 'distutils', 'cygwinccompiler.py')
        with open(cyg) as fd:
            lines = fd.readlines()

        with open(cyg, 'w') as fd:
            for line in lines:
                if line == '        self.dll_libraries = get_msvcr()\n':
                    fd.write('        #self.dll_libraries = get_msvcr()\n')
                else:
                    fd.write(line)

    def do_mingw(self, mingw, env):
        url = self.mingw
        rmtree(mingw, ignore_errors=True)
        makedirs(mingw)
        if isdir(url):
            copytree(url, mingw)
            return mingw

        if not url.endswith('.zip'):
            raise Exception('Expected mingw to be a zip file, got {}'.format(url))

        local_url = join(self.temp_dir, url.split('/')[-1])
        if not exists(local_url) and not exists(url):
            print("*Downloading: {}".format(url))
            print("Progress: 000.00%", end=' ')
            f, _ = urlretrieve(url, local_url, reporthook=report_hook)
            print(" [Done]")
        elif exists(local_url):
            f = local_url
        elif exists(url):
            f = url

        print('Extracting mingw-get {}'.format(f))
        with open(f, 'rb') as fd:
            ZipFile(fd).extractall(mingw)
        exec_binary(
            'Installing MinGW', ['mingw-get.exe', 'install', 'gcc', 'mingw32-make'],
            env, join(mingw, 'bin'), shell=True)
        return mingw

    def do_mingw64(self, mingw, env):
        url = self.mingw
        rmtree(mingw, ignore_errors=True)
        makedirs(mingw)
        if isdir(url):
            copytree(url, mingw)
            return mingw

        local_url = join(self.temp_dir, url.split('/')[-1])
        if not exists(local_url) and not exists(url):
            print("*Downloading: {}".format(url))
            print("Progress: 000.00%", end=' ')
            f, _ = urlretrieve(url, local_url, reporthook=report_hook)
            print(" [Done]")
        elif exists(local_url):
            f = local_url
        elif exists(url):
            f = url

        mingw_extracted = join(self.temp_dir, splitext(basename(f))[0])
        rmtree(mingw_extracted, ignore_errors=True)
        exec_binary(
            'Extracting mingw-w64', [self.zip7, 'x', f, mingw_extracted], env,
            self.temp_dir, shell=True)
        print("Copying {}".format(mingw_extracted))
        copytree(mingw_extracted, mingw)
        return mingw

    def get_pip_deps(self, pydir, env, pywin):
        width = self.width
        temp_dir = self.temp_dir
        py = join(pydir, 'python.exe')

        print('Getting pip and easy install')
        url = 'https://bootstrap.pypa.io/get-pip.py'
        pip = join(temp_dir, url.split('/')[-1])
        if not exists(pip):
            pip, _ = urlretrieve(url, pip)
        url = 'https://bootstrap.pypa.io/ez_setup.py'
        ez = join(temp_dir, url.split('/')[-1])
        if not exists(ez):
            ez, _ = urlretrieve(url, ez)

        exec_binary('Installing pip', [py, pip], env, pydir, shell=True)
        exec_binary('Installing easy install', [py, ez], env, pydir, shell=True)

        pip = join(pydir, 'Scripts', 'pip.exe')
        for mod in self.pip_deps:
            exec_binary('Installing {}'.format(mod), [pip, 'install', mod],
                        env, pydir, shell=True)

        wheel = join(pydir, 'Scripts', 'wheel.exe')

        pywin_out = join(temp_dir, pywin.split('/')[-1])
        if not exists(pywin_out):
            print("Downloading pywin32. Progress: 000.00%", end=' ')
            pywin, _ = urlretrieve(pywin, pywin_out, reporthook=report_hook)
            print(' [Done]')

        exec_binary('Converting {} to wheel'.format(pywin),
                    [wheel, 'convert', pywin], env, temp_dir, shell=True)
        wheels = [join(temp_dir, f) for f in listdir(temp_dir) if f.startswith('pywin32') and f.endswith('.whl')]
        if len(wheels) != 1:
            raise Exception('Expected one pywin wheel, found {}'.format(wheels))

        exec_binary('Installing the wheel {}'.format(wheels[0]),
                    [wheel, 'install', '--force', wheels[0]], env, pydir, shell=True)

        print('Getting kivy')
        url = self.kivy_zip
        kivy = join(temp_dir, 'kivy.zip')
        try:
            remove(kivy)
        except:
            pass
        rmtree(join(temp_dir, 'kivy'), ignore_errors=True)
        rmtree(join(self.dist_dir, 'kivy'), ignore_errors=True)

        kivy, _ = urlretrieve(url, kivy)
        print('Extracting kivy {}'.format(kivy))
        with open(kivy, 'rb') as fd:
            ZipFile(fd).extractall(join(temp_dir, 'kivy'))
        makedirs(join(self.dist_dir, 'kivy'))
        copytree(
            join(temp_dir, 'kivy', list(listdir(join(temp_dir, 'kivy')))[0]),
            join(self.dist_dir, 'kivy'))
        exec_binary('Compiling kivy', [py, 'setup.py', 'build_ext', '--inplace'],
                    env, join(self.dist_dir, 'kivy'), shell=True)

        print('Copying tools')
        def copy_files(src, dst):
            for item in listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    copy_files(s, d)
                else:
                    shutil.copy2(s, d)
        copy_files(join(dirname(__file__), 'data'), pydir)

    def get_glew(self, pydir, mingw, arch, env):
        temp_dir = self.temp_dir
        glew_dir = 'glew-1.12.0'
        glew = glew_dir + '-win32.zip'
        url = 'http://iweb.dl.sourceforge.net/project/glew/glew/1.12.0/' + glew
        f = join(temp_dir, glew)
        arch_path = 'x64' if arch == '64' else 'Win32'

        if not exists(f):
            print("*Getting glew. Downloading: {}".format(url))
            print("Progress: 000.00%", end=' ')
            f, _ = urlretrieve(url, f, reporthook=report_hook)
            print(" [Done]")

        z = join(temp_dir, splitext(glew)[0])
        print('Extracting glew {}'.format(f))
        with open(f, 'rb') as fd:
            ZipFile(fd).extractall(z)
        z = join(z, glew_dir)

        print('Distributing glew to mingw and python')
        include = join(mingw, 'include', 'GL')
        py_include = join(pydir, 'include', 'GL')
        if not exists(include):
            makedirs(include)
        if not exists(py_include):
            makedirs(py_include)

        lib = join(mingw, 'lib')
        glew_dll = join(z, 'bin', 'Release', arch_path, 'glew32.dll')
        files = glob(join(z, 'include', 'GL', '*'))
        files = (
            zip(files, [include] * len(files)) +
            zip(files, [py_include] * len(files)) +
            [(glew_dll, join(mingw, 'bin')),
             (join(z, 'lib', 'Release', arch_path, 'glew32.lib'), lib),
             (join(z, 'lib', 'Release', arch_path, 'glew32s.lib'), lib)])
        for src_f, dst_f in files:
            try:
                copy2(src_f, dst_f)
            except:
                pass

        libs = join(pydir, 'libs')
        glew_def = join(libs, 'glew32.def')

        exec_binary('Gendefing ' + glew_dll, ['gendef.exe', glew_dll], env, libs)
        exec_binary('Generating libglew32.a',
                    ['dlltool', '--dllname', glew_dll, '--def', glew_def,
                     '--output-lib', 'libglew32.a'], env, libs)
        remove(glew_def)


if __name__ == '__main__':
    WindowsPortablePythonBuild().run()
