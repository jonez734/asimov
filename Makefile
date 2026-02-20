PROJECT = asimov

all:

clean:
	-rm *~

backup:
	rsync --recursive --verbose --exclude=.venv/ . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/
