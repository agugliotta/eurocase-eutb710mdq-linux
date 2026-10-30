#!/bin/sh
set -e
g=/sys/kernel/config/usb_gadget/eutb
mkdir "$g"
echo 0x1d6b > "$g/idVendor"
echo 0x0104 > "$g/idProduct"
echo 0x0200 > "$g/bcdUSB"
echo 0xEF > "$g/bDeviceClass"
echo 0x02 > "$g/bDeviceSubClass"
echo 0x01 > "$g/bDeviceProtocol"
mkdir "$g/strings/0x409"
echo eutb710mdq-ram > "$g/strings/0x409/serialnumber"
echo 'Eurocase Linux POC' > "$g/strings/0x409/manufacturer"
echo 'RAM Linux ACM ECM' > "$g/strings/0x409/product"
mkdir "$g/configs/c.1" "$g/configs/c.1/strings/0x409"
echo 'ACM and ECM' > "$g/configs/c.1/strings/0x409/configuration"
echo 100 > "$g/configs/c.1/MaxPower"
mkdir "$g/functions/acm.usb0" "$g/functions/ecm.usb0"
echo 02:71:00:00:00:01 > "$g/functions/ecm.usb0/host_addr"
echo 02:71:00:00:00:02 > "$g/functions/ecm.usb0/dev_addr"
ln -s "$g/functions/acm.usb0" "$g/configs/c.1/"
ln -s "$g/functions/ecm.usb0" "$g/configs/c.1/"
for udc in /sys/class/udc/*; do
    test -e "$udc" || continue
    echo "${udc##*/}" > "$g/UDC"
    break
done
test -n "$(cat "$g/UDC")"
echo 0 > /proc/sys/net/ipv6/conf/usb0/accept_ra
echo 0 > /proc/sys/net/ipv6/conf/usb0/autoconf
echo 0 > /proc/sys/net/ipv6/conf/usb0/router_solicitations
ip link set usb0 up
ip -6 addr add fe80::2/64 dev usb0
echo EUROCASE_USBROOT_INIT_REACHED > /dev/kmsg
