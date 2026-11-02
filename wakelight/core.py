"""WakeLight core: validated configuration, light calculations, and system calls.
Independent of GTK, so it can be tested without a graphical interface."""

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "wakelight"
CONFIG_FILE = CONFIG_DIR / "config.json"
MODES = ("solid", "fade", "sunrise")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_AHEAD = 36 * 3600  # Wake-ups cannot be scheduled more than 36 hours ahead.

# Sunrise: (position 0..1, RGB color). The final stage represents "full sun".
SUNRISE = [
    (0.0, (12, 0, 0)),
    (0.25, (120, 25, 0)),
    (0.5, (255, 110, 20)),
    (0.8, (255, 190, 110)),
    (1.0, (255, 244, 229)),
]


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


@dataclass
class Profile:
    wake_time: str = "11:00"
    mode: str = "solid"          # solid | fade | sunrise
    color: str = "#FFB46B"
    brightness: int = 60         # Screen brightness percentage when the light turns on.
    ramp_min: int = 20           # Transition duration in minutes (fade / sunrise).
    hold_min: int = 120          # Duration in minutes at full brightness.
    suspend_after: bool = True

    def clean(self) -> "Profile":
        d = Profile()
        return Profile(
            wake_time=self.wake_time if isinstance(self.wake_time, str) and _TIME.match(self.wake_time) else d.wake_time,
            mode=self.mode if self.mode in MODES else d.mode,
            color=self.color if isinstance(self.color, str) and _HEX.match(self.color) else d.color,
            brightness=_clamp(self.brightness, 5, 100, d.brightness),
            ramp_min=_clamp(self.ramp_min, 0, 120, d.ramp_min),
            hold_min=_clamp(self.hold_min, 1, 720, d.hold_min),
            suspend_after=self.suspend_after if isinstance(self.suspend_after, bool) else d.suspend_after,
        )


def load_profile() -> Profile:
    try:
        if CONFIG_FILE.stat().st_size > 10_000:
            return Profile()
        raw = json.loads(CONFIG_FILE.read_text())
        known = {f.name for f in fields(Profile)}
        return Profile(**{k: v for k, v in raw.items() if k in known}).clean()
    except (OSError, ValueError, AttributeError, TypeError):
        return Profile()


def save_profile(p: Profile) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(p.clean()), indent=2))
    tmp.chmod(0o600)
    os.replace(tmp, CONFIG_FILE)


def next_wake(hhmm: str, now: float | None = None) -> int:
    """Return the next occurrence of the specified time (today if more than 30 seconds away, otherwise tomorrow)."""
    ref = datetime.fromtimestamp(now) if now is not None else datetime.now()
    h, m = map(int, hhmm.split(":"))
    t = ref.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= ref + timedelta(seconds=30):
        t += timedelta(days=1)
    return int(t.timestamp())


def ramp_seconds(p: Profile) -> int:
    return 0 if p.mode == "solid" else p.ramp_min * 60


def total_seconds(p: Profile) -> int:
    return ramp_seconds(p) + p.hold_min * 60


def hex_to_rgb(h: str):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _sunrise(x: float):
    for (x0, c0), (x1, c1) in zip(SUNRISE, SUNRISE[1:]):
        if x <= x1:
            k = (x - x0) / (x1 - x0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return SUNRISE[-1][1]


def light_at(p: Profile, t: float):
    """Return the RGB color to display t seconds after the light sequence begins."""
    ramp = ramp_seconds(p)
    x = 1.0 if ramp == 0 else max(0.0, min(1.0, t / ramp))
    if p.mode == "sunrise":
        return _sunrise(x)
    r, g, b = hex_to_rgb(p.color)
    f = x if p.mode == "fade" else 1.0
    return (round(r * f), round(g * f), round(b * f))


# --- System integration (no shell, no root) -----------------------------------------


def _rtc_path():
    for p in sorted(Path("/sys/class/rtc").glob("rtc*/wakealarm")):
        return p
    return None


def set_wake_alarm(epoch: int):
    """Schedule a wake-up by writing to the RTC. Returns (success, message)."""
    p = _rtc_path()
    if p is None:
        return False, "No RTC clock was found on this device."
    if not os.access(p, os.W_OK):
        return False, "No RTC permission. Run install.sh and restart your session."
    now = int(time.time())
    if not now < int(epoch) <= now + MAX_AHEAD:
        return False, "Time is outside the allowed range."
    try:
        with open(p, "w") as f:
            f.write("0\n")
        with open(p, "w") as f:
            f.write(f"{int(epoch)}\n")
    except OSError as e:
        return False, f"Could not schedule the wake-up: {e}"
    return True, ""


def clear_wake_alarm() -> None:
    p = _rtc_path()
    if p and os.access(p, os.W_OK):
        try:
            with open(p, "w") as f:
                f.write("0\n")
        except OSError:
            pass


def backlight_get():
    exe = shutil.which("brightnessctl")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-m"], capture_output=True, text=True, timeout=5).stdout
        return int(out.split(",")[3].strip().rstrip("%"))
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def backlight_set(pct: int) -> None:
    exe = shutil.which("brightnessctl")
    if exe:
        try:
            subprocess.run([exe, "set", f"{int(pct)}%"], capture_output=True, timeout=5)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass


def suspend() -> None:
    subprocess.Popen([shutil.which("systemctl") or "/usr/bin/systemctl", "suspend"])
