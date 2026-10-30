# Archive scope and release status

This repository publishes board-support source, research tooling and English
explanations for the Eurocase EUTB_710MDQ. The related application is preserved in
[tablet-proxmox-panel](https://github.com/agugliotta/tablet-proxmox-panel).

Raw acquisitions, private transcripts/inventory, firmware blobs and built images
are excluded. Source/config baselines exported from the original workspace are
under `config-baselines/`; the generated display patch is under `patches/`.
Research scripts retain historical input paths and stages. Personal ADB serials
were replaced with `REPLACE_WITH_YOUR_ADB_SERIAL` in exported tools.

This is a source/research publication, not a validated binary release. The next
reproduction milestone is a clean build using pinned inputs and tracked patches,
without the original Docker volumes or historical image baselines. The tested
local image hashes in the README identify earlier hardware evidence, not
artifacts downloadable from this repository.

No new hardware tests, NAND operations or audio playback are required to publish
this archive. See BUILD.md for remaining dependencies and NOTICE.md at the
repository root for licensing and firmware-distribution boundaries.
