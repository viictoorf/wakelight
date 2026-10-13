# WakeLight

Despertador **silencioso**: el portátil se suspende y, a la hora fijada, se enciende solo y muestra una luz
(color fijo, brillo progresivo o amanecer simulado) el tiempo que quieras. Para Ubuntu (GNOME), GTK4 + libadwaita.

## Instalar
```
sudo bash install.sh
```
Cierra sesión y vuelve a entrar (se añade tu usuario al grupo `wakelight`). Luego abre **WakeLight**.
Antes de fiarte, usa **Probar ahora**, y prueba un despertar real con una hora a 3 minutos.

## Modos
- **Color fijo**: pantalla de un color durante X minutos.
- **Brillo progresivo**: del negro al color elegido en X minutos, y luego fijo.
- **Amanecer**: rojo oscuro → naranja → blanco cálido ("sol completo") y se mantiene.

`Esc` cierra la pantalla de luz en cualquier momento.

## Seguridad
- No ejecuta nada como root ni abre red. La instalación solo da al grupo `wakelight` permiso de escritura
  sobre `/sys/class/rtc/rtcN/wakealarm` (programar el despertar).
- Sin `shell=True`: los comandos externos (`brightnessctl`, `systemctl suspend`) se llaman con listas de argumentos.
- La configuración (`~/.config/wakelight/config.json`, permisos 600) se valida al leerla: tipos, rangos,
  formato de hora y de color. Un fichero corrupto o manipulado vuelve a los valores por defecto.
- El despertar se limita a las próximas 36 h. La app vive en `/opt/wakelight`, sin escritura para el usuario.

## Límites conocidos
Depende de que el RTC del portátil pueda despertarlo (probado con `sudo rtcwake -m mem -s 120`).
El brillo por hardware requiere `brightnessctl`; si no funciona, la luz se muestra igual por software.
Pensado para GNOME/Wayland o X11; otros escritorios no están probados.

## Tests
```
pip install pytest && python3 -m pytest
```
