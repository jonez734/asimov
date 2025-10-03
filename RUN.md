# run asimov

$ sudo modprobe -r v4l2loopback
$ sudo modprobe v4l2loopback devices=2 video_nr=10,11 card_label="asimov.cam0","obs.vcam" exclusive_caps=1
$ cd ~/projects/asimov/
$ source .venv/bin/activate
$ cd src
$ python -m asimov

# second terminal
$ journalctl -f -t asimov

# obs: optional
# select video source 'asimov.cam0'
# start virtual camera
$ obs &

# start chime/jit.si/etc
# select obs.vcam as video source
