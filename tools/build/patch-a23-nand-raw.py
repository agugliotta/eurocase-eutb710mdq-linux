#!/usr/bin/env python3
"""Bounded boot-area raw capture, retaining the ID-only abort/write deny guard."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
old=root/'.tools/overlays/nand-id'
out=root/'.tools/overlays/nand-raw'
out.mkdir(parents=True,exist_ok=True)
source=root/'.tools/sources/linux-6.12/drivers/mtd/nand/raw'
ids=(source/'nand_ids.c').read_text()
needle='struct nand_flash_dev nand_flash_ids[] = {\n'
assert ids.count(needle)==1
ids=ids.replace(needle,needle+'''
\t/* Exact observed ID; diagnostic raw layout, no ECC claim. */
\t{"Eurocase Toshiba 98de84937257 raw diagnostic",
\t\t{ .id = {0x98, 0xde, 0x84, 0x93, 0x72, 0x57, 0x09, 0x04} },
\t\t SZ_16K, SZ_8K, SZ_4M, 0, 8, 1280, NAND_ECC_INFO(0, 0) },
''',1)
(out/'nand_ids.c').write_text(ids)
core=(old/'nand_base.c').read_text().replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/debugfs.h>')
needle='int nand_scan_with_ids(struct nand_chip *chip, unsigned int maxchips,'
assert core.count(needle)==1
helper=r'''
static struct debugfs_blob_wrapper eurocase_raw_blobs[2];

static int eurocase_capture_boot_raw(struct nand_chip *chip)
{
    static const u8 expected_id[8] = {0x98, 0xde, 0x84, 0x93, 0x72, 0x57, 0x09, 0x04};
    static const char * const names[2] = {"eurocase-nand-boot-raw-a", "eurocase-nand-boot-raw-b"};
    struct mtd_info *mtd = nand_to_mtd(chip);
    const unsigned int stride = 16384 + 1280;
    const unsigned int pages = 128;
    struct dentry *entries[2] = { NULL, NULL };
    unsigned int pass, index;
    int ret = 0;

    if (chip->id.len != 8 || memcmp(chip->id.data, expected_id, 8) ||
        mtd->writesize != 16384 || mtd->oobsize != 1280 ||
        mtd->erasesize != 4194304 || mtd->size != 8589934592ULL)
        return -EINVAL;
    if (eurocase_raw_blobs[0].data || eurocase_raw_blobs[1].data)
        return -EBUSY;
    for (pass = 0; pass < 2; pass++) {
        eurocase_raw_blobs[pass].data = kvzalloc((size_t)pages * stride, GFP_KERNEL);
        eurocase_raw_blobs[pass].size = (size_t)pages * stride;
        if (!eurocase_raw_blobs[pass].data) {
            ret = -ENOMEM;
            goto fail;
        }
    }
    nand_select_target(chip, 0);
    for (pass = 0; pass < 2; pass++) {
        for (index = 0; index < pages; index++) {
            unsigned int row = index < 64 ? index : 256 + index - 64;

            ret = nand_read_page_op(chip, row, 0,
                     (u8 *)eurocase_raw_blobs[pass].data + (size_t)index * stride, stride);
            if (ret) {
                pr_err("EUROCASE_NAND_RAW_ERROR pass=%u row=%u ret=%d\n", pass, row, ret);
                nand_deselect_target(chip);
                goto fail;
            }
        }
    }
    nand_deselect_target(chip);
    for (pass = 0; pass < 2; pass++) {
        entries[pass] = debugfs_create_blob(names[pass], 0400, NULL, &eurocase_raw_blobs[pass]);
        if (IS_ERR_OR_NULL(entries[pass])) {
            ret = -EIO;
            goto fail;
        }
    }
    pr_info("EUROCASE_NAND_RAW_CAPTURE_OK passes=2 records=128 stride=17664 rows=0..63,256..319 bytes_per_pass=2260992 equal=%d\n",
            !memcmp(eurocase_raw_blobs[0].data, eurocase_raw_blobs[1].data,
                    eurocase_raw_blobs[0].size));
    return 0;
fail:
    for (pass = 0; pass < 2; pass++) {
        if (!IS_ERR_OR_NULL(entries[pass]))
            debugfs_remove(entries[pass]);
        kvfree(eurocase_raw_blobs[pass].data);
        eurocase_raw_blobs[pass].data = NULL;
        eurocase_raw_blobs[pass].size = 0;
    }
    return ret;
}

'''
core=core.replace(needle,helper+needle,1)
needle='\t\t/* Deliberately stop before ECC attachment, manufacturer init or BBT. */'
assert core.count(needle)==1
core=core.replace(needle,'''
\t\tif (of_property_read_bool(nand_get_flash_node(chip),
\t\t\t\t\t  "eurocase,boot-raw-capture")) {
\t\t\tret = eurocase_capture_boot_raw(chip);
\t\t\tif (ret)
\t\t\t\tgoto cleanup_ident;
\t\t}
'''+needle,1)
assert core.index('ret = eurocase_capture_boot_raw(chip);') < core.index('\tret = nand_attach(chip);')
(out/'nand_base.c').write_text(core)
driver=(old/'sunxi_nand.c').read_text()
# The generic operation guard remains unchanged and precedes all hardware I/O.
needle='\tif (!check_only)\n\t\tsunxi_nfc_select_chip(nand, op->cs);'
assert driver.count(needle)==1
driver=driver.replace(needle,'''
\tif (!check_only && id_only) {
\t\tstruct sunxi_nfc *nfc = to_sunxi_nfc(nand->controller);
\t\twritel(0, nfc->regs + NFC_REG_ECC_CTL);
\t}
'''+needle,1)
for name in ['sunxi_nfc_hw_ecc_write_chunk','sunxi_nfc_hw_ecc_write_page',
             'sunxi_nfc_hw_ecc_write_subpage','sunxi_nfc_hw_ecc_write_page_dma',
             'sunxi_nfc_hw_ecc_write_oob','sunxi_nfc_write_buf']:
    signature=('static void ' if name=='sunxi_nfc_write_buf' else 'static int ')+name+'('
    start=driver.index(signature)
    body=driver.index('\n\n',driver.index('\n{',start)+2)
    returned='return;' if name=='sunxi_nfc_write_buf' else 'return -EROFS;'
    guard='\n\tif (of_property_read_bool(nand_get_flash_node(nand), "eurocase,read-id-only"))\n\t\t'+returned+'\n'
    driver=driver[:body]+guard+driver[body:]
(out/'sunxi_nand.c').write_text(driver)
print('Generated bounded raw-read overlays with unchanged command deny guard and blocked ECC write callbacks.')
