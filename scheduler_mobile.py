"""
scheduler_mobile.py
====================
Same alarm-scheduling logic as the Windows app's scheduler.py, ported to be
platform-independent (no hard-coded relative paths) so it works on Android/iOS
where the app only has write access to its own private data directory.
"""

import os
import json
import logging
import datetime
import uuid
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("AlarmScheduler")


class AlarmScheduler:
    def __init__(self, config_dir: str):
        """config_dir: a writable directory (on mobile, pass App.user_data_dir)."""
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, "alarms_config.json")
        self.alarms: List[Dict] = []
        self.last_checked: Optional[datetime.datetime] = None
        self.load_config()

    def load_config(self) -> None:
        initialize_defaults = False

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.alarms = data.get("alarms", [])
                    if not self.alarms:
                        initialize_defaults = True
                    else:
                        last_checked_str = data.get("last_checked")
                        if last_checked_str:
                            self.last_checked = datetime.datetime.fromisoformat(last_checked_str)
                        else:
                            self.last_checked = datetime.datetime.now()
            except Exception as e:
                logger.error(f"Failed to load config: {e}. Reinitializing default state.")
                initialize_defaults = True
        else:
            initialize_defaults = True

        if initialize_defaults:
            self._initialize_default_state()
        else:
            logger.info(f"Successfully loaded {len(self.alarms)} alarms from config.")

    def _initialize_default_state(self) -> None:
        logger.info("Initializing configuration with default pre-set alarms.")
        self.alarms = [
            {
                "id": str(uuid.uuid4()),
                "time": "07:00",
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "sound_path": "",
                "label": "Morning Walk / Routine",
                "enabled": False,
                "last_triggered": None,
            },
            {
                "id": str(uuid.uuid4()),
                "time": "13:30",
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "sound_path": "",
                "label": "Lunch Reminder",
                "enabled": False,
                "last_triggered": None,
            },
            {
                "id": str(uuid.uuid4()),
                "time": "21:00",
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "sound_path": "",
                "label": "Drink Water / Take Medicine",
                "enabled": False,
                "last_triggered": None,
            },
        ]
        self.last_checked = datetime.datetime.now()
        self.save_config()

    def save_config(self) -> None:
        temp_file = f"{self.config_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "alarms": self.alarms,
                        "last_checked": self.last_checked.isoformat() if self.last_checked else None,
                    },
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            os.rename(temp_file, self.config_file)
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def add_alarm(self, time_str: str, days: List[str], sound_path: str, label: str) -> Dict:
        alarm = {
            "id": str(uuid.uuid4()),
            "time": time_str,
            "days": days,
            "sound_path": sound_path,
            "label": label.strip() or "Untitled Alarm",
            "enabled": True,
            "last_triggered": None,
        }
        self.alarms.append(alarm)
        self.save_config()
        logger.info(f"Added new alarm: {alarm['label']} scheduled at {time_str}")
        return alarm

    def update_alarm(self, alarm_id: str, time_str: str, days: List[str], sound_path: str, label: str) -> bool:
        for alarm in self.alarms:
            if alarm["id"] == alarm_id:
                alarm["time"] = time_str
                alarm["days"] = days
                alarm["sound_path"] = sound_path
                alarm["label"] = label.strip() or "Untitled Alarm"
                alarm["last_triggered"] = None
                self.save_config()
                logger.info(f"Updated alarm ID {alarm_id} to time {time_str}, label '{alarm['label']}'")
                return True
        return False

    def delete_alarm(self, alarm_id: str) -> bool:
        initial_count = len(self.alarms)
        self.alarms = [a for a in self.alarms if a["id"] != alarm_id]
        success = len(self.alarms) < initial_count
        if success:
            self.save_config()
            logger.info(f"Deleted alarm ID: {alarm_id}")
        return success

    def toggle_alarm(self, alarm_id: str, enabled: bool) -> None:
        for alarm in self.alarms:
            if alarm["id"] == alarm_id:
                alarm["enabled"] = enabled
                if enabled:
                    alarm["last_triggered"] = None
                logger.info(f"Toggled alarm '{alarm['label']}' to {'ENABLED' if enabled else 'DISABLED'}")
                break
        self.save_config()

    def check_for_alarms(self) -> Tuple[List[Dict], List[Dict]]:
        now = datetime.datetime.now()
        active_triggered = []
        missed_triggered = []

        if not self.last_checked:
            self.last_checked = now
            self.save_config()
            return active_triggered, missed_triggered

        time_gap_seconds = (now - self.last_checked).total_seconds()
        is_gap_detected = time_gap_seconds > 10.0

        enabled_alarms = [a for a in self.alarms if a["enabled"]]
        current_time_str = now.strftime("%H:%M")
        current_day_name = now.strftime("%A")
        today_date_str = now.strftime("%Y-%m-%d")

        if is_gap_detected:
            start_range = self.last_checked
            if time_gap_seconds > 86400:
                start_range = now - datetime.timedelta(days=1)
                logger.warning(f"Large time gap detected ({time_gap_seconds:.1f}s). Capping missed check to last 24h.")
            else:
                logger.info(f"Time gap detected ({time_gap_seconds:.1f}s). Checking for missed alarms.")

            check_time = start_range.replace(second=0, microsecond=0)
            end_range = (now - datetime.timedelta(seconds=5)).replace(second=0, microsecond=0)

            missed_map = {}
            while check_time <= end_range:
                day_name = check_time.strftime("%A")
                time_str = check_time.strftime("%H:%M")

                for alarm in enabled_alarms:
                    if alarm["time"] == time_str:
                        if not alarm["days"] or day_name in alarm["days"]:
                            run_date_str = check_time.strftime("%Y-%m-%d")
                            if not alarm["days"]:
                                if not alarm["last_triggered"]:
                                    missed_map[alarm["id"]] = (alarm, check_time)
                            else:
                                if alarm["last_triggered"] != run_date_str:
                                    missed_map[alarm["id"]] = (alarm, check_time)

                check_time += datetime.timedelta(minutes=1)

            for alarm_id, (alarm, missed_dt) in missed_map.items():
                missed_triggered.append({
                    "alarm": alarm,
                    "time": missed_dt.strftime("%Y-%m-%d %I:%M %p"),
                })
                if not alarm["days"]:
                    alarm["enabled"] = False
                    alarm["last_triggered"] = missed_dt.isoformat()
                else:
                    alarm["last_triggered"] = missed_dt.strftime("%Y-%m-%d")
                logger.warning(f"Missed Alarm Detected: '{alarm['label']}' scheduled for {alarm['time']} ran at {missed_dt}")

        for alarm in enabled_alarms:
            if alarm["time"] == current_time_str:
                if not alarm["days"] or current_day_name in alarm["days"]:
                    if not alarm["days"]:
                        if not alarm["last_triggered"]:
                            active_triggered.append(alarm)
                            alarm["enabled"] = False
                            alarm["last_triggered"] = now.isoformat()
                            logger.info(f"One-time alarm triggered: '{alarm['label']}'")
                    else:
                        if alarm["last_triggered"] != today_date_str:
                            active_triggered.append(alarm)
                            alarm["last_triggered"] = today_date_str
                            logger.info(f"Recurring alarm triggered: '{alarm['label']}'")

        self.last_checked = now
        self.save_config()

        return active_triggered, missed_triggered
