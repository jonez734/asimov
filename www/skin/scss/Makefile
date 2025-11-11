all:

.scss.css:
	$(SCSS) $< $@

stage: 
	$(SCSS) --update --watch .:$(STAGE)skin/css/

clean:
	-rm *~ *.css *.css.map

.SUFFIXES: .scss .css
