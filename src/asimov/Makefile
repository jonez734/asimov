VERSION ?= $(shell date +%Y%m%d%H%M)
GITHASH := $(shell git log -1 --format='%H' 2>/dev/null | cut -c 1-16)

all:

clean:
	-rm *~
	make -C io clean
	make -C base clean
	make -C modules clean
	make -C net clean
	make -C playingcard clean

version:
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > $(CURDIR)/_version.py
	@echo 'githash = "$(GITHASH)"' >> $(CURDIR)/_version.py
	@echo 'datestamp = "$(VERSION)"' >> $(CURDIR)/_version.py
	@cat $(CURDIR)/_version.py

build: version
	python -m build
