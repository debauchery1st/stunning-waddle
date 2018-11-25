# KV DS9

*Python3, Buildozer, Kivy*

modeled after the Official Kivy VM 2.0

https://kivy.org/#download

*Always use the official version until you cannot.

Virtual Box 
https://www.virtualbox.org/

 - Create a new virtual machine

   20+GB vmdk storage, 4096+ RAM

 - Install Debian (Stretch) 9.6 (https://www.debian.org/CD/netinst/)

following the installation,
 - install build essentials & kernel headers
        
       su -c "apt install build-essential linux-headers-amd64 linux-headers-$(uname -r)"

[VirtualBox] > [Devices] > [Insert VirtualBox Guest Additions CD Image] 

 - mount the cd,
        
       cd /media/cdrom0;sh ./autorun.sh

 - restart DS9

[VirtualBox] 

Create a shared host folder to automount.

after doing so, 
 -     su -c "addgroup $USER vboxsf"
 -     su -c "mkdir /build;chown $USER.$USER /build"

 - restart DS9
  
install *android dependencies*
   
   
    su -c "apt install -y \
        python3-pip \
        openjdk-8-jdk-headless \
        curl \
        libsdl2-gfx-dev \
        openssl \
        cython \
        virtualenv"


install *kivy dependencies* 

    # Install necessary system packages
    su -c "apt-get install -y \
        python-pip \
        build-essential \
        git \
        python \
        python-dev \
        ffmpeg \
        libsdl2-dev \
        libsdl2-image-dev \
        libsdl2-mixer-dev \
        libsdl2-ttf-dev \
        libportmidi-dev \
        libswscale-dev \
        libavformat-dev \
        libavcodec-dev \
        zlib1g-dev"
    
    # Install gstreamer for audio, video (optional)
    su -c "apt-get install -y \
        libgstreamer1.0 \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good"


install (with pip) Cython, cryptography, and the latest buildozer

    pip3 install sh --user
    pip2 install chardet cryptography Cython==0.25.2 virtualenv
    pip3 install https://github.com/kivy/buildozer/archive/master.zip
    pip3 install Cython==0.25.2
    

**copy source to your shared folder and build.**

    ./android_build.sh

on the first round, buildozer spits out an error.

manually update the "Android SDK Tools" and "Platform-tools"

    ~/.buildozer/android/platform/android-sdk-20/tools/android

clean and build a fresh APK

    ./android_clean.sh
    ./android_build.sh
