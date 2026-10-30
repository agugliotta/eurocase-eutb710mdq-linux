#!/bin/sh
set -eu
arm-linux-gnueabihf-gcc -Os -Wall -Wextra -Werror /work/tablet-poc.c -o /out/tablet-poc -lasound -lm
arm-linux-gnueabihf-strip /out/tablet-poc
mkdir -p /out/bundle/poc/bin /out/bundle/poc/lib
cp /out/tablet-poc /out/bundle/poc/bin/
for lib in ld-linux-armhf.so.3 libc.so.6 libm.so.6 libasound.so.2; do
    cp -L /lib/arm-linux-gnueabihf/$lib /out/bundle/poc/lib/
done
arm-linux-gnueabihf-readelf -d /out/tablet-poc
arm-linux-gnueabihf-readelf -d /out/bundle/poc/lib/libasound.so.2
tar -C /out/bundle -czf /out/poc-bundle.tar.gz poc
