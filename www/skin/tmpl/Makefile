all:

clean:
	-rm *~
	$(MAKE) -C sections clean

stage:
	$(RSYNC) *.tmpl sections $(STAGE)skin/tmpl/
