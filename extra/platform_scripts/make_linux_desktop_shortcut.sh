#!/bin/bash

# This script creates a desktop shortcut for the Reductus server.
# The shortcut will be created in the user's desktop directory.
# the executable path is in 'env/bin/python'

# Get the user's desktop directory
desktop_dir=~/Desktop

# Get the path to the bumps webview server
script_dir=$(realpath $(dirname $0))

# Create the desktop shortcut
echo "[Desktop Entry]
Name=Reductus-Server
Comment=Start the reductus server
Exec='$script_dir/env/bin/python' -m reductus.web_gui.run
Icon=$script_dir/share/icons/reductus_logo.svg
Terminal=true
Type=Application
Categories=Development;
" > $desktop_dir/ReductusServer.desktop

# Make the desktop shortcut executable
chmod +x $desktop_dir/ReductusServer.desktop
