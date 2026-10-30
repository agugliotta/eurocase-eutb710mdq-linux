# SPDX-License-Identifier: GPL-2.0-or-later
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc-arm-linux-gnueabihf binutils-arm-linux-gnueabihf \
    bison flex bc libssl-dev device-tree-compiler python3 python3-dev \
    python3-setuptools python3-pyelftools swig ca-certificates \
    wget curl rsync file cpio unzip patch perl bzip2 xz-utils qemu-user cmake \
    && rm -rf /var/lib/apt/lists/*
ENV ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- FORCE_UNSAFE_CONFIGURE=1
