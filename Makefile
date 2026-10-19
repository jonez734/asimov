PROJECT = asimov
VERSION = $(shell date +%Y%m%d%H%M)

PYTHON ?= python3

all:

clean:
	-rm *~
	find . -name "__pycache__" -type d -exec rm -rf {} +

version:
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > src/$(PROJECT)/_version.py
	@echo '__datestamp__ = "$(VERSION)"' >> src/$(PROJECT)/_version.py
	@echo '__githash__ = "'`git log -1 --format='%H' 2>/dev/null | cut -c 1-16`'"' >> src/$(PROJECT)/_version.py
	@cat src/$(PROJECT)/_version.py

build: version
	$(PYTHON) -m build --outdir dist

# deploy: web tree only. The Python wheel is not needed for the vhost, so
# `build` is intentionally not a prerequisite here.
deploy:
	$(MAKE) -C www prod

backup:
	rsync --recursive --verbose --exclude=.venv/ --exclude=__pycache__/ . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/

.PHONY: all clean version build deploy backup
