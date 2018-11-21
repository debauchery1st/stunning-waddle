#!/usr/bin/env bash

pip3 install --upgrade pip;pip3 install Cython==0.25.2;pip3 install -r requirements.txt
echo ""
echo "BUILDING APK..."
echo ""
cp a.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo ""
echo "BUILDING with TWISTED... (expected to fail)"
echo ""
cp b.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo ""
echo "BUILDING with TWISTED & ANDROID (this one should pass)"
echo ""
cp c.spec buildozer.spec
python3 -m buildozer android debug
rm buildozer.spec

echo ""
echo "DONE"
echo ""

# adb logcat *:S python:D
