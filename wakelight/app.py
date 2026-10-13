"""Interfaz GTK4 + libadwaita de WakeLight."""
import sys
import time
from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from . import core  # noqa: E402

_provider = Gtk.CssProvider()


def _css(text: str) -> None:
    try:
        _provider.load_from_string(text)
    except AttributeError:  # GTK < 4.12
        _provider.load_from_data(text.encode())


def _paint(rgb) -> None:
    _css("window.wl-light { background-color: rgb(%d,%d,%d); }" % rgb)


class LightWindow(Gtk.Window):
    """Pantalla completa: negra mientras espera, luego muestra la luz. Esc la cierra."""

    def __init__(self, app, main, p, target, arm=True):
        super().__init__(application=app)
        self.app, self.main, self.p, self.target, self.arm = app, main, p, target, arm
        self.started, self.cookie, self.prev, self.done = None, 0, None, False
        self.add_css_class("wl-light")
        self.set_cursor_from_name("none")
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)
        self.connect("close-request", self._on_close)
        _paint((0, 0, 0))
        self.fullscreen()
        GLib.timeout_add(500, self._tick)

    def _on_key(self, _c, keyval, *_):
        if keyval == Gdk.KEY_Escape:
            if self.arm:
                core.clear_wake_alarm()
            self.close()
            return True
        return False

    def _on_close(self, *_):
        self._release()
        _paint((0, 0, 0))
        self.main.present()
        return False

    def _release(self):
        self.done = True
        if self.cookie:
            self.app.uninhibit(self.cookie)
            self.cookie = 0
        if self.prev is not None:
            core.backlight_set(self.prev)
            self.prev = None

    def _begin(self):
        self.prev = core.backlight_get()
        core.backlight_set(self.p.brightness)
        self.cookie = self.app.inhibit(self, Gtk.ApplicationInhibitFlags.IDLE, "Luz de despertar")

    def _tick(self):
        if self.done:
            return False
        now = time.time()
        if self.started is None:
            if now < self.target:
                return True
            self.started = self.target
            self._begin()
        t = now - self.started
        if t >= core.total_seconds(self.p):
            self._release()
            _paint((0, 0, 0))
            if self.p.suspend_after:
                core.suspend()
            return False
        _paint(core.light_at(self.p, t))
        return True


def _spin(lo, hi, value):
    s = Gtk.SpinButton.new_with_range(lo, hi, 1)
    s.set_value(value)
    s.set_valign(Gtk.Align.CENTER)
    return s


def _row(title, *widgets, subtitle=None):
    r = Adw.ActionRow(title=title)
    if subtitle:
        r.set_subtitle(subtitle)
    for w in widgets:
        w.set_valign(Gtk.Align.CENTER)
        r.add_suffix(w)
    return r


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="WakeLight", default_width=420, default_height=760)
        self.app = app
        p = core.load_profile()

        self.hour = _spin(0, 23, int(p.wake_time[:2]))
        self.minute = _spin(0, 59, int(p.wake_time[3:]))
        for s in (self.hour, self.minute):
            s.connect("output", lambda w: (w.set_text(f"{int(w.get_value()):02d}"), True)[1])
        self.mode = Adw.ComboRow(title="Modo", model=Gtk.StringList.new(["Color fijo", "Brillo progresivo", "Amanecer"]))
        self.mode.set_selected(core.MODES.index(p.mode))
        self.color = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(p.color)
        self.color.set_rgba(rgba)
        self.brightness = _spin(5, 100, p.brightness)
        self.ramp = _spin(0, 120, p.ramp_min)
        self.hold = _spin(1, 720, p.hold_min)
        self.suspend = Gtk.Switch(active=p.suspend_after)

        wake = Adw.PreferencesGroup(title="Despertar")
        wake.add(_row("Hora", self.hour, Gtk.Label(label=":"), self.minute))
        light = Adw.PreferencesGroup(title="Luz")
        self.color_row = _row("Color", self.color)
        self.ramp_row = _row("Transición", self.ramp, subtitle="Minutos hasta llegar a la luz completa")
        light.add(self.mode)
        light.add(self.color_row)
        light.add(_row("Brillo de pantalla", self.brightness, subtitle="Porcentaje del brillo del portátil"))
        light.add(self.ramp_row)
        light.add(_row("Luz completa", self.hold, subtitle="Minutos con la luz fija"))
        end = Adw.PreferencesGroup(title="Al terminar")
        end.add(_row("Suspender el equipo", self.suspend))
        self.mode.connect("notify::selected", self._sync)
        self._sync()

        self.status = Gtk.Label(wrap=True, css_classes=["dim-label"])
        go = Gtk.Button(label="Activar luz", css_classes=["suggested-action", "pill"])
        go.connect("clicked", self._activate)
        test = Gtk.Button(label="Probar ahora", css_classes=["pill"])
        test.connect("clicked", self._test)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for w in (wake, light, end, go, test, self.status):
            page.append(w)
        clamp = Adw.Clamp(maximum_size=480, margin_start=16, margin_end=16, margin_top=12, margin_bottom=24, child=page)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(Adw.HeaderBar())
        outer.append(Gtk.ScrolledWindow(vexpand=True, child=clamp))
        self.set_content(outer)

    def _sync(self, *_):
        i = self.mode.get_selected()
        self.color_row.set_visible(i != 2)
        self.ramp_row.set_visible(i != 0)

    def _collect(self):
        c = self.color.get_rgba()
        return core.Profile(
            wake_time=f"{self.hour.get_value_as_int():02d}:{self.minute.get_value_as_int():02d}",
            mode=core.MODES[self.mode.get_selected()],
            color="#%02X%02X%02X" % tuple(round(v * 255) for v in (c.red, c.green, c.blue)),
            brightness=self.brightness.get_value_as_int(),
            ramp_min=self.ramp.get_value_as_int(),
            hold_min=self.hold.get_value_as_int(),
            suspend_after=self.suspend.get_active(),
        ).clean()

    def _activate(self, *_):
        p = self._collect()
        core.save_profile(p)
        target = core.next_wake(p.wake_time)
        ok, msg = core.set_wake_alarm(target)
        if not ok:
            self.status.set_text(msg)
            return
        LightWindow(self.app, self, p, target).present()
        self.set_visible(False)
        GLib.timeout_add_seconds(2, self._suspend)

    @staticmethod
    def _suspend():
        core.suspend()
        return False

    def _test(self, *_):
        p = self._collect()
        core.save_profile(p)
        LightWindow(self.app, self, replace(p, suspend_after=False), time.time(), arm=False).present()
        self.set_visible(False)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.wakelight.App")

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        MainWindow(self).present()


def main():
    sys.exit(App().run(sys.argv))
