PROJECT = asimov

all:

clean:
	-rm *~
	find . -name "__pycache__" -type d -exec rm -rf {} +

backup:
	rsync --recursive --verbose --exclude=.venv/ --exclude=__pycache__/ . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/
