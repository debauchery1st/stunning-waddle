#!/usr/bin/env bash

if [ ! -d ${PWD}/venv ]; then
    echo "[requires python virtual environment.]"
    sudo apt-get install -y python3-venv
    echo "[CREATING VIRTUAL ENVIRONMENT]"
    python3 -m venv ./venv
    source ./venv/bin/activate
    pip install --upgrade pip;pip install Cython==0.29;pip install -r requirements.txt
else
    echo "Activating Virtual Environment."
    source ./venv/bin/activate
fi

echo "Running Server. [CTRL-C to exit]"
python client.py $1 $2 $3
