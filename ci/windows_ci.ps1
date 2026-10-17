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
    python -m pip install pip wheel<0.38.0 setuptools --upgrade
    python -m "win.$env:PACKAGE_TARGET" build_path "$(pwd)\$env:KIVY_BUILD_DIR" arch $env:PACKAGE_ARCH package $env:PACKAGE_TARGET output "$(pwd)\dist" cache "$(pwd)\$env:KIVY_BUILD_CACHE"
    dir "$(pwd)\dist"
    rm "$(pwd)\dist\*tar.gz"
}


function Upload-windows-wheels-to-server($ip) {
    echo "Uploading wheels*:"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps.$env:PACKAGE_TARGET`_dev-*.whl' ci/win/deps/$env:PACKAGE_TARGET`_dev/"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps.$env:PACKAGE_TARGET-*.whl' ci/win/deps/$env:PACKAGE_TARGET/"
}

function Test-kivy {
    Param(
        [ValidateSet('stable', 'development')]
        [string]$KivyTestTarget = 'development'
    )

    $env:GST_REGISTRY="~/registry.bin"
    $kivyRef = 'master'
    $env:KIVY_GL_BACKEND = 'angle_sdl3'
    $installArgs = @('-m', 'pip', 'install')

    if ($KivyTestTarget -eq 'stable') {
        $kivyRef = '2.3.1'
        $env:KIVY_GL_BACKEND = 'angle_sdl2'
        $constraintsPath = (Resolve-Path -Path (
            Join-Path -Path $PSScriptRoot -ChildPath 'kivy-stable-test-constraints.txt'
        ) -ErrorAction Stop).Path
        $installArgs += @('--constraint', $constraintsPath)
    }

    Write-Host "Kivy integration target: $KivyTestTarget; ref: $kivyRef; backend: $env:KIVY_GL_BACKEND"
    python -m pip config set install.find-links "$(pwd)\dist"
    if ($LASTEXITCODE -ne 0) {
        throw 'Configuring the local wheel search path failed'
    }

    git clone --depth 1 --branch $kivyRef --single-branch https://github.com/kivy/kivy.git kivy_src
    if ($LASTEXITCODE -ne 0) {
        throw "Cloning Kivy ref $kivyRef failed"
    }
    $kivyCommit = git -C kivy_src rev-parse HEAD
    if ($LASTEXITCODE -ne 0) {
        throw 'Reading the Kivy source commit failed'
    }
    Write-Host "Kivy source commit: $kivyCommit"

    # use the current kivy_deps just built, not the older version specified in the reqs
    ((get-content -Path kivy_src/pyproject.toml -Raw -ErrorAction Stop) -replace "kivy_deps.$env:PACKAGE_TARGET`_dev~.+;","kivy_deps.$env:PACKAGE_TARGET`_dev;") | set-content -Path kivy_src/pyproject.toml -ErrorAction Stop
    ((get-content -Path kivy_src/pyproject.toml -Raw -ErrorAction Stop) -replace "kivy_deps.$env:PACKAGE_TARGET~.+;","kivy_deps.$env:PACKAGE_TARGET;") | set-content -Path kivy_src/pyproject.toml -ErrorAction Stop
    # Older Kivy checkouts also declare dependency constraints in setup.cfg.
    if (Test-Path -Path kivy_src/setup.cfg -PathType Leaf) {
        ((get-content -Path kivy_src/setup.cfg -Raw -ErrorAction Stop) -replace "kivy_deps.$env:PACKAGE_TARGET~.+;","kivy_deps.$env:PACKAGE_TARGET;") | set-content -Path kivy_src/setup.cfg -ErrorAction Stop
    }

    $installArgs += './kivy_src[full,dev]'
    python @installArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Kivy source installation failed'
    }

    python -c "import kivy; print('Kivy version:', kivy.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw 'Importing the installed Kivy failed'
    }
    python -c "from importlib.metadata import version; print('pytest:', version('pytest')); print('pytest-asyncio:', version('pytest-asyncio'))"
    if ($LASTEXITCODE -ne 0) {
        throw 'Reporting the installed test-runner versions failed'
    }

    $testPath = python -c 'import kivy.tests as tests; print(tests.__path__[0])' --config "kivy:log_level:error"
    if ($LASTEXITCODE -ne 0) {
        throw 'Locating the installed Kivy tests failed'
    }
    Write-Host "Installed Kivy tests: $testPath"
    if ($KivyTestTarget -eq 'stable') {
        Write-Host 'Stable coverage: released Kivy 2.3.1 suite with its accepted inherited async-app collection gap; see win/README.md.'
    }

    Push-Location -LiteralPath "$testPath" -ErrorAction Stop
    try {
        Set-Content -Path .coveragerc -Value "[run]`nplugins = kivy.tools.coverage`n" -ErrorAction Stop
        python -m pytest .
        if ($LASTEXITCODE -ne 0) {
            throw 'The installed Kivy test suite failed'
        }
    } finally {
        Pop-Location
    }
}

function Get-angle-deps() {
    Invoke-WebRequest -Uri "https://storage.googleapis.com/chrome-infra/depot_tools.zip" -OutFile depot_tools.zip
    7z x depot_tools.zip -odepot_tools
    git clone -b "chromium/6943" --single-branch https://github.com/google/angle.git angle_src
}

function Build-angle() {
    $env:PATH="$(pwd)\depot_tools;$env:PATH"
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
