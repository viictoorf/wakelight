```bash
#!/bin/bash
# Installation: sudo bash install.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run: sudo bash install.sh"; exit 1; }
U="${SUDO_USER:?Run with sudo from your regular user account}"

apt-get install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 brightnessctl

# Minimum required permissions: access only to the RTC wakealarm file
# for the "wakelight" group.
groupadd -f wakelight
usermod -aG wakelight,video "$U"

cat > /etc/udev/rules.d/90-wakelight.rules <<'RULE'
SUBSYSTEM=="rtc", ACTION=="add", RUN+="/bin/chgrp wakelight /sys/class/rtc/%k/wakealarm", RUN+="/bin/chmod 664 /sys/class/rtc/%k/wakealarm"
RULE

udevadm control --reload
udevadm trigger --subsystem-match=rtc --action=add

# Install the application in /opt (root-owned, not writable by regular users).
rm -rf /opt/wakelight && install -d -m 755 /opt/wakelight
cp -r "$(dirname "$0")/wakelight" /opt/wakelight/
find /opt/wakelight -name __pycache__ -prune -exec rm -rf {} +
chmod -R go-w /opt/wakelight

printf '#!/bin/sh\ncd /opt/wakelight && exec python3 -m wakelight\n' > /usr/local/bin/wakelight
chmod 755 /usr/local/bin/wakelight

cat > /usr/share/applications/wakelight.desktop <<'DESK'
[Desktop Entry]
Type=Application
Name=WakeLight
Comment=Silent wake-up light
Exec=/usr/local/bin/wakelight
Icon=weather-clear
Categories=Utility;
DESK

echo "Done. Log out and log back in to activate the new group membership, then launch WakeLight."
```
