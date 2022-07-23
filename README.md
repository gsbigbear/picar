# picar

using donkeycar v4.3.18 ...


> git clone https://github.com/autorope/donkeycar
cd donkeycar
git fetch --all --tags
latestTag=$(git describe --tags `git rev-list --tags --max-count=1`)
git checkout $latestTag
pip install -e .[pi]
pip install https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.2.0/tensorflow-2.2.0-cp37-none-linux_armv7l.whl
