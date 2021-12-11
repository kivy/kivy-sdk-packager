#!/bin/bash
set -e -x

download_cache_curl() {
  fname="$1"
  key="$2"
  url_prefix="$3"

  if [ ! -f $key/$fname ]; then
    if [ ! -d $key ]; then
      mkdir "$key"
    fi
    curl -O -L "$url_prefix/$fname"
    cp "$fname" "$key"
  else
    cp "$key/$fname" .
  fi
}


arm64_set_path_and_python_version(){
  python_version="$1"
  if [[ $(/usr/bin/arch) = arm64 ]]; then
      export PATH=/opt/homebrew/bin:$PATH
      eval "$(pyenv init --path)"
      pyenv install $python_version -s
      pyenv global $python_version
      export PATH=$(pyenv prefix)/bin:$PATH
  fi
}

install_platypus() {
  download_cache_curl "platypus5.3.zip" "osx-cache" "https://github.com/sveinbjornt/Platypus/releases/download/5.3"

  unzip "platypus5.3.zip"
  gunzip Platypus.app/Contents/Resources/platypus_clt.gz
  gunzip Platypus.app/Contents/Resources/ScriptExec.gz

  sudo mkdir -p /usr/local/bin
  sudo mkdir -p /usr/local/share/platypus
  sudo cp Platypus.app/Contents/Resources/platypus_clt /usr/local/bin/platypus
  sudo cp Platypus.app/Contents/Resources/ScriptExec /usr/local/share/platypus/ScriptExec
  sudo cp -a Platypus.app/Contents/Resources/MainMenu.nib /usr/local/share/platypus/MainMenu.nib
  sudo chmod -R 755 /usr/local/share/platypus
}