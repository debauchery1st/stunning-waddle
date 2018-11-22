#!/usr/bin/env bash

echo "creating ICON/SPLASH hack"
cp -r data .data

pip3 install --upgrade pip;pip3 install Cython==0.25.2;pip3 install -r requirements.txt
echo ""
echo "BUILDING APK..."
echo ""
cp hack/a.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo ""
echo "BUILDING with TWISTED... (expected to fail)"
echo ""
cp hack/b.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo ""
echo "BUILDING with TWISTED & ANDROID (this one should pass)"
echo ""
cp hack/c.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo "removing ICON/SPLASH hack"
rm -rf .data

echo ""
echo "DONE"
echo ""

#!/usr/bin/env bash
echo "# example client
a work in progress

####android build environment
" > README.md
python3 --version >> README.md
lsb_release -ds >> README.md

# adb logcat *:S python:D
