# WakeLight

A **silent alarm clock**: your laptop suspends and automatically wakes up at the scheduled time, displaying a light (solid color, gradual brightness increase, or simulated sunrise) for as long as you want. Designed for Ubuntu (GNOME), using GTK4 + libadwaita.

## Installation

```bash
sudo bash install.sh
```

Log out and log back in (your user is added to the `wakelight` group). Then launch **WakeLight**.

Before relying on it, use **Test Now** and perform a real wake-up test by scheduling it for 3 minutes later.

## Modes

- **Solid Color**: Displays a single color for a specified number of minutes.
- **Gradual Brightness**: Gradually transitions from black to the selected color over a specified duration, then stays on.
- **Sunrise**: Transitions from dark red → orange → warm white ("full sun") and stays on.

Press `Esc` to close the light screen at any time.

## Security

- Does not run anything as root or access the network. Installation only grants the `wakelight` group write permission to `/sys/class/rtc/rtcN/wakealarm` (to schedule wake-ups).
- No `shell=True`: external commands (`brightnessctl`, `systemctl suspend`) are executed using argument lists.
- Configuration (`~/.config/wakelight/config.json`, permissions 600) is validated when loaded: types, ranges, time format, and color format. Corrupted or tampered files are reset to default values.
- Wake-up scheduling is limited to the next 36 hours. The application runs from `/opt/wakelight`, which is not writable by regular users.

## Known Limitations

Wake-up functionality depends on the laptop's RTC being able to wake the system (tested with `sudo rtcwake -m mem -s 120`).

Hardware brightness control requires `brightnessctl`. If it is unavailable or does not work, the light will still be displayed using software rendering.

Designed for GNOME/Wayland or X11. Other desktop environments have not been tested.

## Tests

```bash
pip install pytest && python3 -m pytest
```
