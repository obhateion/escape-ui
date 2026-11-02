#!/bin/bash
# escape-UI: settings of the escape/UI theme
T=/userdata/themes/es-theme-escape-ui/tool
mkdir -p /userdata/system/configs/escape-ui
cd "$T" && python3 "$T/app.py" > /userdata/system/configs/escape-ui/app.log 2>&1
sync
