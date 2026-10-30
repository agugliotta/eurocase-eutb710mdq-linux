#!/bin/sh
set -eu
target=$1
# The custom inittab starts only USB, logging and the existing panel.
rm -f "$target/etc/init.d/S40network" "$target/etc/init.d/S01syslogd" \
    "$target/etc/init.d/S02klogd" "$target/etc/init.d/S20urandom"
mkdir -p "$target/lib/firmware/silead" "$target/lib/firmware/rtlwifi"
cp /firmware/silead/eurocase-g739-gsl1680-1024x600.fw "$target/lib/firmware/silead/"
cp /firmware/rtlwifi/rtl8188eufw.bin "$target/lib/firmware/rtlwifi/"
rm -rf "$target/var"
ln -s run "$target/var"
