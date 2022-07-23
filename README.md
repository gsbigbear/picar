# picar

using donkeycar v4.3.18 ...

    cd /home/pi
    git clone https://github.com/autorope/donkeycar
    cd donkeycar
    git fetch --all --tags
    git checkout 4.3.18
    pip install -e .[pi]
    pip install https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.2.0/tensorflow-2.2.0-cp37-none-linux_armv7l.whl
