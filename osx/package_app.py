#!/usr/bin/python
# -*- coding: utf-8 -*-
'''package_app

Usage:
    package-app <path_to_app> [--icon=<icon_path> --author=<copyright>\
 --appname=<appname> --source-app=<source_app> --deps=<dep_list>\
 --gardendeps=<sep_list> --bundleid=<bundle_id> --displayname=<displayname>\
 --bundlename=<bundle_name> --bundleversion=<bundleversion>\
 --strip=<true_false> --with-gstreamer=<yes_no> --whitelist=<path/to/whitelist>\
 --blacklist=<path/to/blacklist>]
    package-app -h | --help
    package-app --version

Options:
    -h  --help                      Show this screen.
    --icon=<icon_path>              Path to source icon
    --author=<copyright>            Copyright attribution
                                    [default: © 2015 Kivy team].
    --appname=<app_name>            Name of the resulting .app file.
    --source-app=<source_app>       Path to the Kivy.app to use as base
                                    [default: Kivy.app].
    --entrypoint=<entrypoint>       Entry point module to your application
                                    [default: main].
    --displayname=<displayname>     Bundle display name of the application.
                                    [default: Kivy].
    --bundleid=<bundleid>           Bundle identifier eg:org.kivy.launcher
                                    [default: org.kivy.launcher].
    --bundlename=<bundle_name>      Bundle name eg: `showcase`
                                    [default: kivy]
    --bundleversion=<version>       Bundle Version eg: 1.2.0
                                    [default: 0.0.1]
    --strip=<True_False>            Greatly reduce app size, by removing a
                                    lot of unneeded files. [default: True].
    --deps=<deplist>                Dependencies list.
    --gardendeps=<deplist>          Garden Dependencies list.
    --with-gstreamer=<yes|no>       Include GStreamer framework. [default: yes]
    --whitelist=<path/to/whitelist> file to use as include list when copying app
    --blacklist=<path/to/blacklist> file to use as exclude list when copying app
'''

__version__ = '0.1'
__author__ = 'the kivy team'

from docopt import docopt
try:
    import sh
except ImportError:
    print('Please install sh `pip install sh --user`')
from os.path import exists, abspath, dirname, join
from subprocess import check_call
from os import walk, unlink
from compileall import compile_dir
from os.path import exists
from subprocess import check_call

try:
    input = raw_input
except NameError:
    pass


def error(message):
    print(message)
    exit(-1)


def bootstrap(source_app, appname):
    # remove mypackage.app if it already exists
    print('Copy Kivy.app/source.app if it exists')
    if exists(appname):
        print('{} already exists removing it...'.format(appname))
        sh.rm('-rf', appname)

    # check if Kivy.app exists and copy it
    if not exists(source_app):
        error("source app {} doesn't exist")
    print('copying {} to {}'.format(source_app, appname))
    sh.cp('-a', source_app, appname)


def insert_app(path_to_app, appname, blacklist=None, whitelist=None):
    # insert appname into our source_app
    params = ['-r', path_to_app + '/', appname + '/Contents/Resources/myapp']
    if whitelist:
        params.append('--include-from={}'.format(whitelist))
    if blacklist:
        params.append('--exclude-from={}'.format(blacklist))
    sh.rsync(*params)

def cleanup(appname, strip, gstreamer=True):
    if not strip:
        return
    print("stripping app")
    from subprocess import call
    call(["sh", "-x", "cleanup_app.sh" , "./"+appname])
    if gstreamer == 'no':
        sh.rm('-rf', '{}/Contents/Frameworks/GStreamer.framework'.format(appname))

    print("Stripping complete")

def fill_meta(appname, arguments):
    print('Editing info.plist')
    bundleversion = arguments.get('--bundleversion')
    import plistlib
    info_plist = appname+'/Contents/info.plist'
    rootObject = plistlib.readPlist(info_plist)
    rootObject['NSHumanReadableCopyright'] = arguments.get('--author').decode('utf-8')
    rootObject['Bundle display name'] = arguments.get('--displayname')
    rootObject['Bundle identifier'] = arguments.get('--bundleid')
    rootObject['Bundle name'] = arguments.get('--bundlename')
    rootObject['Bundle version'] = arguments.get('--bundleversion')
    plistlib.writePlist(rootObject, info_plist)

def setup_icon(path_to_app, path_to_icon):
    # check icon file
    from subprocess import check_output
    if path_to_icon.startswith('http'):
        print('Downloading ' + path_to_icon)
        check_output(['curl', '-O', '-L', path_to_icon])
        path_to_icon = path_to_icon.split('/')[-1]
    if not exists(path_to_icon):
        return
    height = check_output(['sips', '-g', 'pixelHeight', path_to_icon])[-5:]
    width = check_output(['sips', '-g', 'pixelHeight', path_to_icon])[-5:]
    if height != width:
        print('The height and width of the image must be same')
        import sys
        sys.exit()

    # icon file is Finder
    sh.command('sips', '-s', 'format', 'icns', path_to_icon, '--out',
        path_to_app + "/Contents/Resources/appIcon.icns")
    print('Icon set to {}'.format(path_to_icon))

def compile_app(appname):
    #check python Versions
    print('Compiling app...')
    py3 = appname + '/Contents/Frameworks/python/3.5.0/bin/python'
    pypath = appname + '/Contents/Resources'
    if exists(py3):
        print('python3 detected...')
        check_call(
            [pypath + '/script -OO -m compileall -b ' + pypath+'/myapp'],
            shell=True)
        print("Remove all __pycache__")
        check_call(
            ['/usr/bin/find -E {} -regex "(.*)\.py" -print0 |/usr/bin/grep -v __init__| /usr/bin/xargs -0 /bin/rm'.format(pypath+'/yourapp')],
             shell=True)
        check_call(
            ['/usr/bin/find -E {}/Contents/ -name "__pycache__" -print0 | /usr/bin/xargs -0 /bin/rm -rf'.format(appname)],
            shell=True)
    else:
        print('using system python...')
        check_call(
            [pypath + '/script -OO -m compileall ' + pypath+'/myapp'],
            shell=True)
        print("-- Remove all py/pyc/pyo")
        check_call(
            ['/usr/bin/find -E {} -regex "(.*)\.pyc" -print0 | /usr/bin/xargs -0 /bin/rm'.format(appname)],
            shell=True)
        check_call(
            ['/usr/bin/find -E {} -regex "(.*)\.pyo" -print0 | /usr/bin/xargs -0 /bin/rm'.format(appname)],
            shell=True)
        check_call(
            ['/usr/bin/find -E {} -regex "(.*)\.py" -print0 | /usr/bin/grep -v __init__ | /usr/bin/xargs -0 /bin/rm'.format(appname)],
            shell=True)
        print("-- Remove all .c")
        check_call(
            ['/usr/bin/find -E {} -regex "(.*)\.c" -print0 | /usr/bin/xargs -0 /bin/rm'.format(appname)],
            shell=True)
    sh.command('mv', pypath + '/myapp', pypath + '/yourapp')

def install_deps(appname, deps):
    print('managing dependencies {}'.format(deps))
    for dep in deps.split(','):
        print('Installing {} into {}'.format(dep, appname))
        check_call(
            (appname + '/Contents/Resources/script -m' +\
             ' pip install --upgrade --force-reinstall ' + dep),
            shell=True)


def install_garden_deps(appname, deps):
    print('managing garden dependencies {}'.format(deps))
    pypath = appname + '/Contents/Resources'
    check_call(
        ['curl','-O', '-L',
        'https://raw.githubusercontent.com/kivy-garden/garden/master/bin/garden'],
        cwd=pypath+'/venv/bin')
    check_call(pypath+'/python -m pip install --upgrade requests', shell=True)
    for dep in deps.split(','):
        print('Installing {} into {}'.format(dep, appname))
        check_call(
            ('../script '+\
             '../venv/bin/garden' +\
             ' install --upgrade --app ' + dep),
            shell=True, cwd=pypath+'/myapp')


def main(arguments):
    path_to_app = arguments.get('<path_to_app>')
    source_app = arguments.get('--source-app')
    appname = arguments.get('--appname')
    if not appname:
        appname = path_to_app.split('/')[-1] + '.app'
    else:
        appname = appname + '.app'
    icon = arguments.get('--icon')
    strip = arguments.get('--strip', True)
    gstreamer = arguments.get('--with-gstreamer', True)
    deps = arguments.get('--deps', [])
    gardendeps = arguments.get('--gardendeps', [])
    blacklist = arguments.get('--blacklist')
    whitelist = arguments.get('--whitelist')

    bootstrap(source_app, appname)
    insert_app(path_to_app, appname, blacklist=blacklist, whitelist=whitelist)
    if deps:
        install_deps(appname, deps)
    if gardendeps:
        install_garden_deps(appname, gardendeps)
    compile_app(appname)
    if icon:
        setup_icon(appname, icon)
    fill_meta(appname, arguments)
    cleanup(appname, strip, gstreamer=gstreamer)
    print("All done!")


if __name__ == '__main__':
    arguments = docopt(__doc__, version='package app {}'.format(__version__))
    print(arguments)
    main(arguments)
