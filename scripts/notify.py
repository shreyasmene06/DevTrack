#!/usr/bin/env python3
"""
DevTrack Notification Alert Engine
Triggers desktop notifications if the user hasn't satisfied their streak by the reminder hour (default 9:00 PM / 21:00).
Secured with bounded reads, atomic state updates, and argument arrays without shell parsing.
"""

import os
import sys
import json
import tempfile
import subprocess
from datetime import datetime, date

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")
MAX_FILE_BYTES = 1024 * 1024

def secure_read_json(path, max_bytes=MAX_FILE_BYTES):
    if not os.path.exists(path) or os.path.islink(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read(max_bytes)
            if not raw:
                return None
            return json.loads(raw)
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None

def secure_write_json(path, data):
    dir_path = os.path.dirname(os.path.abspath(path))
    if os.path.islink(dir_path):
        return False
    os.makedirs(dir_path, mode=0o700, exist_ok=True)
    
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".tmp_devtrack_")
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return False

def send_notification(title, message, urgency="normal", icon="dialog-warning"):
    try:
        subprocess.run([
            "notify-send",
            "-a", "DevTrack",
            "-u", urgency,
            "-i", icon,
            str(title)[:100],
            str(message)[:250]
        ], check=True, timeout=5)
        return True
    except Exception as e:
        print(f"notify-send failed: {e}", file=sys.stderr)
        return False

def check_and_notify(force=False):
    data = secure_read_json(DATA_PATH)
    if not data:
        return {"status": "no_data"}
        
    config = data.get("config", {})
    reminder = config.get("reminder", {})
    
    if not reminder.get("enabled", True) and not force:
        return {"status": "reminders_disabled"}
        
    today_iso = date.today().isoformat()
    last_notified = str(reminder.get("last_notified_date", ""))
    
    is_done_today = bool(data.get("is_done_today", False))
    streak = int(data.get("composite_streak", 0))
    
    if is_done_today and not force:
        return {"status": "already_done_today"}
        
    now = datetime.now()
    rem_time_str = str(reminder.get("time", "21:00"))
    try:
        rem_hour, rem_minute = map(int, rem_time_str.split(":"))
    except Exception:
        rem_hour, rem_minute = 21, 0
        
    current_minutes = now.hour * 60 + now.minute
    target_minutes = rem_hour * 60 + rem_minute
    
    if force or (current_minutes >= target_minutes and last_notified != today_iso):
        title = f"[DevTrack] Streak Alert ({streak} Day{'s' if streak != 1 else ''})"
        if streak > 0:
            msg = f"It's past {rem_time_str}. No submissions recorded today. Solve a problem on LeetCode / Codeforces or push to GitHub to maintain your {streak}-day streak."
        else:
            msg = f"It's past {rem_time_str}. Start your daily coding streak on LeetCode, Codeforces, or GitHub."
            
        send_notification(title, msg, urgency="critical", icon="dialog-warning")
        
        cfg = secure_read_json(CONFIG_PATH)
        if cfg:
            if "reminder" not in cfg:
                cfg["reminder"] = {}
            cfg["reminder"]["last_notified_date"] = today_iso
            secure_write_json(CONFIG_PATH, cfg)
                
        return {"status": "notified", "streak": streak, "time": now.strftime("%H:%M")}
        
    return {"status": "skipped", "current_time": now.strftime("%H:%M"), "target": rem_time_str}

if __name__ == "__main__":
    force_mode = "--force" in sys.argv or "--test" in sys.argv
    res = check_and_notify(force=force_mode)
    print(json.dumps(res, indent=2))
