#!/usr/bin/env bash
# buildozer needs spec file to clean
cp hack/c.spec buildozer.spec
python3 -m buildozer android clean
rm buildozer.spec
