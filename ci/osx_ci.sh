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
  git clone "https://github.com/akshayaurora/Platypus"

  pushd Platypus
  codesign -fs - products/platypus_clt
  codesign -fs - --deep products/Platypus.app
  codesign -fs - --deep products/ScriptExec.app
  popd

  sudo mkdir -p /usr/local/bin
  sudo mkdir -p /usr/local/share/platypus
  sudo cp Platypus/products/platypus_clt /usr/local/bin/platypus
  sudo cp Platypus/products/ScriptExec.app/Contents/MacOS/ScriptExec /usr/local/share/platypus/ScriptExec
  sudo cp -a Platypus/products/Platypus.app/Contents/Resources/MainMenu.nib /usr/local/share/platypus/MainMenu.nib
  sudo chmod -R 755 /usr/local/share/platypus
 }

activate_app_venv_and_test_kivy(){
  pushd /Applications/Kivy.app/Contents/Resources/venv/bin
  source activate
  source kivy_activate
  popd
  python -c 'import kivy'
  test_path=$(KIVY_NO_CONSOLELOG=1 python -c 'import kivy.tests as tests; print(tests.__path__[0])' --config "kivy:log_level:error")
  cd "$test_path"
  cat >.coveragerc <<'EOF'
[run]
  plugins = kivy.tools.coverage

EOF
  KIVY_GL_BACKEND='mock' KIVY_TEST_AUDIO=0 KIVY_NO_ARGS=1 python3 -m pytest --maxfail=10 --timeout=300 .
}
