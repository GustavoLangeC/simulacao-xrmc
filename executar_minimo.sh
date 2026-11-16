#!/usr/bin/env bash
set -euo pipefail

base_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
xrmc_python="${XRMC_PYTHON:-python3}"
xrmc_bin="$base_dir/.deps/xrmc/bin/xrmc"
xrmc_lib="$base_dir/.deps/xrmc/lib"
xraylib_dir="$base_dir/.deps/xraylib/usr/lib/x86_64-linux-gnu"
experiment_dir="$base_dir/minimo_pmmaa_furo"

if [[ ! -x "$xrmc_bin" ]]; then
  echo "XRMC local ausente: execute ./instalar_xrmc_local.sh" >&2
  exit 2
fi
if ! "$xrmc_python" -c 'import numpy, matplotlib' >/dev/null 2>&1; then
  echo "Python sem numpy/matplotlib: crie .venv e defina XRMC_PYTHON=.venv/bin/python" >&2
  exit 2
fi
if [[ ! -f "$xraylib_dir/libxrl.so.11" ]]; then
  echo "xraylib local ausente: execute ./instalar_xrmc_local.sh" >&2
  exit 2
fi

mkdir -p "$experiment_dir/output"
(
  cd "$experiment_dir"
  LD_LIBRARY_PATH="$xrmc_lib:$xraylib_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$xrmc_bin" input.dat
)
"$xrmc_python" "$base_dir/converter_imagem_xrmc.py" \
  "$experiment_dir/output/image.dat" "$experiment_dir/output/image.npy" \
  --largura 256 --altura 256 \
  --preview "$experiment_dir/output/image.png"
cp "$experiment_dir/manifest.json" "$experiment_dir/output/manifest.json"
"$xrmc_python" "$base_dir/gerar_referencia.py" \
  --manifest "$experiment_dir/manifest.json" \
  --imagem "$experiment_dir/output/image.npy" \
  --saida "$experiment_dir/output/verdade_simulada.npz"
"$xrmc_python" "$base_dir/validar_minimo.py" "$experiment_dir/output/image.npy"
