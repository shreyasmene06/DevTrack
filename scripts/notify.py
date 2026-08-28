#!/usr/bin/env python3
"""
DevTrack Notification Alert Engine
Triggers desktop notifications if the user hasn't satisfied their streak by the reminder hour (default 9:00 PM / 21:00).
"""

import os
import sys
import json
import subprocess
from datetime import datetime, date

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")

def send_notification(title, message, urgency="normal", icon="dialog-warning"):
    try:
        subprocess.run([
            "notify-send",
            "-a", "DevTrack",
            "-u", urgency,
            "-i", icon,
            title,
            message
        ], check=True)
        return True
    except Exception as e:
        print(f"notify-send failed: {e}", file=sys.stderr)
        return False

def check_and_notify(force=False):
    if not os.path.exists(DATA_PATH):
        return {"status": "no_data"}
        
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e)}
        
    config = data.get("config", {})
    reminder = config.get("reminder", {})
    
    if not reminder.get("enabled", True) and not force:
        return {"status": "reminders_disabled"}
        
    today_iso = date.today().isoformat()
    last_notified = reminder.get("last_notified_date", "")
    
    is_done_today = data.get("is_done_today", False)
    streak = data.get("composite_streak", 0)
    
    if is_done_today and not force:
        return {"status": "already_done_today"}
        
    now = datetime.now()
    rem_time_str = reminder.get("time", "21:00")
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
        
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "reminder" not in cfg:
                    cfg["reminder"] = {}
                cfg["reminder"]["last_notified_date"] = today_iso
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception as e:
                print(f"Failed to update last_notified_date: {e}", file=sys.stderr)
                
        return {"status": "notified", "streak": streak, "time": now.strftime("%H:%M")}
        
    return {"status": "skipped", "current_time": now.strftime("%H:%M"), "target": rem_time_str}

if __name__ == "__main__":
    force_mode = "--force" in sys.argv or "--test" in sys.argv
    res = check_and_notify(force=force_mode)
    print(json.dumps(res, indent=2))
