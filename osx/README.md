Kivy for OS X
=============

This repository contains the scripts for:

- creating a Kivy.app directory from scratch 

    - `./create-osx-bundle`: will create a Kivy.app using system python and stable branch of kivy.
    - `./create-osx-bundle python2 master`: will create a Kivy.app using system python and master branch of kivy.
    - `./create-osx-bundle python3`: will create a Kivy.app embedding python3 and stable branch of kivy.
    - `./create-osx-bundle python3 master`: will create a Kivy.app embedding python3 and master branch of kivy.
    
- packaging a Kivy application using the previously generated Kivy.app

    `./package_app.py --help` to get more info

- creating a package (.dmg) of an application (.app)

    `./create-osx-dmg.sh appname.app`

To **install custom packages** into your app just pass them as `--deps=dep1,dep2,dep3` to `package_app.py`
Deps are installed using pip so you can pass arguments like --deps=cython==0.23

To include binaries into the package just put them under app_name.app/Contents/Resources/venv/bin folder. 

This approach works starting from Kivy 1.9, with SDL2 and GStreamer in mind.
Anything else is untested.

Buildozer uses this repository for its OS X packaging process.
