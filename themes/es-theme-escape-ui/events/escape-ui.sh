#!/bin/sh
# escape/UI: draw art for new collections and games in the background (ES event script)
G=/userdata/themes/es-theme-escape-ui/tool/gen.py
L=/userdata/system/configs/escape-ui/gen.log
[ -f "$G" ] || exit 0
mkdir -p "$(dirname "$L")"
# keep the log small: the last 200 lines once it passes 100 KB
if [ -f "$L" ] && [ "$(wc -c < "$L")" -gt 102400 ]; then tail -n 200 "$L" > "$L.tmp" && mv "$L.tmp" "$L"; fi
nohup python3 "$G" --event >> "$L" 2>&1 &
exit 0
