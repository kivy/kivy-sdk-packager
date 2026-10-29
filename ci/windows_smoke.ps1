function Test-wheel-smoke {
    if ($env:PACKAGE_TARGET -cne 'sdl2') {
        throw 'Smoke tests are only defined for PACKAGE_TARGET=sdl2'
    }
    if ($env:PACKAGE_ARCH -cne 'x64') {
        throw 'Windows smoke tests require PACKAGE_ARCH=x64'
    }
    $originChecker = (Resolve-Path -LiteralPath (
        Join-Path $PSScriptRoot 'check_wheel_origins.py'
    ) -ErrorAction Stop).Path
    $smokeTest = (Resolve-Path -LiteralPath (
        Join-Path $PSScriptRoot 'smoke_test_wheels.py'
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

    python -m pip install --no-index --no-deps --force-reinstall @wheelPaths
    if ($LASTEXITCODE -ne 0) {
        throw 'Installing the explicit local dependency wheels failed'
    }
    python $originChecker $localConstraintsPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Verifying the installed local dependency wheels failed'
    }
    python $smokeTest $env:PACKAGE_TARGET
    if ($LASTEXITCODE -ne 0) {
        throw 'The dependency smoke test failed'
    }
}
