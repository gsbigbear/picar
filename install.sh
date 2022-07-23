#!/bin/bash
apt-get update --allow-releaseinfo-change
apt-get upgrade -y
apt-get install -y build-essential python3 python3-dev python3-pip python3-virtualenv python3-numpy python3-picamera python3-pandas python3-rpi.gpio i2c-tools avahi-utils joystick libopenjp2-7-dev libtiff5-dev gfortran libatlas-base-dev libopenblas-dev libhdf5-serial-dev libgeos-dev git ntp
apt-get install -y libilmbase-dev libopenexr-dev libgstreamer1.0-dev libjasper-dev libwebp-dev libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev libqtgui4 libqt4-test
apt-get install -y tmux mplayer
cd /home/pi
python3 -m virtualenv -p python3 env --system-site-packages
echo "source ~/env/bin/activate" >> ~/.bashrc
source ~/.bashrc
git clone https://github.com/autorope/donkeycar
cd donkeycar
git fetch --all --tags
git checkout 4.3.6-17-g5143794
pip install -e .[pi]
pip install https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.2.0/tensorflow-2.2.0-cp37-none-linux_armv7l.whl
cd /home/pi
git clone https://github.com/gsbigbear/picar.git
