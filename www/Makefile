export HOST = merlin
export PROJECT = asimov

export PROD = $(HOST):/srv/www/vhosts/zoidtechnologies.com/html/$(PROJECT)/
export STAGE = /srv/www/vhosts/zoidtechnologies.com/html/$(PROJECT)/

export datestamp = $(shell date +%Y%m%d-%H%M)
export archivename = $(PROJECT)-$(datestamp)-$(USER)
export installfile = install --mode=0660

export RSYNC = rsync --delete-after --chmod=Dg=rwxs,Fgu=rw,Fo=r --verbose \
	--archive --update --backup --recursive \
	--human-readable --rsh=ssh \
	--no-owner --no-group --checksum --mkpath

export PROJECTRELEASEDIR = /srv/repo/$(PROJECT)/

export SCSSLOADPATH = --load-path /home/opencode/data/work/zoid6/shared/skin/scss/ --load-path /home/opencode/data/work/zoid6/scss/ --load-path $(HOME)/projects/$(PROJECT)/www/skin/scss/
export SCSS = sass $(SCSSLOADPATH) --sourcemap=none --stop-on-error --trace --style expanded

all:

clean:
	-rm *~
	$(MAKE) -C skin clean
	$(MAKE) -C php clean

prod:
#	mkdir -p $(STAGE)templates_c/
#	chmod g=rwxs $(STAGE)templates_c/

	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	-$(MAKE) -C js stage
	$(RSYNC) config-prod.php $(STAGE)config.php
	$(RSYNC) htaccess-prod $(STAGE).htaccess
	$(RSYNC) --delete-after $(STAGE) $(PROD)
