TABLET_POC_VERSION = 1
TABLET_POC_SITE = $(BR2_EXTERNAL_TABLET_PATH)/../build
TABLET_POC_SITE_METHOD = local
TABLET_POC_LICENSE = GPL-2.0-or-later
TABLET_POC_DEPENDENCIES = alsa-lib

define TABLET_POC_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) -D_GNU_SOURCE -DPANEL_SD_BOOT -Wall -Wextra -Werror \
		$(@D)/tablet-poc.c $(TARGET_LDFLAGS) -o $(@D)/tablet-poc -lasound -lm
endef

define TABLET_POC_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/tablet-poc $(TARGET_DIR)/usr/bin/tablet-poc
endef

$(eval $(generic-package))
