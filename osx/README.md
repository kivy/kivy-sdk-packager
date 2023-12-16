Kivy packaging for macOS
========================

This repository contains the scripts for packaging a Kivy based app into a installable dmg.

**Important notice:** macOS 11 (or greater), with XCode 12.2 (or greater) is required to build a fully working universal2 ``.app`` due to https://bugs.python.org/issue42619

Kivy versions supported: ``2.2.0+``. For older Kivy versions, use the corresponding stable branch.

The packaged ``.app`` contains a Python virtualenv with ``kivy`` and its dependencies pre-installed.

SDL2 frameworks are included in the app bundle, and the Kivy installation is configured to use them.

Kivy, on every release, provides a ``Kivy.app`` that can be used as a base for your app, so you don't need to build it from scratch.
Below are the steps to use the ``Kivy.app`` as a base for your app, or to build your app from scratch.

* Get the Kivy sdk repo with e.g.
  ``git clone https://github.com/kivy/kivy-sdk-packager.git`` and ``cd`` into
  ``kivy-sdk-packager/osx``.
* Make or download a app bundle:
  * To make a app bundle, simply run::

        ./create-osx-bundle.sh -n MyApp -k ...

    For all the configuration options, you can run ``./create-osx-bundle.sh -h``.

    This will build from scratch all the requirements (openssl, SDL2, SDL2_image, SDL2_mixer, SDL2_ttf, python3).
    A ``build`` directory is created to contain the``MyApp.app`` directory, where ``MyApp`` is the app's name.
  * To use the existing Kivy app bundle:
    * Download the Kivy app from the Kivy download page, the GitHub releases, or the
      nightly release with e.g.::

          curl -O -L https://xxx/Kivy-xxx.dmg
    * Mount it in the current directory and fix the name to your App's name::

          hdiutil attach Kivy-xxx.dmg -mountroot .
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

    On the default macOS shell (zsh) you **must** be in the bin directory containing ``activate`` to be
    able to ``activate`` the virtualenv. ``kivy_activate`` is only necessary if you'll run
    Kivy in the environment - it sets up the Kivy home, and other Kivy environment
    variables.
  * Install any frameworks and relocate them (Consider building the needed frameworks from sources, so you can control the `MACOSX_DEPLOYMENT_TARGET` and supported archs):
    * Mount any frameworks e.g. ``MyFramework`` on your system and copy it over to the app::

          hdiutil attach MyFramework.dmg
          cp -a /Volumes/MyFramework/MyFramework.framework MyApp.app/Contents/Frameworks/

    * Relocate the framework so it can be used from a different path. E.g.::

          python -m pip install git+https://github.com/tito/osxrelocator
          osxrelocator -r MyApp.app MyApp.app/Contents/Frameworks/MyFramework/ @executable_path/Contents/Frameworks/MyFramework/
          osxrelocator -r MyApp.app @rpath/MyFramework.framework/Versions/A/MyFramework \
              @executable_path/Contents/Frameworks/MyFramework.framework/Versions/A/MyFramework

      This should be customized for each framework. See the ``create-osx-bundle.sh`` script for examples.
  * By using the ``prepare-wheels.py`` helper, download and prepare wheels before installing them.
    This script will download the wheels, accordingly to your ``MACOSX_DEPLOYMENT_TARGET`` and merge them into a single ``universal2`` wheel if one is not available from PyPI.

    If no compatible wheel is available, the script will download the source distribution.

    To see all the available options, and usage instructions, run::

        python prepare-wheels.py -h

    Since this tool is rapidly evolving, and the process to install the downloaded 
    wheels is done via ``pip``, consider looking at ``create-osx-bundle.sh`` for examples on how to use the downloaded artifacts.

    :warning: Never install dependencies via ``pip`` from the virtual environment, without using the ``prepare-wheels.py`` helper, as it will install the architecture-specific wheels, and not the ``universal2`` ones.

  * Deactivate the virtualenv by running ``deactivate`` in the shell.
* Reduce app size (optional):

  You can reduce the app size by removing unnecessary files. We provide a script to remove files commonly
  not needed. Run it with::

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

    python3 -m venv venv
    source venv/bin/activate

    cd kivy-sdk-packager/osx

    pip install -r requirements.txt

    curl -O -L https://xxx/Kivy-xxx.dmg
    hdiutil attach Kivy-xxx.dmg -mountroot .

    # notice capital R, don't use lowercase as it will copy symbolic links in a cycle
    cp -R Kivy/Kivy.app MyApp.app
    ./fix-bundle-metadata.sh MyApp.app -n MyApp -v "0.1.1" -a "Name" -o \
        "org.myorg.myapp" -i "../../myapp/doc/source/images/myapp_icon.png"

    # Prepare a my-app-requirements.txt file with your app's dependencies (even indirect ones)
    # and run the following command to prepare the distributions to later be installed in the
    # virtualenv.
    python prepare-wheels.py --requirements-file my-app-requirements.txt --output-folder my-app-wheels

    pushd MyApp.app/Contents/Resources/venv/bin
    source activate
    popd

    SITE_PACKAGES_DIR=$(python -c "import site; print(site.getsitepackages()[0])")
    pip install --platform macosx_11_0_universal2 --find-links=./my-app-wheels --no-deps --target $SITE_PACKAGES_DIR -r my-app-requirements.txt

    # Reduce app size
    ./cleanup-app.sh MyApp.app

    # the link needs to be created relative to the yourapp path, so go to that directory
    pushd MyApp.app/Contents/Resources/
    ln -s ./venv/bin/myapp yourapp
    popd

    ./relocate.sh MyApp.app
    ./create-osx-dmg.sh MyApp.app MyApp


Example create app from scratch
-------------------------------

``create-osx-bundle.sh`` can be used to create a app bundle from scratch. It will download and
build all the dependencies, and create a app bundle with a virtualenv with the dependencies
installed.

You can later use the same steps as above to install your app and its dependencies, and create a
dmg.


Dev note:: Buildozer uses this repository for its OS X packaging process.
