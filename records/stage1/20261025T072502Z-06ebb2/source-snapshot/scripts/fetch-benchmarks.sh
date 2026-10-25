#!/usr/bin/env bash
set -Eeuo pipefail
project_root=$(realpath "${1:-$(dirname "$0")/..}")
work_root=${CS340_ASAN_WORKDIR:-${XDG_CACHE_HOME:-$HOME/.cache}/cs340-asan}
commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["benchmark_commit"])' "$project_root/config/environment-lock.json")
mkdir -p "$work_root" "$project_root/records/setup"
exec > >(tee -a "$project_root/records/setup/source-download.log") 2>&1
if [[ ! -d "$work_root/llvm-test-suite/.git" ]]; then
  git clone --depth 1 --branch release/14.x --filter=blob:none --no-checkout https://github.com/llvm/llvm-test-suite.git "$work_root/llvm-test-suite"
  git -C "$work_root/llvm-test-suite" sparse-checkout set --no-cone '/*' '!/SingleSource/' '!/External/' '!/MicroBenchmarks/' '!/Fortran/' '!/MultiSource/*' '/MultiSource/CMakeLists.txt' '/MultiSource/Benchmarks/CMakeLists.txt' '/MultiSource/Benchmarks/Olden/'
fi
if ! git -C "$work_root/llvm-test-suite" cat-file -e "$commit^{commit}"; then
  git -C "$work_root/llvm-test-suite" fetch --depth 1 origin "$commit"
fi
git -C "$work_root/llvm-test-suite" checkout --detach "$commit"
git -C "$work_root/llvm-test-suite" diff --exit-code
cp "$work_root/llvm-test-suite/LICENSE.TXT" "$project_root/vendor/LLVM-test-suite-LICENSE.TXT"
git -C "$work_root/llvm-test-suite" rev-parse HEAD
find "$work_root/llvm-test-suite/MultiSource/Benchmarks/Olden" -name CMakeLists.txt -print -exec cat {} \;
