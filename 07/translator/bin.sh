#!/bin/bash
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
FILEPATH="$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
(cd $SCRIPTPATH/.. && python3 translator/main.py $FILEPATH)