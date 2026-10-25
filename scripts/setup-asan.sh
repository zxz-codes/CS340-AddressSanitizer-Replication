#!/usr/bin/env bash
set -Eeuo pipefail
project_root=$(realpath "${1:-$(dirname "$0")/..}")
mkdir -p "$project_root/records/setup"
exec > >(tee -a "$project_root/records/setup/install.log") 2>&1
export DEBIAN_FRONTEND=noninteractive
if [[ ${ASAN_SKIP_APT_UPDATE:-0} != 1 ]]; then apt-get -o Acquire::Retries=3 update; fi
if [[ -f "$project_root/config/install-packages.txt" ]]; then
  mapfile -t packages < "$project_root/config/install-packages.txt"
else
  packages=(clang-14 llvm-14 build-essential cmake ninja-build python3-venv python3-pip ca-certificates git time)
fi
apt-get -o Acquire::Retries=3 install -y --no-install-recommends "${packages[@]}"
work_root=${CS340_ASAN_WORKDIR:-${XDG_CACHE_HOME:-$HOME/.cache}/cs340-asan}
mkdir -p "$work_root"
python3 -m venv "$work_root/venv"
"$work_root/venv/bin/python" -m pip install 'lit==14.0.6'
bash "$project_root/scripts/fetch-benchmarks.sh" "$project_root"
clang-14 --version
llvm-symbolizer-14 --version
"$work_root/venv/bin/lit" --version
printf '%s\n' "$work_root" > "$project_root/records/setup/linux-work-root.txt"
bash "$project_root/scripts/capture-environment.sh" "$project_root"
