Kivy packaging for OS X
=======================

This repository contains the scripts for packaging a Kivy based app into a installable dmg.

Kivy versions supported: ``2.0.0+``. For older Kivy versions, use the corresponding stable branch.

The packaged dmg contains a Python virtualenv, Kivy and its binary dependencies such as SDL2. Kivy 
provides an existing dmg containing the virtualenv and Kivy pre-installed that can be used
as a base into which your app can be installed and packaged again as a dmg. Below are the steps:

**Note:** A Kivy.app build on one OS X version will typically
not work on older OS X versions. For older OS X versions, you need to build Kivy.app
on the oldest machine you wish to support.

* Get the Kivy sdk repo with e.g.
  ``git clone https://github.com/kivy/kivy-sdk-packager.git`` and ``cd`` into
  ``kivy-sdk-packager/osx``.
* Make or download a app bundle:
  * To make a app bundle, simply run::

        ./create-osx-bundle.sh -n MyApp -k ...

    See in ``create-osx-bundle.sh`` for all the configuration options. This will create
    a ``MyApp.app`` directory, where ``MyApp`` is the app's name.
  * To use the existing Kivy app bundle:
    * Download the Kivy app from the Kivy download page, the GitHub releases, or the
      nightly release with e.g.::

          curl -O -L https://xxx/Kivy-2.0.0-python3.8.dmg
    * Mount it in the current directory and fix the name to your App's name::

          hdiutil attach Kivy-2.0.0-python3.8.dmg -mountroot .
          cp -R Kivy/Kivy.app MyApp.app

      This should create the ``MyApp.app`` directory.

      Notice the capitalized ``R``, don't use lowercase as it will copy symbolic links in a cycle.
    * Fix the app's metadata to your app's metadata::

          ./fix-bundle-metadata.sh MyApp.app -n MyApp ...
* Install your dependencies and your app:
  * Activate the included virtualenv so you can install your app and its dependencies::

        pushd MyApp.app/Contents/Resources/venv/bin
        source activate
        source kivy_activate
        popd

    On the default mac shell you **must** be in the bin directory containing ``activate`` to be
    able to ``activate`` the virtualenv. ``kivy_activate`` is only necessary if you'll run
    Kivy in the environment - it sets up the Kivy home, gstreamer and other Kivy environment
    variables.
  * Install any frameworks and relocate them:
    * Mount any frameworks e.g. ``MyFramework`` on your system and copy it over to the app::

          hdiutil attach MyFramework.dmg
          cp -a /Volumes/MyFramework/MyFramework.framework MyApp.app/Contents/Frameworks/

    * Relocate the framework so it can be used from a different path. E.g.::

          python -m pip install git+https://github.com/tito/osxrelocator
          osxrelocator -r MyApp.app MyApp.app/Contents/Frameworks/MyFramework/ @executable_path/Contents/Frameworks/MyFramework/
          osxrelocator -r MyApp.app @rpath/MyFramework.framework/Versions/A/MyFramework \
              @executable_path/Contents/Frameworks/MyFramework.framework/Versions/A/MyFramework

      This should be customized for each framework. See the ``create-osx-bundle.sh`` script for examples.
  * Install your dependencies with e.g. ``pip``::

        python -m pip install ...

  * Install your app::

        python -m pip install myapp

  * Deactivate the virtualenv by running ``deactivate`` in the shell.
* Reduce app size (optional):

  You can reduce the app size by removing unnecessary files. We provide a script to remove files commonly
  not needed and optionally gstreamer (see its options). Run it with::

      ./cleanup-app.sh MyApp.app

  And/or manually remove files and directories.
* Create a script that will run when the user clicks on the installed app.

  To do this, you'll copy a shell, python file, or other script into
  ``MyApp.app/Contents/Resources`` with the name ``yourapp``. The app will automatically run it
  using a launcher script that activates the venv, initializes the kivy environment similarly to
  ``kivy_activate`` and runs ``yourapp`` whenever the user runs the app.

  A common technique is in your ``setup.py`` add something like::

      entry_points={'console_scripts': ['myapp=myapp.main:run_app']}

  to your ``setup`` function. When you install your app package, pip will create a ``myapp``
  script that runs your app. Then, create a symlink to ``myapp``, and your app will run
  when the user clicks the applications. E.g.::

      pushd MyApp.app/Contents/Resources/
      ln -s ./venv/bin/myapp yourapp
      popd

  will create such a symlink. The link needs to be created relative to the ``yourapp`` path,
  so we go to that directory.
* Relocate the hard-coded links created by pip. This is required to be able to compile the app
  into a dmg install to a different path. Do::

      ./relocate.sh MyApp.app

* Finally, package the app into a dmg as follows::

      ./create-osx-dmg.sh MyApp.app MyApp

  This creates the MyApp.dmg in your current directory.
* TODO: figure out how to sign the dmg/app.
* Clean up and unmount and mounted DMGs if needed.


Example using Kivy.app
----------------------

A complete example using ``Kivy.app`` with a entry_point pointing to your app as described above
(notice the metadata and download URLs need to be replaced with actual metadata and URLs)::

    git clone https://github.com/user/myapp.git
    git clone https://github.com/kivy/kivy-sdk-packager.git
    cd kivy-sdk-packager/osx

    curl -O -L https://xxx/Kivy-xxx.dmg
    hdiutil attach Kivy-xxx.dmg -mountroot .

    # notice capital R, don't use lowercase as it will copy symbolic links in a cycle
    cp -R Kivy/Kivy.app MyApp.app
    ./fix-bundle-metadata.sh MyApp.app -n MyApp -v "0.1.1" -a "Name" -o \
        "org.myorg.myapp" -i "../../myapp/doc/source/images/myapp_icon.png"

    pushd MyApp.app/Contents/Resources/venv/bin
    source activate
    popd

    python -m pip install --upgrade pyobjus plyer ...
    python -m pip install ../../myapp/

    # remove gstreamer and reduce app size
    ./cleanup-app.sh MyApp.app -g 1

    # the link needs to be created relative to the yourapp path, so go to that directory
    pushd MyApp.app/Contents/Resources/
    ln -s ./venv/bin/myapp yourapp
    popd

    ./relocate.sh MyApp.app
    ./create-osx-dmg.sh MyApp.app MyApp


Example create app from scratch
-------------------------------

A complete example creating a bundle and building a dmg without using the prepared Kivy.app.
Also using a entry_point pointing to your app as described above
(notice the metadata and download URLs need to be replaced with actual metadata and URLs).
The dependencies versions and url should be updated as needed. Note that gstreamer is not
included::

    # configure kivy
    export CC=clang
    export CXX=clang
    export FFLAGS='-ff2c'
    export USE_SDL2=1
    export USE_GSTREAMER=0

    # get the dependencies
    export SDL2=2.0.12
    export SDL2_IMAGE=2.0.5
    export SDL2_MIXER=2.0.4
    export SDL2_TTF=2.0.15
    export PLATYPUS=5.3

    curl -O -L "https://www.libsdl.org/release/SDL2-$SDL2.dmg"
    curl -O -L "https://www.libsdl.org/projects/SDL_image/release/SDL2_image-$SDL2_IMAGE.dmg"
    curl -O -L "https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-$SDL2_MIXER.dmg"
    curl -O -L "https://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-$SDL2_TTF.dmg"
    curl -O -L "http://www.sveinbjorn.org/files/software/platypus/platypus$PLATYPUS.zip"

    hdiutil attach SDL2-$SDL2.dmg
    sudo cp -a /Volumes/SDL2/SDL2.framework /Library/Frameworks/
    hdiutil attach SDL2_image-$SDL2_IMAGE.dmg
    sudo cp -a /Volumes/SDL2_image/SDL2_image.framework /Library/Frameworks/
    hdiutil attach SDL2_ttf-$SDL2_TTF.dmg
    sudo cp -a /Volumes/SDL2_ttf/SDL2_ttf.framework /Library/Frameworks/
    hdiutil attach SDL2_mixer-$SDL2_MIXER.dmg
    sudo cp -a /Volumes/SDL2_mixer/SDL2_mixer.framework /Library/Frameworks/

    unzip platypus$PLATYPUS.zip
    gunzip Platypus.app/Contents/Resources/platypus_clt.gz
    gunzip Platypus.app/Contents/Resources/ScriptExec.gz
    mkdir -p /usr/local/bin
    mkdir -p /usr/local/share/platypus
    cp Platypus.app/Contents/Resources/platypus_clt /usr/local/bin/platypus
    cp Platypus.app/Contents/Resources/ScriptExec /usr/local/share/platypus/ScriptExec
    cp -a Platypus.app/Contents/Resources/MainMenu.nib /usr/local/share/platypus/MainMenu.nib
    chmod -R 755 /usr/local/share/platypus

    # create app
    git clone https://github.com/user/myapp.git
    git clone https://github.com/kivy/kivy-sdk-packager.git
    cd kivy-sdk-packager/osx

    ./create-osx-bundle.sh -k master -n MyApp -v "0.1.1" -a "Name" -o \
        "org.myorg.myapp" -i "../../myapp/doc/source/images/myapp_icon.png" -g 0

    pushd MyApp.app/Contents/Resources/venv/bin
    source activate
    popd

    python -m pip install --upgrade pyobjus plyer ...
    python -m pip install ../../myapp/

    # reduce app size
    ./cleanup-app.sh MyApp.app -g 1

    # the link needs to be created relative to the yourapp path, so go to that directory
    pushd MyApp.app/Contents/Resources/
    ln -s ./venv/bin/myapp yourapp
    popd

    ./relocate.sh MyApp.app
    ./create-osx-dmg.sh MyApp.app MyApp


Dev note:: Buildozer uses this repository for its OS X packaging process.
