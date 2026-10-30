#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Builds regular files only. No USB, privileged container or block-device access.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
for name in gslX680.cfg rtk_efuse_8188etv.map; do
    test -s "firmware/$name" || {
        echo "Missing firmware/$name. See firmware/README.md for stock extraction instructions." >&2
        exit 1
    }
done
command -v docker >/dev/null || { echo 'Install and start Docker first.' >&2; exit 1; }
docker info >/dev/null
mkdir -p dist
docker build --platform linux/amd64 -t eutb710mdq-builder -f tools/build/Dockerfile .
docker run --platform linux/amd64 --rm --init \
    -e JOBS="${JOBS:-4}" \
    -v "$PWD:/project:ro" -v "$PWD/dist:/artifacts" \
    -v "${BUILD_VOLUME:-eutb710mdq-build}:/cache" \
    eutb710mdq-builder sh /project/tools/build/build.sh
