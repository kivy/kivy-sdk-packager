from __future__ import print_function, absolute_import
from .common import *
import subprocess
import sys
import os
from os import makedirs, listdir, remove, rename
from os.path import exists, join, abspath, isdir, isfile, splitext, dirname, basename
import argparse
from subprocess import Popen, PIPE
from shutil import rmtree, copytree, copy2
from glob import glob
from collections import defaultdict
import hashlib
import re
from re import match
import csv
import platform
from zipfile import ZipFile
import ssl
from functools import partial
import inspect
from time import sleep


MSYSGIT_STIPPED_FILES = 'msysgit_stripped_files'


class WindowsPortablePythonBuild(object):
    '''Custom build command that builds portable win32 python
    and kivy deps.
    '''

    pip_deps = ['cython==0.21.2', 'docutils', 'pygments', 'requests', 'plyer',
                'kivy-garden', 'wheel', 'nose', 'sphinxcontrib-blockdiag',
                'sphinxcontrib-seqdiag', 'sphinxcontrib-actdiag',
                'sphinxcontrib-nwdiag', 'mock']

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
    kivy_lib = False
    glew_zip = ''
    gst_ver = ''
    no_gst = False
    no_sdl2 = False
    generic = True
    arg_build_path = 'py{pyver}_x{bitnes}'
    no_msysgit = False
    no_msysgit_strip = False
    mingw_strip = False
    no_gst_strip = False
    no_kivy = False

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
/project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-\
builds/4.9.2/threads-win32/sjlj/i686-4.9.2-release-win32-sjlj-rt_v4-rev2.7z'
        parser.add_argument("--mingw", help='''Path to MinGW-w64 32-bit. \
It is either a local path to a mingw-w64 32-bit installation, a url path to download \
mingw-w64 32-bit, or a local path to the mingw-w64 32-bit .7z file. If not supplied it will \
download mingw-w64 32-bit (from {}) and install it, unless --no-mingw is \
specified.'''.format(mingw_default.replace('%', '%%')),
        default=mingw_default)
        parser.add_argument(
            "--no-mingw",
            help='Whether mingw (and/or mingw-w64) should be downloaded. '
            'Defaults to False. If set, gcc needs to be in PATH, otherwise '
            'kivy and other pip deps will fail to be compiled.', action="store_true",
            dest='no_mingw')

        mingw64_default='http://iweb.dl.sourceforge.net\
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
            "--7zip", help='The full path to the 7-zip binary. Required for SDL2 '
            '. Defaults to {}'.format(zip7),
            default=zip7, dest='zip7')
        parser.add_argument(
            "--kivy-lib", help='Whether kivy should be installed in a directory '
            'in the distribution directory (False), or if it should be installed to site '
            'packages (True). Defaults to False.', action="store_true", dest='kivy_lib')
        parser.add_argument(
            "--glew-ver", help='The version number of glew to compile and install.'
            'Could be one of the released versions, e.g. 1.12.0 from '
            'http://sourceforge.net/projects/glew/files/glew/. Defaults to'
            ' 1.12.0.', default='1.12.0', dest='glew_ver')
        parser.add_argument(
            "--gst-ver", help='The version number of gstreamer to install.'
            'Could be one of the released versions, e.g. 2013.6 from '
            'http://www.freedesktop.org/software/gstreamer-sdk/data/packages/windows/. '
            'Defaults to 2013.6.', default='2013.6', dest='gst_ver')
        parser.add_argument(
            "--no-gst", help='If Gstreamer should not be downloaded. '
            'If specified, GST_REGISTRY, GST_PLUGIN_PATH, and PKG_CONFIG_PATH '
            'should be set and gstreamer/bin should be in the PATH, otherwise, '
            'kivy will fail to use gstreamer if compiled by the script.',
            action="store_true", dest='no_gst')
        parser.add_argument(
            "--no-sdl2", help='If SDL2 should not be downloaded. '
            'If specified, KIVY_SDL2_PATH should be set to the SDL2 bin, include, '
            'and lib diretories and SDL2 bin should be in the PATH, otherwise, '
            'SDL2 will not be used by kivy if compiled by the script.',
            action="store_true", dest='no_sdl2')
        parser.add_argument(
            "--no-generic", help='Whether the kivy directory, the python directory and all '
            'kivy scripts referring to that directory will use just kivy, and Python '
            '(the default) or if it will name it with the python version '
            '(e.g. kivy27, Python27, kivy-2.7.bat etc.)',
            action="store_false", dest='generic')
        parser.add_argument(
            "--build-path", help='The directory name in --dir into which '
            'the python currently being build will be saved. Defaults to '
            '`py{pyver}_x{bitnes}`. The only available keywords are '
            'pyver for the python version, e.g. 27 and bitnes for the OS '
            'arch, e.g. 86 or 64',
            default='py{pyver}_x{bitnes}', dest='build_path')
        parser.add_argument(
            "--no-msysgit", help='If msysgit should not be included.',
            action="store_true", dest='no_msysgit')
        parser.add_argument(
            "--no-kivy", help='If kivy should not be downloaded and/or compiled.',
            action="store_true", dest='no_kivy')
        parser.add_argument(
            "--no-msysgit-strip", help='Whether msysgit should not be stripped of all the '
            'identical git.exe alias files. See the script that creates the symlinks '
            'instead of the removed files. Default is False',
            action="store_true", dest='no_msysgit_strip')
        parser.add_argument(
            "--mingw-strip", help='Whether we should strip mingw from '
            'seemingly unneeded files. Default is False',
            action="store_true", dest='mingw_strip')
        parser.add_argument(
            "--no-gst-strip", help='Whether we should strip gstreamer from '
            'seemingly unneeded files. Default is False',
            action="store_true", dest='no_gst_strip')

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
        self.kivy_lib = args.kivy_lib
        self.glew_zip = ('http://iweb.dl.sourceforge.net/project/glew/glew/{}/glew-{}.zip'.
                         format(args.glew_ver, args.glew_ver))
        self.gst_ver = args.gst_ver
        self.no_gst = args.no_gst
        self.no_sdl2 = args.no_sdl2
        self.generic = args.generic
        self.arg_build_path = args.build_path
        self.no_msysgit = args.no_msysgit
        self.no_kivy = args.no_kivy
        self.no_msysgit_strip = args.no_msysgit_strip
        self.mingw_strip = args.mingw_strip
        self.no_gst_strip = args.no_gst_strip

        if not exists(self.zip7):
            raise Exception('Valid 7-Zip installtion was not found at {}'.format(self.zip7))

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
                    ['https://www.python.org/ftp/python', pyver[:5], fname])
            else:
                link = py[1]
                if len(py) > 2:
                    md5 = py[2]

            if arch == '64':
                try:
                    proc = Popen(['git'], stdout=PIPE, stderr=PIPE)
                    proc.communicate()
                except WindowsError:
                    raise Exception(
                        'Git not found, required for a 64 bit installation')

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
            pyver_minor = pyver.replace('.', '')[:2]
            name = self.arg_build_path.format(
                **{'pyver': pyver_minor, 'bitnes': arch})
            build_path = join(dist_dir, name)
            patch_py = False
            if link.endswith('.exe'):  # already existing python
                pydir = dirname(link)
            else:
                if self.generic:
                    pydir = join(build_path, 'Python')
                else:
                    pydir = join(build_path, 'Python{}'.format(pyver_minor))

            if self.clean and exists(build_path):
                print("*Cleaning old build dir, {}".format(build_path))
                rmtree(build_path, ignore_errors=True)
            if not exists(build_path):
                print("*Creating build directory: {}".format(build_path))
                makedirs(build_path)
            self.get_python(width, pydir, link, md5)
            self.get_msvcr(build_path, pydir, arch, pyver, os.environ)
            print('Done installing Python\n')
            patch_py = arch == '64'

            mingw = join(build_path, 'MinGW')
            if not self.no_mingw:
                print("-" * width)
                print("Preparing MinGW")
                print("-" * width)
                mingw = self.do_mingw(mingw, arch, os.environ)
                self.do_strip_mingw(mingw)
                if not self.no_msysgit:
                    self.do_msysgit(mingw, os.environ)
                print('Done installing MinGW\n')

            env = os.environ.copy()
            env['PATH'] = ';'.join(
                [join(build_path, 'SDL2', 'bin'), pydir, join(mingw, 'bin'),
                join(pydir, 'Scripts'), join(build_path, 'gstreamer', 'bin'),
                env['PATH']])
            env['PYTHONPATH'] = ''
            env['USE_SDL2'] = '1'
            env['GST_REGISTRY'] = join(build_path, 'gstreamer', 'registry.bin')
            env['GST_PLUGIN_PATH'] = join(build_path, 'gstreamer', 'lib', 'gstreamer-1.0')
            env['PKG_CONFIG_PATH'] = join(build_path, 'gstreamer', 'lib', 'pkgconfig')

            if patch_py:
                print("-" * width)
                print("Patching python")
                print("-" * width)
                self.patch_python_x64(pydir, env, pyver)
                print('Done patching python\n')
            self.patch_cygwinccompiler(pydir)
            exec_binary('GCC version', ['gcc -v'], env, shell=True)

            print("-" * width)
            print("Preparing Glew")
            print("-" * width)
            self.get_glew(pydir, mingw, arch, env)
            print('Done preparing Glew\n')

            if not self.no_sdl2:
                print("-" * width)
                print("Preparing SDL2")
                print("-" * width)
                self.get_sdl2(build_path, arch, env)
                print('Done preparing SDL2\n')
            else:
                lib = join(build_path, 'SDL2', 'lib')
                bin = join(build_path, 'SDL2', 'bin')
                include = join(build_path, 'SDL2', 'include')
                env['KIVY_SDL2_PATH'] = (
                    ';'.join([lib, bin, join(include, 'SDL2')]) + ';' +
                    env.get('KIVY_SDL2_PATH', ''))
            if not self.no_gst:
                print("-" * width)
                print("Preparing GStreamer")
                print("-" * width)
                self.get_gstreamer(build_path, arch, env)
                sdl = join(build_path, 'SDL2', 'bin')
                gst = join(build_path, 'gstreamer', 'bin')
                if exists(sdl):
                    print('Removing gst dlls existing in SDL2')
                    for fname in set(listdir(sdl)) & set(listdir(gst)):
                        names = (join(gst, fname), join(gst, fname + '.old'))
                        try:
                            rename(*names)
                            print('Changed {} to {}'.format(*names))
                        except:
                            pass
                print('Done preparing GStreamer\n')

            print("-" * width)
            print("Preparing pip deps")
            print("-" * width)
            self.get_pip_deps(build_path, pydir, pyver, env, pywin_url)
            print('Done preparing pip deps\n')
            self.do_strip_python(width, pydir)

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
        print('Updating {}'.format(f))
        config = ConfigParser()
        config.read(f)
        if not config.has_section('build'):
            config.add_section('build')
        config.set('build', 'compiler', 'mingw32')
        with open(f, 'w') as fh:
            config.write(fh)

        if not exists(join(pydir, 'Scripts')):
            makedirs(join(pydir, 'Scripts'))

    def do_strip_python(self, width, pydir):
        if not self.strip_py:
            return
        print("\nStripping python")
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
                    try:
                        remove(f)
                    except:
                        pass

    def patch_python_x64(self, pydir, env, pyver):
        libs = join(pydir, 'libs')
        py = 'python{}'.format(pyver.replace('.', '')[:2])
        pylib = py + '.lib'
        pydll = join(pydir, py + '.dll')
        pydef = join(libs, py + '.def')

        # see http://bugs.python.org/issue4709 and
        # http://ascend4.org/Setting_up_a_MinGW-w64_build_environment
        if exists(join(libs, pylib)):
            try: remove(join(libs, 'old_' + pylib))
            except: pass
            try: rename(join(libs, pylib), join(libs, 'old_' + pylib))
            except: pass
        exec_binary('Gendefing ' + pydll, ['gendef.exe', pydll], env, libs)
        exec_binary('Generating lib' + py + '.a',
                    ['dlltool', '--dllname', pydll, '--def', pydef,
                     '--output-lib', 'lib' + py + '.a'], env, libs, shell=True)
        remove(pydef)

        # http://bugs.python.org/issue4709
        config = join(pydir, 'include', 'pyconfig.h')
        print('Patching {}'.format(config))
        with open(config, 'rb') as fh:
            lines = fh.readlines()

        match_line = b'/* Compiler specific defines */'
        with open(config, 'wb') as fh:
            for line in lines:
                if line.startswith(match_line):
                    cr = line[len(match_line):]
                    fh.write(
                        cr.join([b'', b'#ifdef _WIN64', b'#define MS_WIN64',
                                 b'#endif', b'', b'']))
                fh.write(line)

    def patch_cygwinccompiler(self, pydir):
        # see http://bugs.python.org/issue16472
        print('Patching cygwinccompiler.py')
        cyg = join(pydir, 'Lib', 'distutils', 'cygwinccompiler.py')
        with open(cyg, 'rb') as fd:
            lines = fd.readlines()

        with open(cyg, 'wb') as fd:
            for line in lines:
                if line.startswith(b'        self.dll_libraries = get_msvcr()'):
                    fd.write(b'        # self.dll_libraries = get_msvcr()\n')
                else:
                    fd.write(line)

    def do_mingw(self, mingw, arch, env):
        url = self.mingw64 if arch == '64' else self.mingw
        rmtree(mingw, ignore_errors=True)
        try:
            remove(mingw)
        except:
            pass
        if isdir(url):
            copytree(url, mingw)
            if not exists(join(mingw, 'bin', 'make.exe')):
                try:
                    copy2(join(mingw, 'bin', 'mingw32-make.exe'),
                          join(mingw, 'bin', 'make.exe'))
                except:
                    pass
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

        mingw_extracted = join(self.temp_dir, 'mingw' + ('64' if arch == '64' else '32'))
        rmtree(mingw_extracted, ignore_errors=True)
        rmtree(mingw, ignore_errors=True)
        exec_binary(
            'Extracting mingw', [self.zip7, 'x', '-y', f], env,
            self.temp_dir, shell=True, exclude=zip_q)

        for i in range(10):
            try:
                rename(mingw_extracted, mingw)
                break
            except WindowsError:
                if i == 9:
                    copy_files(mingw_extracted, mingw)
                else:
                    sleep(2.5)
        if not exists(join(mingw, 'bin', 'make.exe')):
            try:
                copy2(join(mingw, 'bin', 'mingw32-make.exe'),
                      join(mingw, 'bin', 'make.exe'))
            except:
                pass
        return mingw

    def do_strip_mingw(self, mingw):
        if not self.mingw_strip:
            return

    def do_msysgit(self, mingw, env):
        temp_dir = self.temp_dir
        url = (
            'https://github.com/msysgit/msysgit/releases/download/'
            'Git-1.9.5-preview20150319/PortableGit-1.9.5-preview20150319.7z')

        local_url = join(temp_dir, url.split('/')[-1])
        if not exists(local_url):
            print("*Downloading: {}".format(url))
            print("Progress: 000.00%", end=' ')
            local_url, _ = urlretrieve(url, local_url, reporthook=report_hook)
            print(" [Done]")

        exec_binary(
            'Extracting msysgit',
            [self.zip7, 'x', '-y', '-o{}'.format(join(mingw, 'msysgit')), local_url],
            env, temp_dir, shell=True, exclude=zip_q)

        if self.no_msysgit_strip:
            return
        core = join(mingw, 'msysgit', 'libexec', 'git-core')
        git = join(core, 'git.exe')
        files = get_file_duplicates(git)
        with open(join(core, MSYSGIT_STIPPED_FILES), 'wb') as fh:
            fh.write('\n'.join(files))
        print('Writing {} containing git duplicates'.format(join(core, MSYSGIT_STIPPED_FILES)))
        for f in files:
            print('Removing {}'.format(join(core, f)))
            remove(join(core, f))

    def get_pip_deps(self, build_path, pydir, pyver, env, pywin):
        width = self.width
        temp_dir = self.temp_dir
        py = join(pydir, 'python.exe')
        print('\n')

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
        for mod in self.pip_deps + (
            [self.kivy_zip] if self.kivy_lib and not self.no_kivy else []):
            exec_binary('\nInstalling {}'.format(mod), [pip, 'install', mod],
                        env, pydir, shell=True)

        wheel = join(pydir, 'Scripts', 'wheel.exe')
        for f in list(listdir(temp_dir)):
            if f.endswith('.whl'):
                remove(join(temp_dir, f))

        pywin_out = join(temp_dir, pywin.split('/')[-1])
        if not exists(pywin_out):
            print("\nDownloading pywin32. Progress: 000.00%", end=' ')
            pywin, _ = urlretrieve(pywin, pywin_out, reporthook=report_hook)
            print(' [Done]')

        exec_binary('Converting {} to wheel'.format(pywin_out),
                    [wheel, 'convert', pywin_out], env, temp_dir, shell=True)
        wheels = [join(temp_dir, f) for f in listdir(temp_dir)
                  if f.startswith('pywin32') and f.endswith('.whl')]
        if len(wheels) != 1:
            raise Exception('Expected one pywin wheel, found {}'.format(wheels))

        exec_binary('Installing the wheel {}'.format(wheels[0]),
                    [wheel, 'install', '--force', wheels[0]], env, pydir, shell=True)
        copy_files(join(pydir, 'Lib', 'site-packages', 'pywin32_system32'), pydir)

        if not self.kivy_lib and not self.no_kivy:
            print('\nGetting kivy')
            url = self.kivy_zip
            kivy = join(temp_dir, 'kivy.zip')
            try:
                remove(kivy)
            except:
                pass
            rmtree(join(temp_dir, 'kivy'), ignore_errors=True)
            rmtree(join(build_path, 'kivy'), ignore_errors=True)

            kivy, _ = urlretrieve(url, kivy)
            print('Extracting kivy {}'.format(kivy))
            with open(kivy, 'rb') as fd:
                ZipFile(fd).extractall(join(temp_dir, 'kivy'))

            kivy_path = join(build_path, 'kivy{}'.format(
                '' if self.generic else pyver.replace('.', '')[:2]))
            copytree(
                join(temp_dir, 'kivy', list(listdir(join(temp_dir, 'kivy')))[0]),
                kivy_path)
            exec_binary('Compiling kivy', [py, 'setup.py', 'build_ext', '--inplace'],
                        env, kivy_path, shell=True)

        print('Copying tools')
        if self.generic:
            copy_files(join(dirname(__file__), 'data'), build_path)
            return

        data = join(temp_dir, 'kivy_data')
        rmtree(data, ignore_errors=True)
        copy_files(join(dirname(__file__), 'data'), data)

        pyvdot = pyver[:3]
        pyv = pyver.replace('.', '')[:2]
        for fname in ('kivy.bat', 'kivyenv.sh', 'kivywineenv.sh'):
            with open(join(data, fname)) as fh:
                lines = fh.readlines()
            with open(join(data, fname), 'w') as fh:
                for line in lines:
                    if 'PY_VER=' in line:
                        line = line.replace('PY_VER=', 'PY_VER={}'.format(pyv))
                    fh.write(line)
            name, ext = splitext(fname)
            rename(join(data, fname), join(data, name + '-' + pyvdot + ext))

        with open(join(data, 'kivybash.rc')) as fh:
            lines = fh.readlines()
        with open(join(data, 'kivybash.rc'), 'w') as fh:
            for line in lines:
                if 'kivyenv.sh' in line:
                    line = line.replace('kivyenv.sh', 'kivyenv-{}.sh'.format(pyvdot))
                fh.write(line)
        rename(join(data, 'kivybash.rc'), join(data, 'kivybash-{}.rc'.format(pyvdot)))

        with open(join(data, 'kivy-bash.bat')) as fh:
            lines = fh.readlines()
        with open(join(data, 'kivy-bash.bat'), 'w') as fh:
            for line in lines:
                if 'kivybash.rc' in line:
                    line = line.replace('kivybash.rc', 'kivybash-{}.rc'.format(pyvdot))
                fh.write(line)
        rename(join(data, 'kivy-bash.bat'), join(data, 'kivy-bash-{}.bat'.format(pyvdot)))
        copy_files(data, build_path)

    def get_glew(self, pydir, mingw, arch, env):
        glew_exists = exists(join(mingw, 'bin', 'glew32.dll'))
        temp_dir = self.temp_dir
        url = self.glew_zip
        local_url = join(temp_dir, url.split('/')[-1])
        rmtree(join(temp_dir, 'glew'), ignore_errors=True)

        if not exists(local_url):
            print("Progress: 000.00%", end=' ')
            local_url, _ = urlretrieve(url, local_url, reporthook=report_hook)
            print(" [Done]")
        print('Extracting glew {}'.format(local_url))
        with open(local_url, 'rb') as fd:
            ZipFile(fd).extractall(join(temp_dir, 'glew'))

        z = base_dir = join(temp_dir, 'glew', list(listdir(join(temp_dir, 'glew')))[0])
        if not glew_exists:
            exec_binary('GCC', ['gcc', '-v'], env, base_dir, shell=True)
            exec_binary(
                'Compiling Glew',
                ['gcc', '-DGLEW_NO_GLU', '-O2', '-Wall', '-W', '-Iinclude', '-DGLEW_BUILD',
                 '-o', 'src/glew.o', '-c', 'src/glew.c'], env, base_dir, shell=True)
            exec_binary(
                '',
                ['gcc', '-shared', '-Wl,-soname,libglew32.dll',
                 '-Wl,--out-implib,lib/libglew32.dll.a', '-o', 'lib/glew32.dll',
                 'src/glew.o', '-lglu32', '-lopengl32', '-lgdi32',
                 '-luser32', '-lkernel32'], env, base_dir, shell=True)
            exec_binary(
                '', ['ar', 'cr', 'lib/libglew32.a', 'src/glew.o'], env, base_dir, shell=True)

        print('Distributing glew to mingw and python')
        include = join(mingw, 'include', 'GL')
        py_include = join(pydir, 'include', 'GL')
        if not exists(include):
            makedirs(include)
        if not exists(py_include):
            makedirs(py_include)

        files = glob(join(z, 'include', 'GL', '*'))
        files = (
            zip(files, [py_include] * len(files)) +
            ((zip(files, [include] * len(files)) +
            [(join(z, 'lib', 'glew32.dll'), join(mingw, 'bin')),
             (join(z, 'lib', 'libglew32.a'), join(mingw, 'lib')),
             (join(z, 'lib', 'libglew32.dll.a'), join(mingw, 'lib')),
             (join(z, 'lib', 'libglew32.dll.a'), join(pydir, 'libs'))])
             if not glew_exists else []))
        for src_f, dst_f in files:
            copy2(src_f, dst_f)

    def get_sdl2(self, build_path, arch, env):
        sdl2_ver = '2.0.3'
        sdl2_mixer_ver = '2.0.0'
        sdl2_ttf_ver = '2.0.12'
        sdl2_image_ver = '2.0.0'

        temp_dir = self.temp_dir
        lib = join(build_path, 'SDL2', 'lib')
        bin = join(build_path, 'SDL2', 'bin')
        include = join(build_path, 'SDL2', 'include')
        env['KIVY_SDL2_PATH'] = ';'.join([lib, bin, join(include, 'SDL2')])
        for d in (lib, bin, include):
            if not exists(d):
                makedirs(d)

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
            local_url = join(temp_dir, url.split('/')[-1])

            print('\nGetting {}'.format(url))
            if not exists(local_url):
                print("Progress: 000.00%", end=' ')
                local_url, _ = urlretrieve(url, local_url,
                                           reporthook=report_hook)
                print(" [Done]")

            exec_binary(
                'Extracting {}'.format(local_url),
                [self.zip7, 'x', '-y', local_url], env, self.temp_dir, shell=True,
                exclude=zip_q)
            exec_binary(
                'Extracting {}'.format(local_url[:-3]),
                [self.zip7, 'x', '-y', local_url[:-3]], env, self.temp_dir,
                shell=True, exclude=zip_q)

            base_dir = local_url.replace('-mingw.tar.gz', '').replace('-devel', '')
            if arch == '64':
                base_dir = join(base_dir, 'x86_64-w64-mingw32')
            else:
                base_dir = join(base_dir, 'i686-w64-mingw32')
            copy_files(join(base_dir, 'lib'), lib)
            copy_files(join(base_dir, 'bin'), bin)
            copy_files(join(base_dir, 'include'), include)

        print('\nGetting patched SDL_platform.h')
        local_url = join(temp_dir, 'SDL_platform.h')
        if not exists(local_url):
            local_url, _ = urlretrieve(
            'https://hg.libsdl.org/SDL/raw-file/e217ed463f25/include/SDL_platform.h',
            local_url)
        copy2(local_url, join(include, 'SDL2'))

    def get_gstreamer(self, build_path, arch, env):
        temp_dir = self.temp_dir
        bitness = 'x86_64' if arch == '64' else 'x86'
        runtime_name = 'gstreamer-1.0-{}-1.4.5.msi'.format(bitness, self.gst_ver)
        devel_name = 'gstreamer-1.0-devel-{}-1.4.5.msi'.format(bitness, self.gst_ver)

        gst = join(temp_dir, 'gstreamer')
        print('Removing gstreamer directory {}'.format(gst))
        rmtree(gst, ignore_errors=True)
        if not exists(gst):
            makedirs(gst)

        for name in (runtime_name, devel_name):
            local_url = join(temp_dir, name)
            url = (
                'http://gstreamer.freedesktop.org/data/pkg/windows/1.4.5/{}'.format(name))
            if not exists(local_url):
                print("Getting {}\nProgress: 000.00%".format(url), end=' ')
                local_url, _ = urlretrieve(url, local_url, reporthook=report_hook)
                print(" [Done]")

            exec_binary(
                "Extracting {} to {}".format(local_url, gst),
                ['msiexec', '/a', local_url, '/qb', 'TARGETDIR={}'.format(gst)],
                cwd=gst, shell=False)
        gst = join(gst, 'gstreamer')
        gst = join(gst, list(listdir(gst))[0], bitness)

        print('Removing {}'.format(join(build_path, 'gstreamer')))
        rmtree(join(build_path, 'gstreamer'), ignore_errors=True)
        print('Moving {} to {}'.format(gst, join(build_path, 'gstreamer')))

        for i in range(10):
            try:
                rename(gst, join(build_path, 'gstreamer'))
                break
            except WindowsError:
                if i == 9:
                    copy_files(gst, join(build_path, 'gstreamer'))
                else:
                    sleep(2.5)

        bittness = '64' if arch == '64' else '32'
        pkg_url = 'pkg-config_0.28-1_win{}.zip'.format(bittness)
        url = 'http://win32builder.gnome.org/packages/3.6/{}'.format(pkg_url)

        local_url = join(temp_dir, pkg_url)
        if not exists(local_url):
            print("Getting {}\nProgress: 000.00%".format(url), end=' ')
            local_url, _ = urlretrieve(url, local_url, reporthook=report_hook)
            print(" [Done]")

        base_dir = join(temp_dir, splitext(pkg_url)[0])
        rmtree(base_dir, ignore_errors=True)
        makedirs(base_dir)
        with open(local_url, 'rb') as fd:
            ZipFile(fd).extractall(base_dir)
        copy_files(join(base_dir, 'bin'), join(build_path, 'gstreamer', 'bin'))

        if self.no_gst_strip:
            return

        inc = join(build_path, 'gstreamer', 'include')
        for f in listdir(inc):
            if f in ('glib-2.0', 'gstreamer-1.0'):
                continue
            f = join(inc, f)
            if isdir(f):
                rmtree(f)
            else:
                remove(f)

        gstreamer = join(inc, 'gstreamer-1.0')
        for f in listdir(gstreamer):
            if f == 'gst':
                continue
            f = join(gstreamer, f)
            if isdir(f):
                rmtree(f)
            else:
                remove(f)
        gst = join(gstreamer, 'gst')
        for f in listdir(gst):
            f = join(gst, f)
            if isdir(f):
                rmtree(f)

        lib_files = [
            ['gio'],
            ['glib-2.0'],
            ['gstreamer-1.0'],
            ['glib-2.0.lib'],
            ['gmodule-2.0.lib'],
            ['gobject-2.0.lib'],
            ['gstreamer-1.0.lib'],
            ['intl.lib'],
            ['libglib-2.0.dll.a'],
            ['libglib-2.0.la'],
            ['libgmodule-2.0.dll.a'],
            ['libgmodule-2.0.la'],
            ['libgobject-2.0.dll.a'],
            ['libgobject-2.0.la'],
            ['libgstreamer-1.0.a'],
            ['libgstreamer-1.0.dll.a'],
            ['libgstreamer-1.0.la'],
            ['pkgconfig', 'glib-2.0.pc'],
            ['pkgconfig', 'gmodule-2.0.pc'],
            ['pkgconfig', 'gmodule-no-export-2.0.pc'],
            ['pkgconfig', 'gobject-2.0.pc'],
            ['pkgconfig', 'gstreamer-1.0.pc'],
            ]
        remove_from_dir(join(build_path, 'gstreamer', 'lib'), lib_files)

    def get_msvcr(self, build_path, pydir, arch, pyver, env):
        temp_dir = self.temp_dir
        msvcr = join(temp_dir, 'msvcr')
        rmtree(msvcr, ignore_errors=True)

        temp_dir = self.temp_dir
        py2 = pyver.startswith('2')
        if arch == '64' and py2:
            url = ('http://download.microsoft.com/download/d/2/4/'
                   'd242c3fb-da5a-4542-ad66-f9661d0a8d19/vcredist_x64.exe')
        elif py2:
            url = ('http://download.microsoft.com/download/1/1/1/'
                   '1116b75a-9ec3-481a-a3c8-1777b5381140/vcredist_x86.exe')
        elif arch == '64':
            url = ('http://download.microsoft.com/download/3/2/2/'
                   '3224B87F-CFA0-4E70-BDA3-3DE650EFEBA5/vcredist_x64.exe')
        else:
            url = ('http://download.microsoft.com/download/5/B/C/'
                   '5BC5DBB3-652D-4DCE-B14A-475AB85EEF6E/vcredist_x86.exe')
        local_url = join(temp_dir, url.split('/')[-1])

        try:
            remove(local_url)
        except:
            pass
        print("Progress: 000.00%", end=' ')
        local_url, _ = urlretrieve(url, local_url, reporthook=report_hook)
        print(" [Done]")

        exec_binary(
            'Extracting vcredist',
            [self.zip7, 'x', '-y', '-o{}'.format(msvcr), local_url], env,
            self.temp_dir, shell=True, exclude=zip_q)

        # for VS2010 we need to create pretend files, otherwise the isnatller
        # chokes looking for them since they do not actually exist
        if pyver.startswith('3'):
            for fname in (
                'eula.1028.txt', 'eula.1031.txt', 'eula.1032.txt', 'eula.1033.txt',
                'eula.1036.txt', 'eula.1040.txt', 'eula.1041.txt', 'eula.1042.txt',
                'eula.1049.txt', 'eula.2052.txt', 'eula.3082.txt', 'globdata.ini',
                'install.exe', 'install.ini', 'install.res.1028.dll', 'install.res.1031.dll',
                'install.res.1033.dll', 'install.res.1036.dll', 'install.res.1040.dll',
                'install.res.1041.dll', 'install.res.1042.dll', 'install.res.1049.dll',
                'install.res.2052.dll', 'install.res.3082.dll', 'vcredist.bmp'):
                if not exists(join(msvcr, fname)):
                    with open(join(msvcr, fname), 'wb'):
                        pass

        exec_binary(
            '', ['msiexec', '/a', join(msvcr, 'vc_red.msi'), '/qb', 'TARGETDIR={}'.
                 format(join(msvcr, 'msvcr_msi'))], shell=False)
        if pyver.startswith('2'):
            if arch == '64':
                msvcr = join(msvcr, 'msvcr_msi', 'Windows', 'winsxs', 'dlCRTx64')
            else:
                msvcr = join(msvcr, 'msvcr_msi', 'Windows', 'winsxs', 'dlCRTx86')
            files = ['msvcr90.dll', 'msvcp90.dll']
        else:
            if arch == '64':
                msvcr = join(msvcr, 'msvcr_msi', 'Win', 'System64')
            else:
                msvcr = join(msvcr, 'msvcr_msi', 'Win', 'System')
            files = ['msvcr100.dll', 'msvcp100.dll']
        for fname in files:
            if not exists(join(pydir, fname)):
                copy2(join(msvcr, fname), pydir)


if __name__ == '__main__':
    WindowsPortablePythonBuild().run()
