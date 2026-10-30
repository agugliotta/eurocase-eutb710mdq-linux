# SPDX-License-Identifier: GPL-2.0-or-later
.DEFAULT_GOAL := image
.PHONY: image test help
image:
	sh build.sh
test:
	python3 -m unittest discover -s tools/build -p 'test_*.py' -v
help:
	@echo 'make image  Build dist/sdcard.img in Docker (requires firmware/ inputs)'
	@echo 'make test   Run offline build-tool checks (requires Python 3)'
