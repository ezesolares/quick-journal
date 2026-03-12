#!/bin/bash
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0

# Sometimes QT needs an explicit push to use Wayland or XCB fallback
# export QT_QPA_PLATFORM="wayland;xcb"

/home/scofmb/.pyenv/versions/.venv/bin/python /home/scofmb/src/project/test/opendeck-journal/diario_pro.py "$@"
