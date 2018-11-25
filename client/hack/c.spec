[app]
title = LanCat
package.name = LanCat
package.domain = org.test
source.dir = .

source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,images/*.png,data/*.png
# (str) Presplash of the application
presplash.filename = %(source.dir)sdata/icon.png
# (str) Icon of the application
icon.filename = %(source.dir)sdata/icon.png

# first build : requirements=incremental,kivy
# second build : requirements=incremental,kivy,twisted

requirements = incremental,kivy,twisted,jnius,android


# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

#
# Android specific
#

# (str) Application versioning (method 2)
version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/main.py

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

android.permissions = INTERNET, WAKE_LOCK, CAMERA, VIBRATE, ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, SEND_SMS, CALL_PRIVILEGED, CALL_PHONE
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86
android.arch = armeabi-v7a


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 1

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer
build_dir = /build/LanCat

