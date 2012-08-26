#!/bin/bash

########################## START INSTALLATION ################################

#define constants
SCRIPT_NAME=`basename "$0"`
SCRIPT_PATH=${0%`basename "$0"`}

    echo "Installing plugin locally"
    PLUGIN_PATH="/home/${USER}/.local/share/rhythmbox/plugins/smallwindow/"
    
    #build the dirs
    mkdir -p $PLUGIN_PATH

    #copy the files
    cp -r "${SCRIPT_PATH}"* "$PLUGIN_PATH"
    
    #remove the install script from the dir (not needed)
    rm "${PLUGIN_PATH}${SCRIPT_NAME}"

echo "Finished installing the plugin. Enjoy :]"

