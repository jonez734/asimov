== overview ==

- "Any Technology, Suffeciently Advanced, is Indistinguishable from Magic" -- Asimov
- I am building a telestage (jitsi, chime, zoom, etc) for use in tutorials and in magic
- dxf file is readable by the open-source 'librecad' tool, which ships with fedora.

== cameras ==

- 3x usb camera for video
- 1x object/motion detecting camera
  * lightning from fingertips
  * flames
  * plasma
- willing to wear thimbles but would like to avoid it
- usb hub
- controlling: https://www.omgubuntu.co.uk/2022/12/cameractrls-webcam-settings-app-for-linux

- green screen behind chair, draped over chair, and on table
- lighting is critical for green screen!
- no wrinkles in screens, shadows, leakage
- touch sensitive performance pad: visual effect when cards are placed on it
- all green screens are to be machine washable
- scrim

- overhead camera, plugged into a laptop/pi, that detects card position on a greenscreen, and also can tell when a finger is within one of those cards.  idea is to highlight the card pointed to by the performer and have it outline the card or trigger 3d effects (opengl+blender?)
- would also be nice to trigger a sound cue

== install ==

dnf install python3.10
python3.10 -m venv ./asimovenv
source asimovenv/bin/activate
pip install mediapipe
(asimovenv) jam@minotaur:~/projects/asimov$ pip show mediapipe
Name: mediapipe
Version: 0.10.21
Summary: MediaPipe is the simplest way for researchers and developers to build world-class ML solutions and applications for mobile, edge, cloud and the web.
Home-page: https://github.com/google/mediapipe
Author: The MediaPipe Authors
Author-email: mediapipe@google.com
License: Apache 2.0
Location: /home/jam/projects/asimov/src/asimov/asimovenv/lib/python3.10/site-packages
Requires: absl-py, attrs, flatbuffers, jax, jaxlib, matplotlib, numpy, opencv-contrib-python, protobuf, sentencepiece, sounddevice

$ sudo dnf install python3-opencv # error about package conflict:
$ sudo dnf remove postgresql-private-devel-16.8-1.fc41.x86_64
$ sudo dnf install python3-opencv
$ pip install bbsengine6-202505272022-py3-none-any.whl

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install psycopg
Collecting psycopg
  Downloading psycopg-3.2.9-py3-none-any.whl.metadata (4.5 kB)
Collecting typing-extensions>=4.6 (from psycopg)
  Downloading typing_extensions-4.13.2-py3-none-any.whl.metadata (3.0 kB)
Downloading psycopg-3.2.9-py3-none-any.whl (202 kB)
Downloading typing_extensions-4.13.2-py3-none-any.whl (45 kB)
Installing collected packages: typing-extensions, psycopg
Successfully installed psycopg-3.2.9 typing-extensions-4.13.2

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install psycopg_pool
Collecting psycopg_pool
  Using cached psycopg_pool-3.2.6-py3-none-any.whl.metadata (2.6 kB)
Requirement already satisfied: typing-extensions>=4.6 in ./asimov/asimovenv/lib/python3.10/site-packages (from psycopg_pool) (4.13.2)
Using cached psycopg_pool-3.2.6-py3-none-any.whl (38 kB)
Installing collected packages: psycopg_pool
Successfully installed psycopg_pool-3.2.6

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install pyopengl
Collecting pyopengl
  Downloading PyOpenGL-3.1.9-py3-none-any.whl.metadata (3.3 kB)
Downloading PyOpenGL-3.1.9-py3-none-any.whl (3.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.2/3.2 MB 25.5 MB/s eta 0:00:00
Installing collected packages: pyopengl
Successfully installed pyopengl-3.1.9

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install numpy
Requirement already satisfied: numpy in ./asimov/asimovenv/lib/python3.10/site-packages (1.26.4)

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install flask
Collecting flask
  Downloading flask-3.1.1-py3-none-any.whl.metadata (3.0 kB)
Collecting blinker>=1.9.0 (from flask)
  Downloading blinker-1.9.0-py3-none-any.whl.metadata (1.6 kB)
Collecting click>=8.1.3 (from flask)
  Downloading click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting itsdangerous>=2.2.0 (from flask)
  Downloading itsdangerous-2.2.0-py3-none-any.whl.metadata (1.9 kB)
Collecting jinja2>=3.1.2 (from flask)
  Downloading jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting markupsafe>=2.1.1 (from flask)
  Downloading MarkupSafe-3.0.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.0 kB)
Collecting werkzeug>=3.1.0 (from flask)
  Downloading werkzeug-3.1.3-py3-none-any.whl.metadata (3.7 kB)
Downloading flask-3.1.1-py3-none-any.whl (103 kB)
Downloading blinker-1.9.0-py3-none-any.whl (8.5 kB)
Downloading click-8.2.1-py3-none-any.whl (102 kB)
Downloading itsdangerous-2.2.0-py3-none-any.whl (16 kB)
Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
Downloading MarkupSafe-3.0.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (20 kB)
Downloading werkzeug-3.1.3-py3-none-any.whl (224 kB)
Installing collected packages: markupsafe, itsdangerous, click, blinker, werkzeug, jinja2, flask
Successfully installed blinker-1.9.0 click-8.2.1 flask-3.1.1 itsdangerous-2.2.0 jinja2-3.1.6 markupsafe-3.0.2 werkzeug-3.1.3

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install glfw
Collecting glfw
  Downloading glfw-2.9.0-py2.py27.py3.py30.py31.py32.py33.py34.py35.py36.py37.py38.p39.p310.p311.p312.p313-none-manylinux_2_28_x86_64.whl.metadata (5.4 kB)
Downloading glfw-2.9.0-py2.py27.py3.py30.py31.py32.py33.py34.py35.py36.py37.py38.p39.p310.p311.p312.p313-none-manylinux_2_28_x86_64.whl (243 kB)
Installing collected packages: glfw
Successfully installed glfw-2.9.0

(asimovenv) jam@minotaur:~/projects/asimov/src$ pip install cvzone
Collecting cvzone
  Downloading cvzone-1.6.1.tar.gz (25 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting opencv-python (from cvzone)
  Downloading opencv_python-4.11.0.86-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (20 kB)
Requirement already satisfied: numpy in ./asimov/asimovenv/lib/python3.10/site-packages (from cvzone) (1.26.4)
Downloading opencv_python-4.11.0.86-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (63.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 63.0/63.0 MB 57.1 MB/s eta 0:00:00
Building wheels for collected packages: cvzone
  Building wheel for cvzone (pyproject.toml) ... done
  Created wheel for cvzone: filename=cvzone-1.6.1-py3-none-any.whl size=26328 sha256=ed3cb1390e8abd241f992736ec8072c87318c68052598867bcd0ea44540d2db5
  Stored in directory: /home/jam/.cache/pip/wheels/2c/9f/b3/92e945ac4a71bf727a92463f38155cc5a4fa49c5010b38ec4c
Successfully built cvzone
Installing collected packages: opencv-python, cvzone
Successfully installed cvzone-1.6.1 opencv-python-4.11.0.86
