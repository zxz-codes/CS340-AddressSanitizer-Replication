#!/usr/bin/env bash
# Remove only the two previously inventoried PERIOD images; never prune globally.
set -Eeuo pipefail
project_root=$(realpath "${1:-$(dirname "$0")/..}")
mkdir -p "$project_root/records/setup"
exec > >(tee "$project_root/records/setup/period-image-cleanup.log") 2>&1
docker system df -v
df -B1 /
for id in 8f80860515f147a56c351573e1ecb12e66068f0fe07bf128890f9a38ddb8c6b5 8f47d8b9148f2db579627842026e722d0f205ddeab13e70ee41a8df3dbd59fbc; do
  if docker image inspect "$id" > "$project_root/records/setup/removed-image-$id.json" 2>/dev/null; then
    [[ -z $(docker ps -aq --filter "ancestor=$id") ]] || { echo 'Image still used by a container; stopping.'; exit 1; }
    docker image rm "$id"
  fi
done
docker system df -v
df -B1 /
du -sh /var/lib/containerd /var/lib/docker
echo 'The WSL distribution and VHDX were preserved. Windows VHDX compaction was not attempted.'
