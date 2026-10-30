# Hardware and support status

## Tested device

| Item | Observation |
| --- | --- |
| Brand/model | Eurocase EUTB_710MDQ |
| Stock product | `polaris_wifionly` / `polaris-wifionly` |
| SoC | Allwinner A23, dual Cortex-A7 |
| RAM | 1 GiB recognized during mainline bring-up |
| Stock software | Android 4.2.2, Linux 3.4.39 |
| Mainline development kernel | Linux 6.12 with local board/driver changes |
| LCD | 1024 × 600, 52 MHz pixel clock |
| Touch | Silead GSL1680, using stock-derived firmware |
| Wi-Fi | Realtek RTL8188EU |
| Power management | AXP223 over RSB |
| Internal flash | Toshiba MLC NAND; stock table indicates 16 KiB pages and 4 MiB blocks |
| Mainline boot medium | microSD |

Identification comes from stock metadata, driver analysis and hardware tests.
The product name alone does not guarantee identical components. Board photos,
PCB markings and a component-identification guide are still needed for a public
hardware revision checklist.

## Validation boundaries

| Feature | Tested result | Remaining limitation |
| --- | --- | --- |
| microSD boot | Autonomous boot; USB may already be connected | One physical unit tested |
| LCD | Stable picture, colors confirmed by user | Local panel driver required |
| Touch | Navigation, filters and scrolling confirmed | Fine edge calibration remains incomplete |
| Home | Returns to summary | No broader key-remapping interface |
| USB | Console and data channels, recovery after restart | Console depends on Linux startup; no early boot visibility |
| Local power controls | UI shutdown/restart validated in the SD development sequence | No claim of optimized suspend or power consumption |
| Wi-Fi | Association, DHCP, DNS and HTTP validated in a separate test | No persistent setup or automatic connection; calibration workaround required |
| Audio | Headphone output audibly confirmed | Integrated speaker silent; cause unresolved |
| Accelerometer | Tilt response observed during bring-up | No dashboard integration |
| Battery/charging | PMIC and voltage readings available | Capacity, charging behavior and long-term thermal behavior not validated |
| Cameras | No completed validation | Unsupported for this project's current purpose |
| NAND installation | No Linux installation performed | No validated complete restore workflow |

## Board-specific decisions

The SD device tree disables UART0 because its PF2/PF4 pin assignment conflicts
with the SD bus. The SD controller uses `broken-cd` polling instead of the
unresolved PB4 card-detect configuration, at a maximum clock of 25 MHz and
without 1.8 V signaling.

The custom display setup includes RGB666 output, PH7 panel enable, PH6 backlight
enable, PWM backlight and a separate PWM VCOM signal on PH1. These details must
be preserved when packaging the kernel patches; a generic A23 device tree does
not describe this board adequately.

The bootloader uses measured stock DRAM parameters including 552 MHz,
ZQ `63351` and ODT enabled. Those values are board-specific. Do not substitute
parameters from an unrelated A23 tablet.

Wi-Fi required stock calibration data as a software eFuse shadow fallback.
No eFuse was programmed. Do not publish a per-device identity as a universal
calibration file or assume all units need identical calibration.
