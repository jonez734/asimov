$ sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-41.noarch.rpm
$ sudo dnf install kmod-v4l2loopback
$ python -m venv $HOME/projects/asimov/.venv
$ source $HOME/projects/asimov/.venv/bin/activate
$ sudo dnf install python3.10 # mediapipe restriction. concurrent install with system version
$ sudo dnf install opencv
$ pip install pyvirtualcam mediapipe

$ sudo dnf install v4l-utils
$ v4l2-ctl --list-devices
$ v4l2-ctl --device=/dev/video0 --list-formats-ext # optional

$ sudo usermod -aG video `whoami` # add 'video' group to current user; note the 'a' option for append

(asimovenv) jam@minotaur:~/projects/asimov/src$ groups
jam : jam wheel video repo www
