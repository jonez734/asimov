export HOST = merlin
export PROJECT = asimov

export PROD = $(HOST):/srv/www/vhosts/zoidtechnologies.com/html/$(PROJECT)/
export STAGE = /srv/www/vhosts/zoidtechnologies.com/html/$(PROJECT)/
export SKINDIR = $(STAGE)skin/

export datestamp = $(shell date +%Y%m%d-%H%M)
export archivename = $(PROJECT)-$(datestamp)-$(USER)
export installfile = install --mode=0660

export RSYNC = rsync --delete-after --chmod=Dg=rwxs,Fgu=rw,Fo=r --verbose \
	--archive --update --backup --recursive \
	--human-readable --rsh=ssh \
	--no-owner --no-group --times --checksum --mkpath

export PROJECTRELEASEDIR = /srv/repo/$(PROJECT)/

export SCSSLOADPATH = --load-path /home/opencode/data/work/zoid6/shared/skin/scss/ --load-path $(HOME)/projects/$(PROJECT)/www/skin/scss/
export SCSS = sass $(SCSSLOADPATH) --sourcemap=none --stop-on-error --trace --style expanded

all:

clean:
	-rm *~
	$(MAKE) -C skin clean
	$(MAKE) -C php clean

# stage: build the vhost tree under $(STAGE) on this host.
stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(RSYNC) config-prod.php $(STAGE)config.php
	$(RSYNC) htaccess-prod $(STAGE).htaccess

# prod: stage, then push the whole tree to $(HOST). RSYNC already carries
# --delete-after, so the push removes remote files that are not in $(STAGE).
prod: stage
	$(RSYNC) $(STAGE) $(PROD)

.PHONY: all clean stage prod
