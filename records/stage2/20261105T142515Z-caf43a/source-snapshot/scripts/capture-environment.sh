#!/usr/bin/env bash
set -Eeuo pipefail
project_root=$(realpath "${1:-$(dirname "$0")/..}")
mkdir -p "$project_root/records/setup"
packages=(clang-14 llvm-14 libclang-common-14-dev build-essential cmake ninja-build python3-venv python3-pip ca-certificates git time libc6 libc6-dev libstdc++6)
dpkg-query -W -f='${binary:Package}=${Version}\n' "${packages[@]}" > "$project_root/config/install-packages.txt"
dpkg-query -W > "$project_root/records/setup/all-installed-packages.txt"
clang-14 --version > "$project_root/records/setup/compiler.txt"
llvm-symbolizer-14 --version > "$project_root/records/setup/symbolizer.txt"
cp /var/log/apt/history.log "$project_root/records/setup/apt-history.log"
cp /var/log/apt/term.log "$project_root/records/setup/apt-terminal.log"
uname -a > "$project_root/records/setup/kernel.txt"
cat /etc/os-release > "$project_root/records/setup/os-release.txt"
echo 'Pinned package versions and setup evidence saved.'
