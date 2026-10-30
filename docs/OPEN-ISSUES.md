# What remains unknown, incomplete or untested

These categories describe different kinds of uncertainty. A driver registering
successfully is not the same as a physically confirmed feature. A failed test
does not by itself identify its root cause.

## Built-in speaker: tested, unresolved

Headphone output was audibly confirmed by the user. The integrated speaker
remained silent. PCM was RUNNING, DMA pointers advanced, DAC/headphone paths
were enabled and PH9 was high during playback. Those observations show that
software was doing work, not that sound reached the speaker.

Trials included direct stereo DAC output, mixer output, separate left/right
channels, a higher analog level and a final mono route inspired by the vendor
A23 source. None produced audible speaker output. Controls and the temporarily
changed analog routing bits were restored, and no diagnostic playback process
was left running.

The exact routing used by this unit's stock binary was not demonstrated. The
speaker's physical presence, connection and condition were not independently
checked; the owner had not tested sound in Android. We cannot conclude that it
is broken, absent, wired differently or affected by one particular missing bit.

Investigation stopped at the user's request. Any future audible test needs an
explicit request and advance coordination. Do not run tones as part of an
automated build/install procedure. A controlled stock-Android comparison and
physical inspection could provide new evidence; neither has been performed.

## Cameras: not tested

No completed camera bring-up or image-capture test was performed. Sensor
identification, power/reset sequencing, clocks, bus configuration, driver support
and image quality remain unverified. There is no basis to label the cameras
working or broken. Stock detection/configuration entries alone would not prove
which sensors are physically fitted.

## Touch: usable, calibration incomplete

Orientation and practical interaction were confirmed. Edge accuracy remains
imperfect. Manual five-point observations and the difference between vendor and
mainline processing do not establish a precise correction matrix. Application
Y scaling is a workaround, not a completed hardware calibration.

## Wi-Fi: connectivity tested, persistent setup missing

Association and IP connectivity were confirmed with stock-derived calibration
and RAM-only credentials. Stable device identity, credential storage, automatic
startup/reconnection and a configuration UI remain pending. Another unit needs
its own calibration/identity checks rather than a clone of private device data.

## NAND: research reads succeeded, installation unsupported

Physical bootloader recovery succeeded for selected copies. That is not a full
NAND backup, a complete bad-block/ECC/read-retry implementation or a demonstrated
restore procedure. Mainline MLC storage installation remains unresolved. The
working SD port does not require solving it.

## Power, battery and suspend: partial coverage

Orderly UI shutdown and restart were validated. PMIC/voltage readings exist.
Battery capacity accuracy, charging behavior, thermal limits under extended load,
suspend/resume and power optimization were not validated. The cause of an earlier
long-press restart with USB attached was not isolated.

## Reliability and portability: limited coverage

Only one physical tablet was used. A small DRAM window passed patterns; full-RAM
stress and prolonged retention tests were not performed. Long-term unattended
operation and different board revisions are not established. The new self-contained Docker build passed offline checks with a new isolated
cache; its output still needs hardware validation independently of the earlier
installed image. See [build verification](BUILD-VERIFICATION.md).
