#!/bin/bash
# Instalación: sudo bash install.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta: sudo bash install.sh"; exit 1; }
U="${SUDO_USER:?Ejecuta con sudo desde tu usuario}"

apt-get install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 brightnessctl

# Permiso mínimo: solo el fichero wakealarm del RTC, para el grupo "wakelight".
groupadd -f wakelight
usermod -aG wakelight,video "$U"
cat > /etc/udev/rules.d/90-wakelight.rules <<'RULE'
SUBSYSTEM=="rtc", ACTION=="add", RUN+="/bin/chgrp wakelight /sys/class/rtc/%k/wakealarm", RUN+="/bin/chmod 664 /sys/class/rtc/%k/wakealarm"
RULE
udevadm control --reload
udevadm trigger --subsystem-match=rtc --action=add

# App en /opt (propiedad de root, sin escritura para el usuario)
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
Comment=Luz silenciosa para despertar
Exec=/usr/local/bin/wakelight
Icon=weather-clear
Categories=Utility;
DESK
echo "Listo. Cierra sesión y vuelve a entrar (para activar el grupo) y abre WakeLight."
