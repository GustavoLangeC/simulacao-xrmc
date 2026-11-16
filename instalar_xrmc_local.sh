#!/usr/bin/env bash
set -euo pipefail

# Instalação local, sem sudo, para Debian/Trixie. Não altera /usr/local.
base_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deps="$base_dir/.deps"
mkdir -p "$deps/xraylib" "$deps/src" "$deps/build"

work=$(mktemp -d /tmp/xrmc-local.XXXXXX)
trap 'rm -rf "$work"' EXIT
(
  cd "$work"
  apt-get download libxrl11 libxrl-dev
  dpkg-deb -x libxrl11_*.deb "$deps/xraylib"
  dpkg-deb -x libxrl-dev_*.deb "$deps/xraylib"
)
curl -L --fail --silent --show-error \
  https://github.com/golosio/xrmc/releases/download/XRMC-6.7.0/xrmc-6.7.0.tar.gz \
  -o "$work/xrmc-6.7.0.tar.gz"
tar -xzf "$work/xrmc-6.7.0.tar.gz" -C "$deps/src"

build="$deps/build/xrmc-6.7.0"
mkdir -p "$build"
xrl="$deps/xraylib"
(
  cd "$build"
  xraylib_CFLAGS="-I$xrl/usr/include/xraylib" \
  xraylib_LIBS="-L$xrl/usr/lib/x86_64-linux-gnu -lxrl -lm" \
  "$deps/src/xrmc-6.7.0/configure" --prefix="$deps/xrmc" --disable-xmi-msim
  make -j2
  make install
)
echo "XRMC local instalado em: $deps/xrmc/bin/xrmc"
