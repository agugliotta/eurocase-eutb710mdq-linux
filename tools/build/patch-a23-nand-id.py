#!/usr/bin/env python3
"""Generate an identification-only NAND diagnostic overlay, never edit upstream."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
source=root/'.tools/sources/linux-6.12/drivers/mtd/nand/raw'
out=root/'.tools/overlays/nand-id'
out.mkdir(parents=True,exist_ok=True)
core=(source/'nand_base.c').read_text()
needle='\tret = nand_attach(chip);\n'
assert core.count(needle)==1
core=core.replace(needle,'''\tif (of_property_read_bool(nand_get_flash_node(chip),
\t\t\t\t  "eurocase,read-id-only")) {
\t\tstruct mtd_info *mtd = nand_to_mtd(chip);

\t\tpr_info("EUROCASE_NAND_ID_ONLY_OK id=%*ph size=%llu page=%u oob=%u erase=%u\\n",
\t\t\tchip->id.len, chip->id.data,
\t\t\t(unsigned long long)mtd->size, mtd->writesize,
\t\t\tmtd->oobsize, mtd->erasesize);
\t\t/* Deliberately stop before ECC attachment, manufacturer init or BBT. */
\t\tret = -ECANCELED;
\t\tgoto cleanup_ident;
\t}

'''+needle,1)
(out/'nand_base.c').write_text(core)
driver=(source/'sunxi_nand.c').read_text()
start=driver.index('static int sunxi_nfc_exec_op(')
end=driver.index('\nstatic const struct nand_controller_ops',start)
old=driver[start:end]
new=old.replace('\tconst struct nand_op_parser *parser;','''\tconst struct nand_op_parser *parser;
\tbool id_only = of_property_read_bool(nand_get_flash_node(nand),
\t\t\t\t\t     "eurocase,read-id-only");
\tunsigned int i;
\tint ret;

\tif (id_only) {
\t\tfor (i = 0; i < op->ninstrs; i++) {
\t\t\tconst struct nand_op_instr *instr = &op->instrs[i];

\t\t\tif (instr->type == NAND_OP_DATA_OUT_INSTR)
\t\t\t\treturn -EROFS;
\t\t\tif (instr->type != NAND_OP_CMD_INSTR)
\t\t\t\tcontinue;
\t\t\tswitch (instr->ctx.cmd.opcode) {
\t\t\tcase NAND_CMD_RESET:
\t\t\tcase NAND_CMD_READID:
\t\t\tcase NAND_CMD_PARAM:
\t\t\tcase NAND_CMD_STATUS:
\t\t\tcase NAND_CMD_GET_FEATURES:
\t\t\tcase NAND_CMD_READ0:
\t\t\tcase NAND_CMD_READSTART:
\t\t\tcase NAND_CMD_RNDOUT:
\t\t\tcase NAND_CMD_RNDOUTSTART:
\t\t\t\tbreak;
\t\t\tdefault:
\t\t\t\treturn -EROFS;
\t\t\t}
\t\t}
\t}''',1)
needle='\treturn nand_op_parser_exec_op(nand, parser, op, check_only);'
assert new.count(needle)==1
new=new.replace(needle,'''\tret = nand_op_parser_exec_op(nand, parser, op, check_only);
\tif (!ret && !check_only && id_only && op->ninstrs &&
\t    op->instrs[0].type == NAND_OP_CMD_INSTR &&
\t    op->instrs[0].ctx.cmd.opcode == NAND_CMD_READID) {
\t\tfor (i = 0; i < op->ninstrs; i++) {
\t\t\tif (op->instrs[i].type == NAND_OP_DATA_IN_INSTR)
\t\t\t\tpr_info("EUROCASE_NAND_READID %*ph\\n",
\t\t\t\t\tmin_t(unsigned int, op->instrs[i].ctx.data.len, 16),
\t\t\t\t\top->instrs[i].ctx.data.buf.in);
\t\t}
\t}
\treturn ret;''',1)
assert old!=new
(out/'sunxi_nand.c').write_text(driver[:start]+new+driver[end:])
assert core.index('EUROCASE_NAND_ID_ONLY_OK') < core.index('\tret = nand_attach(chip);')
print('Generated ID-only NAND overlays; upstream unchanged.')
