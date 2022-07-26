#!/bin/bash
sudo apt-get update --allow-releaseinfo-change
sudo apt-get upgrade -y
sudo apt-get install -y build-essential python3 python3-dev python3-pip python3-virtualenv python3-numpy python3-picamera python3-pandas python3-rpi.gpio i2c-tools avahi-utils joystick libopenjp2-7-dev libtiff5-dev gfortran libatlas-base-dev libopenblas-dev libhdf5-serial-dev libgeos-dev git ntp
sudo apt-get install -y libilmbase-dev libopenexr-dev libgstreamer1.0-dev libjasper-dev libwebp-dev libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev libqtgui4 libqt4-test
sudo apt-get install -y tmux mplayer python3-opencv
cd /home/pi
python3 -m virtualenv -p python3 env --system-site-packages
echo "source ~/env/bin/activate" >> ~/.bashrc
. ~/env/bin/activate
git clone https://github.com/autorope/donkeycar
cd donkeycar
git fetch --all --tags
git checkout 4.3.6-17-g5143794
pip3 install https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.2.0/tensorflow-2.2.0-cp37-none-linux_armv7l.whl 
pip3 install -e .[pi] 
cd /home/pi
pip3 install adafruit-circuitpython-ina219
git clone https://github.com/gsbigbear/picar.git
cd picar
mkdir models
mkdir data
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0
echo "Need a reboot to apply i2c & cam"
