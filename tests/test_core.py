import json
import stat
from datetime import datetime

from wakelight import core


def test_clean_rejects_garbage():
    p = core.Profile(wake_time="25:99", mode="x", color="red; rm -rf", brightness=9999,
                     ramp_min=-5, hold_min="a", suspend_after="yes").clean()
    assert (p.wake_time, p.mode, p.color) == ("11:00", "solid", "#FFB46B")
    assert (p.brightness, p.ramp_min, p.hold_min, p.suspend_after) == (100, 0, 120, True)


def test_load_bad_and_roundtrip(tmp_path, monkeypatch):
    f = tmp_path / "wl" / "config.json"
    monkeypatch.setattr(core, "CONFIG_DIR", f.parent)
    monkeypatch.setattr(core, "CONFIG_FILE", f)
    assert core.load_profile() == core.Profile()
    core.save_profile(core.Profile(wake_time="09:15", mode="sunrise"))
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert core.load_profile().wake_time == "09:15"
    f.write_text("[1, 2]")
    assert core.load_profile() == core.Profile()
    f.write_text(json.dumps({"color": "#zzzzzz", "extra": 1}))
    assert core.load_profile().color == "#FFB46B"


def test_next_wake():
    now = datetime(2026, 10, 5, 10, 0).timestamp()
    assert core.next_wake("11:00", now) == int(datetime(2026, 10, 5, 11, 0).timestamp())
    assert core.next_wake("09:00", now) == int(datetime(2026, 10, 6, 9, 0).timestamp())


def test_light_modes():
    solid = core.Profile(mode="solid", color="#FF8000")
    assert core.light_at(solid, 0) == (255, 128, 0)
    assert core.total_seconds(solid) == 120 * 60
    fade = core.Profile(mode="fade", color="#FF8000", ramp_min=10)
    assert core.light_at(fade, 300) == (128, 64, 0)
    assert core.light_at(fade, 99999) == (255, 128, 0)
    sun = core.Profile(mode="sunrise", ramp_min=10)
    assert core.light_at(sun, 0) == (12, 0, 0)
    assert core.light_at(sun, 600) == (255, 244, 229)
