# Archive scope and release status

This repository publishes board-support source, research tooling and English
explanations for the Eurocase EUTB_710MDQ. The related application is preserved in
[tablet-proxmox-panel](https://github.com/agugliotta/tablet-proxmox-panel).

Raw acquisitions, private transcripts/inventory, firmware blobs and built images
are excluded. Source/config baselines exported from the original workspace are
under `config-baselines/`; the generated display patch is under `patches/`.
Historical diagnostic scripts are preserved in the initial commit; the active
tree contains a self-contained `make image` path and only its required tools.
Owner-supplied stock inputs and generated images are ignored by Git.

This is a source/research publication, not a validated binary release. The self-contained Docker build completed without the original Docker volumes
or historical image baselines; see [the build verification](BUILD-VERIFICATION.md).
Hardware validation of the new output and binary-release licensing remain pending. The tested
local image hashes in the README identify earlier hardware evidence, not
artifacts downloadable from this repository.

No new hardware tests, NAND operations or audio playback are required to publish
this archive. See BUILD.md for remaining dependencies and NOTICE.md at the
repository root for licensing and firmware-distribution boundaries.
