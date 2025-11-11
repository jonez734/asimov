all:

clean:
	-rm *~

install:
	mkdir -p $(DOCROOT)skin/css/
	-$(installfile) *.css $(DOCROOT)skin/css/

release:
	mkdir -p $(PROJECTBUILDDIR)skin/css/
	-$(installfile) Makefile *.css $(PROJECTBUILDDIR)skin/css/
