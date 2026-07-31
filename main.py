"""
Alarm Scheduler - Mobile (Android / iOS) version
==================================================
Same alarm data model & scheduling logic as the Windows desktop app,
rebuilt with Kivy so it can be packaged into a real .apk (Android, via
buildozer) or .ipa (iOS, via kivy-ios on a Mac). tkinter/customtkinter/
pystray/winreg do NOT exist on phones, so this UI layer is a full
rewrite - only scheduler_mobile.py (the alarm logic) is shared.
"""

import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp

from scheduler_mobile import AlarmScheduler

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
             "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}

KV = """
#:import dp kivy.metrics.dp

<AlarmRow>:
    size_hint_y: None
    height: dp(84)
    padding: dp(14), dp(10)
    spacing: dp(12)
    canvas.before:
        Color:
            rgba: 0.114, 0.125, 0.176, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

    BoxLayout:
        orientation: "vertical"
        size_hint_x: 0.62
        Label:
            text: root.time_text
            font_size: dp(26)
            bold: True
            halign: "left"
            valign: "middle"
            text_size: self.size
            color: (1,1,1,1) if root.enabled else (0.55,0.56,0.62,1)
        Label:
            text: root.label_text
            font_size: dp(14)
            halign: "left"
            valign: "middle"
            text_size: self.size
            color: 0.66, 0.68, 0.78, 1
        Label:
            text: root.days_text
            font_size: dp(12)
            halign: "left"
            valign: "middle"
            text_size: self.size
            color: 0.45, 0.47, 0.58, 1

    BoxLayout:
        orientation: "horizontal"
        size_hint_x: 0.38
        spacing: dp(6)
        Switch:
            active: root.enabled
            on_active: root.on_toggle(args[1])
        Button:
            text: "Edit"
            font_size: dp(12)
            background_normal: ""
            background_color: 0.30, 0.31, 0.85, 1
            on_release: root.on_edit()
        Button:
            text: "Del"
            font_size: dp(12)
            background_normal: ""
            background_color: 0.55, 0.16, 0.20, 1
            on_release: root.on_delete()

<AlarmListScreen>:
    BoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: 0.075, 0.082, 0.114, 1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: dp(16), dp(10)
            Label:
                text: "Alarm Scheduler"
                font_size: dp(22)
                bold: True
                halign: "left"
                text_size: self.size

        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: alarm_list
                cols: 1
                spacing: dp(10)
                padding: dp(14), dp(4), dp(14), dp(90)
                size_hint_y: None
                height: self.minimum_height

        FloatLayout:
            size_hint_y: None
            height: 0
            Button:
                text: "+"
                font_size: dp(30)
                size_hint: None, None
                size: dp(62), dp(62)
                pos_hint: {"right": 0.96, "y": 0.06}
                background_normal: ""
                background_color: 0.30, 0.31, 0.85, 1
                on_release: app.open_edit_screen(None)

<AlarmEditScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: 0.075, 0.082, 0.114, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: root.title_text
            font_size: dp(20)
            bold: True
            size_hint_y: None
            height: dp(36)

        BoxLayout:
            size_hint_y: None
            height: dp(70)
            spacing: dp(10)
            Spinner:
                id: hour_spinner
                text: root.hour_text
                values: [f"{h:02d}" for h in range(24)]
                font_size: dp(24)
            Label:
                text: ":"
                font_size: dp(24)
                size_hint_x: None
                width: dp(16)
            Spinner:
                id: minute_spinner
                text: root.minute_text
                values: [f"{m:02d}" for m in range(0, 60, 5)] + ([root.minute_text] if root.minute_text not in [f"{m:02d}" for m in range(0,60,5)] else [])
                font_size: dp(24)

        TextInput:
            id: label_input
            text: root.label_text
            hint_text: "Alarm label (e.g. Take Medicine)"
            multiline: False
            size_hint_y: None
            height: dp(48)
            font_size: dp(16)

        Label:
            text: "Repeat on:"
            size_hint_y: None
            height: dp(24)
            halign: "left"
            text_size: self.size

        GridLayout:
            id: days_grid
            cols: 7
            size_hint_y: None
            height: dp(46)
            spacing: dp(4)

        Label:
            text: "Sound:"
            size_hint_y: None
            height: dp(24)
            halign: "left"
            text_size: self.size

        Spinner:
            id: sound_spinner
            text: root.sound_text
            values: root.sound_names
            size_hint_y: None
            height: dp(46)

        Widget:

        BoxLayout:
            size_hint_y: None
            height: dp(52)
            spacing: dp(10)
            Button:
                text: "Cancel"
                background_normal: ""
                background_color: 0.25, 0.26, 0.32, 1
                on_release: app.close_edit_screen()
            Button:
                text: "Save"
                background_normal: ""
                background_color: 0.30, 0.31, 0.85, 1
                on_release: root.on_save()
"""


class AlarmRow(BoxLayout):
    time_text = StringProperty("")
    label_text = StringProperty("")
    days_text = StringProperty("")
    enabled = BooleanProperty(False)
    alarm_id = StringProperty("")

    def on_toggle(self, active):
        App.get_running_app().toggle_alarm(self.alarm_id, active)

    def on_edit(self):
        App.get_running_app().open_edit_screen(self.alarm_id)

    def on_delete(self):
        App.get_running_app().delete_alarm(self.alarm_id)


class AlarmListScreen(Screen):
    pass


class AlarmEditScreen(Screen):
    title_text = StringProperty("New Alarm")
    hour_text = StringProperty("07")
    minute_text = StringProperty("00")
    label_text = StringProperty("")
    sound_text = StringProperty("Default")
    sound_names = ObjectProperty(["Default"])
    editing_id = StringProperty("")
    selected_days = ObjectProperty(set())

    def on_kv_post(self, base_widget):
        self.rebuild_day_buttons()

    def rebuild_day_buttons(self):
        grid = self.ids.days_grid
        grid.clear_widgets()
        for day in DAYS:
            btn = Button(
                text=DAY_SHORT[day],
                font_size="12sp",
                background_normal="",
                background_color=(0.30, 0.31, 0.85, 1) if day in self.selected_days else (0.18, 0.19, 0.26, 1),
            )
            btn.bind(on_release=lambda b, d=day: self.toggle_day(d))
            grid.add_widget(btn)

    def toggle_day(self, day):
        if day in self.selected_days:
            self.selected_days.discard(day)
        else:
            self.selected_days.add(day)
        self.rebuild_day_buttons()

    def on_save(self):
        app = App.get_running_app()
        time_str = f"{self.ids.hour_spinner.text}:{self.ids.minute_spinner.text}"
        label = self.ids.label_input.text
        days = [d for d in DAYS if d in self.selected_days]
        sound_choice = self.ids.sound_spinner.text
        sound_path = app.sound_map.get(sound_choice, "")
        app.save_alarm(self.editing_id, time_str, days, sound_path, label)


class AlarmSchedulerApp(App):
    def build(self):
        self.title = "Alarm Scheduler"
        Window.clearcolor = (0.075, 0.082, 0.114, 1)

        self.scheduler = AlarmScheduler(config_dir=self.user_data_dir)
        self.sound_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm alert")
        self.sound_map = self._load_sounds()
        self.ringtone = None

        Builder.load_string(KV)
        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(AlarmListScreen(name="list"))
        self.sm.add_widget(AlarmEditScreen(name="edit"))
        self.refresh_list()

        Clock.schedule_interval(self.check_alarms, 1.0)
        return self.sm

    # ---------- sounds ----------
    def _load_sounds(self):
        sounds = {"Default": ""}
        if os.path.isdir(self.sound_dir):
            for fname in sorted(os.listdir(self.sound_dir)):
                if fname.lower().endswith((".mp3", ".wav")):
                    display = os.path.splitext(fname)[0]
                    sounds[display] = os.path.join(self.sound_dir, fname)
        return sounds

    # ---------- list screen ----------
    def refresh_list(self):
        screen = self.sm.get_screen("list")
        grid = screen.ids.alarm_list
        grid.clear_widgets()
        for alarm in sorted(self.scheduler.alarms, key=lambda a: a["time"]):
            days_text = "Every day" if len(alarm["days"]) == 7 else (
                ", ".join(DAY_SHORT[d] for d in alarm["days"]) if alarm["days"] else "One-time"
            )
            row = AlarmRow(
                time_text=alarm["time"],
                label_text=alarm["label"],
                days_text=days_text,
                enabled=alarm["enabled"],
                alarm_id=alarm["id"],
            )
            grid.add_widget(row)

    def toggle_alarm(self, alarm_id, active):
        self.scheduler.toggle_alarm(alarm_id, active)

    def delete_alarm(self, alarm_id):
        self.scheduler.delete_alarm(alarm_id)
        self.refresh_list()

    # ---------- edit screen ----------
    def open_edit_screen(self, alarm_id):
        screen = self.sm.get_screen("edit")
        if alarm_id:
            alarm = next((a for a in self.scheduler.alarms if a["id"] == alarm_id), None)
        else:
            alarm = None

        if alarm:
            screen.title_text = "Edit Alarm"
            screen.editing_id = alarm["id"]
            h, m = alarm["time"].split(":")
            screen.hour_text = h
            screen.minute_text = m
            screen.label_text = alarm["label"]
            screen.selected_days = set(alarm["days"])
            reverse_map = {v: k for k, v in self.sound_map.items()}
            screen.sound_text = reverse_map.get(alarm["sound_path"], "Default")
        else:
            screen.title_text = "New Alarm"
            screen.editing_id = ""
            screen.hour_text = "07"
            screen.minute_text = "00"
            screen.label_text = ""
            screen.selected_days = set()
            screen.sound_text = "Default"

        screen.sound_names = list(self.sound_map.keys())
        screen.rebuild_day_buttons()
        self.sm.current = "edit"

    def close_edit_screen(self):
        self.sm.current = "list"

    def save_alarm(self, alarm_id, time_str, days, sound_path, label):
        if alarm_id:
            self.scheduler.update_alarm(alarm_id, time_str, days, sound_path, label)
        else:
            self.scheduler.add_alarm(time_str, days, sound_path, label)
        self.refresh_list()
        self.sm.current = "list"

    # ---------- alarm firing ----------
    def check_alarms(self, dt):
        active, missed = self.scheduler.check_for_alarms()
        for alarm in active:
            self.fire_alarm(alarm)
        if missed:
            self.show_missed_popup(missed)
            self.refresh_list()

    def fire_alarm(self, alarm):
        self.refresh_list()
        sound_path = alarm.get("sound_path") or ""
        if sound_path and os.path.exists(sound_path):
            self.ringtone = SoundLoader.load(sound_path)
        else:
            # fall back to the first bundled sound
            fallback = next((p for p in self.sound_map.values() if p), None)
            self.ringtone = SoundLoader.load(fallback) if fallback else None
        if self.ringtone:
            self.ringtone.loop = True
            self.ringtone.play()

        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(16))
        content.add_widget(Label(text=alarm["label"], font_size="24sp", bold=True))
        content.add_widget(Label(text=alarm["time"], font_size="40sp"))
        stop_btn = Button(text="Dismiss", size_hint_y=None, height=dp(56),
                           background_normal="", background_color=(0.30, 0.31, 0.85, 1))
        content.add_widget(stop_btn)

        popup = Popup(title="Alarm!", content=content, size_hint=(0.85, 0.5), auto_dismiss=False)

        def dismiss(*_):
            if self.ringtone:
                self.ringtone.stop()
            popup.dismiss()

        stop_btn.bind(on_release=dismiss)
        popup.open()

    def show_missed_popup(self, missed):
        lines = "\n".join(f"- {m['alarm']['label']} ({m['time']})" for m in missed)
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        content.add_widget(Label(text=f"You missed {len(missed)} alarm(s):\n\n{lines}"))
        close_btn = Button(text="OK", size_hint_y=None, height=dp(48))
        content.add_widget(close_btn)
        popup = Popup(title="Missed Alarms", content=content, size_hint=(0.85, 0.5))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    AlarmSchedulerApp().run()
