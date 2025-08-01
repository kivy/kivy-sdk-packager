# Extract the build architecture from the arguments
param(
    [string]$build_arch = "x64"
)

# Check if KIVY_DEPS_BUILD is set
if ($env:KIVY_DEPS_BUILD) {
    Write-Host "KIVY_DEPS_BUILD is set. Powershell script should be run in a clean environment."
    exit 1
}
# Set KIVY_DEPS_BUILD to 1
$env:KIVY_DEPS_BUILD = 1

Write-Host "Building SDL3 dependencies for $build_arch architecture."

# Cleaning the kivy-dependencies/download, kivy-dependencies/build and kivy-dependencies/dist folders
Write-Host "Cleaning the kivy-dependencies folder..."
Remove-Item -Path "kivy-dependencies" -Force -Recurse -ErrorAction SilentlyContinue

# Create the kivy-dependencies folder
New-Item -ItemType Directory -Path kivy-dependencies

# Create the kivy-dependencies/Powershell folder
New-Item -ItemType Directory -Path kivy-dependencies/WindowsPowerShell/Modules

pushd kivy-dependencies
Write-Host "Downloading the Visual Studio Setup PowerShell module ..."
Invoke-WebRequest -Uri "https://github.com/microsoft/vssetup.powershell/releases/download/2.2.12-65a71775b3/VSSetup.zip" -OutFile "VSSetup.zip"
Expand-Archive VSSetup.zip "WindowsPowerShell\Modules\VSSetup"
Write-Host "Visual Studio Setup PowerShell module downloaded."
popd

Write-Host "Adding the Visual Studio Setup PowerShell module to the PSModulePath ..."
$env:PSModulePath = $env:PSModulePath + ";$(pwd)\kivy-dependencies\WindowsPowerShell\Modules"

# Get the Visual Studio installation path
$vs_install_path = Get-VSSetupInstance | Where-Object { $_.InstallationPath -ne $null } | Select-Object -ExpandProperty InstallationPath
Write-Host "Visual Studio installation path: $vs_install_path"

# Set the environment variables via vcvarsall.bat
$vcvars_path = "$vs_install_path/VC/Auxiliary/Build/vcvarsall.bat"
Write-Host "vcvarsall path: $vcvars_path"

# Call the .bat file from the PowerShell script
cmd.exe /c " `"$vcvars_path`" $build_arch && set" | ForEach-Object {
    if ($_ -match "=") {
        $v = $_.split("=", 2);
        Set-Item -Force -Path "ENV:\$($v[0])" -Value "$($v[1])";
        Write-host "Setting $($v[0]) to $($v[1])"
    }
};

write-host "`nVisual Studio Command Prompt variables set." -ForegroundColor Yellow


# Create the kivy-dependencies/download folder
New-Item -ItemType Directory -Path kivy-dependencies/download

# Create the build folder for the dependencies
New-Item -ItemType Directory -Path kivy-dependencies/build  

# Create the dist folder for the dependencies
New-Item -ItemType Directory -Path kivy-dependencies/dist

# windows SDL3
$WINDOWS__SDL3__VERSION = "3.2.18"
$WINDOWS__SDL3__URL="https://github.com/libsdl-org/SDL/releases/download/release-$WINDOWS__SDL3__VERSION/SDL3-$WINDOWS__SDL3__VERSION.tar.gz"
$WINDOWS__SDL3__FOLDER="SDL3-$WINDOWS__SDL3__VERSION"

# windows SDL3_image
$WINDOWS__SDL3_IMAGE__VERSION="3.2.4"
$WINDOWS__SDL3_IMAGE__URL="https://github.com/libsdl-org/SDL_image/releases/download/release-$WINDOWS__SDL3_IMAGE__VERSION/SDL3_image-$WINDOWS__SDL3_IMAGE__VERSION.tar.gz"
$WINDOWS__SDL3_IMAGE__FOLDER="SDL3_image-$WINDOWS__SDL3_IMAGE__VERSION"

# windows SDL3_mixer
$WINDOWS__SDL3_MIXER__URL="https://github.com/libsdl-org/SDL_mixer/archive/refs/heads/main.tar.gz"
$WINDOWS__SDL3_MIXER__FOLDER="SDL_mixer-main"

# windows SDL3_ttf
$WINDOWS__SDL3_TTF__VERSION = "3.2.2"
$WINDOWS__SDL3_TTF__URL="https://github.com/libsdl-org/SDL_ttf/releases/download/release-$WINDOWS__SDL3_TTF__VERSION/SDL3_ttf-$WINDOWS__SDL3_TTF__VERSION.tar.gz"
$WINDOWS__SDL3_TTF__FOLDER="SDL3_ttf-$WINDOWS__SDL3_TTF__VERSION"

# Download the dependencies
Write-Host "Downloading the dependencies..."
Write-Host "-- SDL3, url: $WINDOWS__SDL3__URL"
Invoke-WebRequest -Uri $WINDOWS__SDL3__URL -OutFile "kivy-dependencies/download/SDL3-$WINDOWS__SDL3__VERSION.tar.gz"
Invoke-WebRequest -Uri $WINDOWS__SDL3_IMAGE__URL -OutFile "kivy-dependencies/download/SDL3_image-$WINDOWS__SDL3_IMAGE__VERSION.tar.gz"
Invoke-WebRequest -Uri $WINDOWS__SDL3_MIXER__URL -OutFile "kivy-dependencies/download/SDL_mixer-main.tar.gz"
Invoke-WebRequest -Uri $WINDOWS__SDL3_TTF__URL -OutFile "kivy-dependencies/download/SDL3_ttf-$WINDOWS__SDL3_TTF__VERSION.tar.gz"

# Save dist folder full path
$dist_folder = (Get-Item -Path ".\kivy-dependencies\dist").FullName

pushd kivy-dependencies/build

Write-Host "Extracting the dependencies..."
# Extract the dependencies
tar -xf "../download/SDL3-$WINDOWS__SDL3__VERSION.tar.gz"
tar -xf "../download/SDL3_image-$WINDOWS__SDL3_IMAGE__VERSION.tar.gz"
tar -xf "../download/SDL_mixer-main.tar.gz"
tar -xf "../download/SDL3_ttf-$WINDOWS__SDL3_TTF__VERSION.tar.gz"

# Move into the SDL3 folder
Write-Host "-- Build SDL3"
cd $WINDOWS__SDL3__FOLDER
cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$dist_folder" -DCMAKE_BUILD_TYPE=Release -GNinja
cmake --build build/ --config Release --verbose --parallel
cmake --install build/ --config Release

cd ..

# Move into the SDL_mixer folder
Write-Host "-- Build SDL_mixer"
cd $WINDOWS__SDL3_MIXER__FOLDER
./external/Get-GitModules.ps1
cmake -B build -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_BUILD_TYPE=Release -DSDLMIXER_VENDORED=ON  -DSDL_DIR="$dist_folder/cmake"  -DCMAKE_INSTALL_PREFIX="$dist_folder" -GNinja
cmake --build build/ --config Release --parallel --verbose
cmake --install build/ --config Release
cd ..

# Move into the SDL_image folder
Write-Host "-- Build SDL_image"
cd $WINDOWS__SDL3_IMAGE__FOLDER
./external/Get-GitModules.ps1
cmake -B build -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release -DSDLIMAGE_TIF_VENDORED=ON -DSDLIMAGE_WEBP_VENDORED=ON -DSDLIMAGE_JPG_VENDORED=ON -DSDLIMAGE_PNG_VENDORED=ON -DSDLIMAGE_TIF_SHARED=OFF -DSDLIMAGE_WEBP_SHARED=OFF  -DSDLIMAGE_VENDORED=OFF -DSDL_DIR="$dist_folder/cmake"  -DCMAKE_INSTALL_PREFIX="$dist_folder" -DCMAKE_POLICY_DEFAULT_CMP0141=NEW -GNinja
cmake --build build/ --config Release --parallel --verbose
cmake --install build/ --config Release
cd ..

# Move into the SDL_ttf folder
Write-Host "-- Build SDL_ttf"
cd $WINDOWS__SDL3_TTF__FOLDER
./external/Get-GitModules.ps1
cmake -B build-cmake -DBUILD_SHARED_LIBS=ON -DSDLTTF_HARFBUZZ=ON -DFT_DISABLE_PNG=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_BUILD_TYPE=Release -DSDLTTF_VENDORED=ON -DSDL_DIR="$dist_folder/cmake"  -DCMAKE_INSTALL_PREFIX="$dist_folder" -GNinja
cmake --build build-cmake --config Release --verbose
cmake --install build-cmake/ --config Release --verbose
cd ..

popd

# Set KIVY_DEPS_ROOT to the dist folder
Write-Host "Setting KIVY_DEPS_ROOT to $dist_folder"
$env:KIVY_DEPS_ROOT = $dist_folder

Write-Host "Dependencies built successfully."