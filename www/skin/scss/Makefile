all:

# Compile every .scss in this directory into $(SKINDIR)css/. The load path
# is this directory (not the parent's $(HOME)/projects copy) on purpose.
stage:
	sass --load-path /home/opencode/data/work/zoid6/shared/skin/scss/ \
	     --load-path /home/opencode/data/work/bbsengine6/skin/scss/ \
	     --load-path $(CURDIR) \
	     --sourcemap=none --stop-on-error --trace --style expanded \
	     --update .:$(SKINDIR)css/

clean:
	-rm *~ *.css *.css.map

.PHONY: all clean stage
