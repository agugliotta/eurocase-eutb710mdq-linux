#!/usr/bin/env python3
"""Prepare a board-only RAM efuse-map fallback without editing upstream Linux."""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[2]
source = root / '.tools/sources/linux-6.12/drivers/net/wireless/realtek/rtl8xxxu/8188e.c'
stock = root / 'acquisition/originals/board-config/rtk_efuse_8188etv.map'
raw = bytes.fromhex(stock.read_text())
assert len(raw) == 512 and raw[:2] == b'\x29\x81'
assert raw[0x130:0x13d] == (root / 'analysis/wifi/v1/mainline-efuse-map.bin').read_bytes()[0x130:0x13d]
assert all(value <= 63 for value in raw[0x10:0x1b]) and raw[0xb9] != 255
firmware = root / 'analysis/wifi/v1/firmware/rtlwifi/eurocase-g739-rtl8188eu-efuse.bin'
firmware.parent.mkdir(parents=True, exist_ok=True)
firmware.write_bytes(raw)
code = source.read_text()
needle = 'static int rtl8188eu_parse_efuse(struct rtl8xxxu_priv *priv)'
assert code.count(needle) == 1
validator = '''static bool eurocase_efuse_map_valid(const u8 *otp, const u8 *map, size_t size)
{
	unsigned int i;

	if (size != 512 || map[0] != 0x29 || map[1] != 0x81 ||
	    map[0xb9] == 0xff || memcmp(otp + 0x130, map + 0x130, 13))
		return false;
	for (i = 0x10; i < 0x1b; i++)
		if (map[i] > 63)
			return false;
	return true;
}

'''
code = code.replace(needle, validator + needle)
needle = '\tether_addr_copy(priv->mac_addr, efuse->mac_addr);'
assert code.count(needle) == 1
replacement = '''	/* This tablet's stock driver supplies its missing calibration from a file. */
	if (of_machine_is_compatible("eurocase,eutb-710mdq") &&
	    !memchr_inv(&efuse->tx_power_index_A, 0xff, sizeof(efuse->tx_power_index_A)) &&
	    efuse->xtal_k == 0xff) {
		const struct firmware *map;
		u8 original_mac[ETH_ALEN];
		bool missing_mac = !is_valid_ether_addr(efuse->mac_addr);
		int ret;

		ret = request_firmware(&map, "rtlwifi/eurocase-g739-rtl8188eu-efuse.bin",
				       &priv->udev->dev);
		if (ret)
			return ret;
		if (!eurocase_efuse_map_valid((const u8 *)efuse, map->data, map->size)) {
			release_firmware(map);
			return -EINVAL;
		}
		ether_addr_copy(original_mac, efuse->mac_addr);
		/* Replace only the software shadow, never program the physical eFuse. */
		memcpy(efuse, map->data, sizeof(*efuse));
		release_firmware(map);
		if (missing_mac)
			eth_random_addr(efuse->mac_addr);
		else
			ether_addr_copy(efuse->mac_addr, original_mac);
		dev_info(&priv->udev->dev, "Eurocase stock calibration applied in RAM%s\\n",
			 missing_mac ? "; locally administered MAC" : "");
	}

	ether_addr_copy(priv->mac_addr, efuse->mac_addr);'''
code = code.replace(needle, replacement)
code = code.replace('#include "regs.h"', '#include <linux/etherdevice.h>\n#include <linux/firmware.h>\n#include <linux/of.h>\n\n#include "regs.h"', 1)
output = root / '.tools/overlays/wifi-rtl8188e.c'
output.write_text(code)
(root / 'analysis/wifi/v1/driver-overlay.c').write_text(code)
print(f'Prepared overlay and RAM calibration map SHA256={hashlib.sha256(raw).hexdigest()}')
