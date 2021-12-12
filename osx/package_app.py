#!/usr/bin/python
# -*- coding: utf-8 -*-
'''package_app

Usage:
    package-app <path_to_app> [--icon=<icon_path> --author=<copyright>\
 --appname=<appname> --source-app=<source_app> --deps=<dep_list>\
 --bundleid=<bundle_id> --displayname=<displayname>\
 --bundlename=<bundle_name> --bundleversion=<bundleversion>\
 --strip=<true_false> --whitelist=<path/to/whitelist>\
 --blacklist=<path/to/blacklist>]
    package-app -h | --help
    package-app --version

Options:
    -h  --help                      Show this screen.
    --icon=<icon_path>              Path to source icon
    --author=<copyright>            Copyright attribution
                                    [default: © 2021 Kivy team].
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
    --whitelist=<path/to/whitelist> file to use as include list when copying app
    --blacklist=<path/to/blacklist> file to use as exclude list when copying app
'''

__version__ = '0.1'
__author__ = 'the kivy team'

from os.path import exists
import subprocess
import plistlib
from docopt import docopt
import sh


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
    params = ['-r', path_to_app + '/', appname + '/Contents/Resources/yourapp']
    if whitelist:
        params.append('--include-from={}'.format(whitelist))
    if blacklist:
        params.append('--exclude-from={}'.format(blacklist))
    sh.rsync(*params)


def relocate(appname):
    print("relocating app")
    subprocess.call(["sh", "-x", "relocate.sh" , f"./{appname}"])

def cleanup(appname, strip):
    if not strip:
        return
    print("stripping app")
    subprocess.call(["sh", "-x", "cleanup-app.sh" , f"./{appname}"])
    print("Stripping complete")


def fill_meta(appname, arguments):
    print('Editing info.plist')
    info_plist = appname+'/Contents/info.plist'
    with open(info_plist, 'rb') as f:
        rootObject = plistlib.load(f)
    rootObject['NSHumanReadableCopyright'] = arguments.get('--author')
    rootObject['Bundle display name'] = arguments.get('--displayname')
    rootObject['Bundle identifier'] = arguments.get('--bundleid')
    rootObject['Bundle name'] = arguments.get('--bundlename')
    rootObject['Bundle version'] = arguments.get('--bundleversion')
    with open(info_plist, 'wb') as f:
        plistlib.dump(rootObject, f)


def setup_icon(path_to_app, path_to_icon):
    # check icon file
    if path_to_icon.startswith('http'):
        print('Downloading ' + path_to_icon)
        subprocess.check_output(['curl', '-O', '-L', path_to_icon])
        path_to_icon = path_to_icon.split('/')[-1]
    if not exists(path_to_icon):
        return
    height = subprocess.check_output(['sips', '-g', 'pixelHeight', path_to_icon])[-5:]
    width = subprocess.check_output(['sips', '-g', 'pixelHeight', path_to_icon])[-5:]
    if height != width:
        print('The height and width of the image must be same')
        import sys
        sys.exit()

    # icon file is Finder
    sh.command('sips', '-z', '256', '256', path_to_icon, '--out', 'resicon.png')
    sh.command('sips', '-s', 'format', 'icns', 'resicon.png', '--out',
        path_to_app + "/Contents/Resources/appIcon.icns")
    print('Icon set to {}'.format(path_to_icon))


def install_deps(appname, deps):
    print('managing dependencies {}'.format(deps))
    for dep in deps.split(','):
        print('Installing {} into {}'.format(dep, appname))
        subprocess.check_call(
            (appname + '/Contents/Resources/script -m' +\
             ' pip install --upgrade --force-reinstall ' + dep),
            shell=True)


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
    deps = arguments.get('--deps', [])
    blacklist = arguments.get('--blacklist')
    whitelist = arguments.get('--whitelist')

    bootstrap(source_app, appname)
    insert_app(path_to_app, appname, blacklist=blacklist, whitelist=whitelist)
    if deps:
        install_deps(appname, deps)
    if icon:
        setup_icon(appname, icon)
    fill_meta(appname, arguments)
    relocate(appname)
    cleanup(appname, strip)
    print("All done!")


if __name__ == '__main__':
    arguments = docopt(__doc__, version='package app {}'.format(__version__))
    print(arguments)
    main(arguments)
