function raise-only-error{
    Param([scriptblock]$Func)
    # powershell interprets writing to stderr as an error, so only raise error if the return code is none-zero
    try {
      $Func.Invoke()
    } catch {
      if ($LastExitCode -ne 0) {
        throw $_
      } else {
        echo $_
      }
    }
}

function Prepre-env {
    pip install requests twine

    mkdir "$(pwd)\dist"
    mkdir "$(pwd)\$env:KIVY_BUILD_DIR"
    if (!(Test-Path "$(pwd)\$env:KIVY_BUILD_CACHE")) {
      mkdir "$(pwd)\$env:KIVY_BUILD_CACHE"
    }
}


function Download-Packages() {
    python -m pip install pip wheel setuptools --upgrade
    python -m "win.$env:PACKAGE_TARGET" build_path "$(pwd)\$env:KIVY_BUILD_DIR" arch $env:PACKAGE_ARCH package $env:PACKAGE_TARGET output "$(pwd)\dist" cache "$(pwd)\$env:KIVY_BUILD_CACHE" download_only "1"
}


function Create-Packages() {
    python -m pip install pip wheel setuptools --upgrade
    python -m "win.$env:PACKAGE_TARGET" build_path "$(pwd)\$env:KIVY_BUILD_DIR" arch $env:PACKAGE_ARCH package $env:PACKAGE_TARGET output "$(pwd)\dist" cache "$(pwd)\$env:KIVY_BUILD_CACHE"
    dir "$(pwd)\dist"
    rm "$(pwd)\dist\*tar.gz"
}


function Upload-windows-wheels-to-server($ip) {
    echo "Uploading wheels*:"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps.$env:PACKAGE_TARGET`_dev-*.whl' ci/win/deps/$env:PACKAGE_TARGET`_dev/"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps.$env:PACKAGE_TARGET-*.whl' ci/win/deps/$env:PACKAGE_TARGET/"
}

function Test-kivy() {
    $env:GST_REGISTRY="~/registry.bin"
    $env:KIVY_GL_BACKEND="angle_sdl2"
    # workaround for https://github.com/pyinstaller/pyinstaller/issues/4265 until next release
    python -m pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

    python -m pip config set install.find-links "$(pwd)\dist"

    git clone --depth 1 git://github.com/kivy/kivy.git kivy_src
    # use the current kivy_deps just built, not the older version specified in the reqs
    ((get-content -Path kivy_src/pyproject.toml -Raw) -replace "kivy_deps.$env:PACKAGE_TARGET`_dev~.+;","kivy_deps.$env:PACKAGE_TARGET`_dev;") | set-content -Path kivy_src/pyproject.toml
    ((get-content -Path kivy_src/pyproject.toml -Raw) -replace "kivy_deps.$env:PACKAGE_TARGET~.+;","kivy_deps.$env:PACKAGE_TARGET;") | set-content -Path kivy_src/pyproject.toml
    ((get-content -Path kivy_src/setup.cfg -Raw) -replace "kivy_deps.$env:PACKAGE_TARGET~.+;","kivy_deps.$env:PACKAGE_TARGET;") | set-content -Path kivy_src/setup.cfg
    python -m pip install "./kivy_src[full,dev]"

    python -c 'import kivy'
    $test_path=python -c 'import kivy.tests as tests; print(tests.__path__[0])'  --config "kivy:log_level:error"
    cd "$test_path"

    echo "[run]`nplugins = kivy.tools.coverage`n" > .coveragerc
    python -m pytest .
}

function Get-angle-deps() {
    Invoke-WebRequest -Uri "https://storage.googleapis.com/chrome-infra/depot_tools.zip" -OutFile depot_tools.zip
    7z x depot_tools.zip -odepot_tools
    git clone https://github.com/google/angle.git angle_src
}

function Build-angle() {
    $env:PATH="$(pwd)\depot_tools;$env:PATH"
    $env:PATH="$(python -c "import os; print(';'.join([p for p in os.environ['PATH'].split(';') if 'Python' not in p and 'python' not in p and 'Chocolatey' not in p]))")"
    cd angle_src

    gclient
    python scripts/bootstrap.py
    gclient sync

    gn gen out/Release_x86 --args='is_debug=false target_cpu=""x86""'
    type out/Release_x86/args.gn
    autoninja -C out\Release_x86 libEGL
    autoninja -C out\Release_x86 libGLESv2

    gn gen out/Release_x64 --args='is_debug=false target_cpu=""x64""'
    type out/Release_x64/args.gn
    autoninja -C out\Release_x64 libEGL
    autoninja -C out\Release_x64 libGLESv2

    dir out\Release_x64
    dir out\Release_x86

    cd ..
    mkdir angle_dlls\Release_x64
    mkdir angle_dlls\Release_x86
    cp angle_src\out\Release_x64\*.dll angle_dlls\Release_x64
    cp angle_src\out\Release_x86\*.dll angle_dlls\Release_x86
}

function Prepare-ttf($arch) {
    # currently there's a binary incompatibility between gst and harfbuzz compiled here for x86. So
    # don't include that for x86
    if ($arch -eq "x64") {
        Prepare-ttf-x64 -arch $arch
    } else {
        Prepare-ttf-x86 -arch $arch
    }
}

function Prepare-ttf-x64($arch) {
    python -m pip install --upgrade meson ninja fonttools

    $root="harfbuzz-2.8.0"
    $harf_path="$(pwd)\$root"

    # get and compile harfbuzz
    Invoke-WebRequest -Uri "https://github.com/harfbuzz/harfbuzz/releases/download/2.8.0/$root.tar.xz" -OutFile "$root.tar.xz"
    C:\"Program Files"\7-Zip\7z.exe x "$root.tar.xz"
    C:\"Program Files"\7-Zip\7z.exe x "$root.tar"
    cd "$root"

    # This dir contains a pkg-config which meson will happily use and later fail, so remove it
    $env:path = ($env:path.Split(';') | Where-Object { $_ -ne 'C:\Strawberry\perl\bin' }) -join ';'

    meson setup build --wrap-mode=default --buildtype=release -Dglib=disabled -Dgobject=disabled -Dcairo=disabled `
-Dfreetype=enabled -Dgdi=enabled -Ddirectwrite=enabled -Dicu=disabled
    meson compile -C build
    cd ..

    # get sdl2
    cp "$env:KIVY_BUILD_CACHE\SDL2-devel-*-VC.zip" .
    C:\"Program Files"\7-Zip\7z.exe x "SDL2-devel-*-VC.zip"
    cd "SDL2-*"
    $sdl2="$(pwd)"
    cd ..

    # get sdl_ttf
    Invoke-WebRequest -Uri "https://github.com/libsdl-org/SDL_ttf/archive/refs/heads/main.zip" -OutFile "SDL_ttf-main.zip"
    C:\"Program Files"\7-Zip\7z.exe x "SDL_ttf-main.zip"

    # now build it
    $env:UseEnv="true"
    $env:INCLUDE="$env:INCLUDE;$sdl2\include;$harf_path\src"
    $env:LIB="$env:LIB;$sdl2\lib\$arch;$harf_path\build\src"
    $env:CL="/DTTF_USE_HARFBUZZ#1"

    if ($arch -eq "x64") {
        $ttf_arch="x64"
    } else {
        $ttf_arch="Win32"
    }

    cd .\SDL_ttf-main\VisualC\
    devenv .\SDL_ttf.sln /Upgrade
    (Get-Content .\SDL_ttf.vcxproj).replace(";%(AdditionalDependencies)",";harfbuzz.lib;%(AdditionalDependencies)") | Set-Content .\SDL_ttf.vcxproj
    devenv /UseEnv .\SDL_ttf.sln  /Build "Release|$ttf_arch"
    cd "..\..\"

    mkdir "result"
    mkdir "result\SDL2_ttf-main"
    mkdir "result\SDL2_ttf-main\include"
    mkdir "result\SDL2_ttf-main\include\harfbuzz"
    mkdir "result\SDL2_ttf-main\lib"
    mkdir "result\SDL2_ttf-main\lib\$arch"

    cp ".\SDL_ttf-main\VisualC\$ttf_arch\Release\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\VisualC\$ttf_arch\Release\*.lib" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\VisualC\$ttf_arch\Release\LICENSE*.txt" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\*.h" "result\SDL2_ttf-main\include"

    cp "$harf_path\build\src\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp "$harf_path\build\src\*.lib" "result\SDL2_ttf-main\lib\$arch"
    cp "$harf_path\build\subprojects\*\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp "$harf_path\build\subprojects\*\*\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp "$harf_path\build\subprojects\*\*\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp "$harf_path\src\*.h" "result\SDL2_ttf-main\include\harfbuzz"

    Compress-Archive -LiteralPath "result\SDL2_ttf-main" -DestinationPath "SDL2_ttf-devel-main-VC.zip"
    cp "SDL2_ttf-devel-main-VC.zip" "$env:KIVY_BUILD_CACHE"
}

function Prepare-ttf-x86($arch) {
    # get sdl2
    cp "$env:KIVY_BUILD_CACHE\SDL2-devel-*-VC.zip" .
    C:\"Program Files"\7-Zip\7z.exe x "SDL2-devel-*-VC.zip"
    cd "SDL2-*"
    $sdl2="$(pwd)"
    cd ..

    # get sdl_ttf
    Invoke-WebRequest -Uri "https://github.com/libsdl-org/SDL_ttf/archive/refs/heads/main.zip" -OutFile "SDL_ttf-main.zip"
    C:\"Program Files"\7-Zip\7z.exe x "SDL_ttf-main.zip"

    # now build it
    $env:UseEnv="true"
    $env:INCLUDE="$env:INCLUDE;$sdl2\include"
    $env:LIB="$env:LIB;$sdl2\lib\$arch"

    cd .\SDL_ttf-main\VisualC\
    devenv .\SDL_ttf.sln /Upgrade
    devenv /UseEnv .\SDL_ttf.sln  /Build "Release|Win32"
    cd "..\..\"

    mkdir "result"
    mkdir "result\SDL2_ttf-main"
    mkdir "result\SDL2_ttf-main\include"
    mkdir "result\SDL2_ttf-main\lib"
    mkdir "result\SDL2_ttf-main\lib\$arch"

    cp ".\SDL_ttf-main\VisualC\Win32\Release\*.dll" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\VisualC\Win32\Release\*.lib" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\VisualC\Win32\Release\LICENSE*.txt" "result\SDL2_ttf-main\lib\$arch"
    cp ".\SDL_ttf-main\*.h" "result\SDL2_ttf-main\include"

    Compress-Archive -LiteralPath "result\SDL2_ttf-main" -DestinationPath "SDL2_ttf-devel-main-VC.zip"
    cp "SDL2_ttf-devel-main-VC.zip" "$env:KIVY_BUILD_CACHE"
}
