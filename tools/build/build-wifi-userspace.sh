#!/bin/sh
# Clone build state into a separate volume; keep the validated SD build read-only.
set -eu
if [ ! -f /out/.config ]; then
    cp -a /validated/. /out/
fi
/src/utils/config --file /out/.config \
    -e BR2_PACKAGE_IW -e BR2_PACKAGE_WPA_SUPPLICANT \
    -e BR2_PACKAGE_WPA_SUPPLICANT_NL80211 \
    -e BR2_PACKAGE_WPA_SUPPLICANT_CLI -e BR2_PACKAGE_WPA_SUPPLICANT_PASSPHRASE \
    -d BR2_PACKAGE_WPA_SUPPLICANT_WPA3 -d BR2_PACKAGE_WPA_SUPPLICANT_WPS \
    -d BR2_PACKAGE_WPA_SUPPLICANT_EAP -d BR2_PACKAGE_WPA_SUPPLICANT_WEXT
make -C /src O=/out BR2_EXTERNAL=/work/tools/buildroot olddefconfig
make -C /src O=/out BR2_DL_DIR=/downloads -j6 iw wpa_supplicant
mkdir -p /export/bundle/wifi/bin /export/bundle/wifi/lib
for name in iw wpa_supplicant wpa_cli wpa_passphrase; do
    path=$(find /out/target/usr/bin /out/target/usr/sbin -name "$name" -type f)
    test -n "$path"
    cp "$path" "/export/bundle/wifi/bin/$name"
done
for name in libnl-3.so.200 libnl-genl-3.so.200; do
    cp -L "/out/target/usr/lib/$name" "/export/bundle/wifi/lib/$name"
done
qemu-arm -L /out/target /export/bundle/wifi/bin/iw --version
qemu-arm -L /out/target /export/bundle/wifi/bin/wpa_supplicant -v
qemu-arm -L /out/target /export/bundle/wifi/bin/wpa_cli -v
cp /out/.config /export/buildroot.config
tar -C /export/bundle -czf /export/wifi-bundle.tar.gz wifi
