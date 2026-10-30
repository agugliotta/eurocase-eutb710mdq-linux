FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc-arm-linux-gnueabihf binutils-arm-linux-gnueabihf \
    bison flex bc libssl-dev device-tree-compiler python3 python3-dev \
    python3-setuptools python3-pyelftools swig ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV CROSS_COMPILE=arm-linux-gnueabihf-
