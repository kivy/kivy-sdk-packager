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
    python -m pip install 'pip>=25.3' 'wheel<0.38.0' setuptools --upgrade
    python -m "win.$env:PACKAGE_TARGET" build_path "$(pwd)\$env:KIVY_BUILD_DIR" arch $env:PACKAGE_ARCH package $env:PACKAGE_TARGET output "$(pwd)\dist" cache "$(pwd)\$env:KIVY_BUILD_CACHE"
    dir "$(pwd)\dist"
    rm "$(pwd)\dist\*tar.gz"
}


function Upload-windows-wheels-to-server($ip) {
    echo "Uploading wheels*:"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps[._]$env:PACKAGE_TARGET`_dev-*.whl' ci/win/deps/$env:PACKAGE_TARGET`_dev/"
    C:\tools\msys64\usr\bin\bash --login -c "ci/windows-server-upload.sh $ip dist 'kivy_deps[._]$env:PACKAGE_TARGET-*.whl' ci/win/deps/$env:PACKAGE_TARGET/"
}

function Test-kivy {
    Param(
        [ValidateSet('stable', 'development')]
        [string]$KivyTestTarget = 'development'
    )

    if ($env:PACKAGE_TARGET -cnotin @('angle', 'glew', 'gstreamer', 'sdl2', 'sdl3')) {
        throw 'PACKAGE_TARGET must select a supported Windows dependency'
    }
    if ($env:PACKAGE_ARCH -cne 'x64') {
        throw 'Windows integration requires PACKAGE_ARCH=x64'
    }
    if (($env:PACKAGE_TARGET -eq 'sdl2' -and $KivyTestTarget -ne 'stable') -or
        ($env:PACKAGE_TARGET -eq 'sdl3' -and $KivyTestTarget -ne 'development')) {
        throw 'The selected SDL dependency does not match the Kivy test profile'
    }
    $pipHelp = python -m pip install --help
    if ($LASTEXITCODE -ne 0 -or ($pipHelp -join "`n") -notmatch '--build-constraint') {
        throw 'Test-kivy requires pip >=25.3 for --build-constraint. Run: python -m pip install --upgrade "pip>=25.3"'
    }
    $originChecker = (Resolve-Path -LiteralPath (
        Join-Path $PSScriptRoot 'check_wheel_origins.py'
    ) -ErrorAction Stop).Path
    $wheelDirectory = (Resolve-Path -LiteralPath (
        Join-Path (Get-Location).Path 'dist'
    ) -ErrorAction Stop).Path
    $localConstraintsPath = Join-Path (Get-Location).Path 'local-wheel-constraints.txt'
    $wheelPaths = @()
    $wheelVersions = @()
    $localConstraints = foreach ($suffix in @('', '_dev')) {
        $name = "kivy_deps.$env:PACKAGE_TARGET$suffix"
        $pattern = '^kivy_deps[._]' + [Regex]::Escape("$env:PACKAGE_TARGET$suffix") + '-'
        $wheels = @(Get-ChildItem -LiteralPath $wheelDirectory -Filter '*.whl' -File -ErrorAction Stop |
            Where-Object { $_.Name -match $pattern })
        if ($wheels.Count -ne 1) {
            throw "Expected exactly one local $name wheel, found $($wheels.Count)"
        }
        $wheel = $wheels[0]
        $wheelPaths += $wheel.FullName
        $wheelVersions += $wheel.Name.Split('-')[1]
        $uri = ([UriBuilder]::new('file', '', -1, $wheel.FullName)).Uri.AbsoluteUri
        $hash = (Get-FileHash -LiteralPath $wheel.FullName -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
        "$name @ $uri#sha256=$hash"
    }
    if (@($wheelVersions | Select-Object -Unique).Count -ne 1) {
        throw 'Local runtime/development wheel versions do not match'
    }
    Set-Content -LiteralPath $localConstraintsPath -Value $localConstraints -Encoding utf8 -ErrorAction Stop
    $localConstraints | ForEach-Object { Write-Host "Local wheel constraint: $_" }

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
    $installArgs += @('--constraint', $localConstraintsPath, '--build-constraint', $localConstraintsPath, '--verbose')

    Write-Host "Kivy integration target: $KivyTestTarget; ref: $kivyRef; backend: $env:KIVY_GL_BACKEND"
    python -m pip config set install.find-links $wheelDirectory
    if ($LASTEXITCODE -ne 0) {
        throw 'Configuring the local wheel search path failed'
    }

    python -m pip install --no-index --no-deps --force-reinstall @wheelPaths
    if ($LASTEXITCODE -ne 0) {
        throw 'Installing the explicit local dependency wheels failed'
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
    python $originChecker $localConstraintsPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Verifying the installed local dependency wheels failed'
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
        $pytestArgs = @('.')
        if ($kivyRef -eq '2.3.1') {
            # Kivy 2.3.1's UrlRequest auth tests compare live httpbin.org responses
            # exactly; httpbin now adds "authorized": true. Fixed upstream by
            # kivy/kivy#9304 (in 2.3.2+). Drop this when $kivyRef moves past 2.3.1.
            $pytestArgs += @(
                '--deselect', 'test_urlrequest/test_urlrequest_urllib.py::test_auth_header',
                '--deselect', 'test_urlrequest/test_urlrequest_urllib.py::test_auth_auto'
            )
            Write-Host 'Deselected httpbin-dependent 2.3.1 auth tests; see kivy/kivy#9304.'
        }
        python -m pytest @pytestArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'The installed Kivy test suite failed'
        }
        python $originChecker $localConstraintsPath
        if ($LASTEXITCODE -ne 0) {
            throw 'Verifying local dependency wheels after pytest failed'
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

    # Skip unused WebGPU/Dawn and compiler debug info; PDBs are not packaged.
    gn gen out/Release_x64 --args='is_debug=false target_cpu=""x64"" angle_enable_wgpu=false symbol_level=0'
    type out/Release_x64/args.gn
    autoninja -C out\Release_x64 libEGL
    autoninja -C out\Release_x64 libGLESv2

    dir out\Release_x64

    cd ..
    mkdir angle_dlls\Release_x64
    cp angle_src\out\Release_x64\*.dll angle_dlls\Release_x64
}
