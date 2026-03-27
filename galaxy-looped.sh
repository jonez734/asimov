#!/bin/bash
while true; do
  gst-launch-1.0 -e filesrc location=$(pwd)/galaxy-dark-blue-colors-shutterstock.mp4 ! \
    qtdemux name=demux demux.video_0 ! \
    h264parse ! avdec_h264 ! videoconvert ! \
    videorate ! video/x-raw,framerate=30/1 ! \
    x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! \
    rtph264pay ! udpsink host=127.0.0.1 port=5000
  sleep 0.1
done
