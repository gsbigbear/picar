# picar

### Flash OS
[Raspbian buster](https://downloads.raspberrypi.org/raspios_oldstable_lite_armhf/images/raspios_oldstable_lite_armhf-2021-12-02/2021-12-02-raspios-buster-armhf-lite.zip)

### Wifi & ssh

Add ssh file on /boot
   
Add wpa_supplicant.conf on /boot

    country=FR
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    network={
        ssid="ssid"
        psk="key"
    }
   
### Configure ssh on linux

Add alias in /etc/hosts

   sudo nano /etc/hosts
   
   192.168.0.88   picar

   ssh-copy-id picar@pi
   
   raspberry


### Configure
sudo raspi-config

    enable camera + i2c + expand filesystem

### Install :

    wget -O - https://raw.githubusercontent.com/gsbigbear/picar/main/install.sh | sudo bash
