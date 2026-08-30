#!/usr/bin/env python3
"""
DevTrack Notification Alert Engine
Triggers desktop notifications if the user hasn't satisfied their streak by the reminder hour (default 9:00 PM / 21:00).
Secured with O_NOFOLLOW file descriptors, atomic tempfile replacement, and oversized payload rejection.
"""

import os
import sys
import json
import stat
import secrets
import tempfile
import subprocess
from datetime import datetime, date

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")
MAX_FILE_BYTES = 1024 * 1024

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
ICON_PATH = os.path.join(PLUGIN_ROOT, "assets", "devtrack.svg")

def get_notification_icon():
    if os.path.exists(ICON_PATH) and not os.path.islink(ICON_PATH):
        return ICON_PATH
    return "dialog-warning"

def secure_read_json(path, max_bytes=MAX_FILE_BYTES):
    """
    Securely reads and parses a JSON file without TOCTOU symlink races or unbounded reads.
    Opens the file with O_NOFOLLOW and O_NONBLOCK, checking S_ISREG and UID, and reads max_bytes + 1.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except (OSError, IOError):
        return None

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            return None
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            os.close(fd)
            return None
        if st.st_size > max_bytes:
            os.close(fd)
            return None
        
        with open(fd, "r", encoding="utf-8", closefd=True) as f:
            raw = f.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return None
            if not raw.strip():
                return None
            return json.loads(raw)
    except Exception:
        return None

def secure_write_json(path, data):
    """
    Securely and atomically writes JSON data to path.
    Verifies directory ownership and O_NOFOLLOW, keeping a verified parent-directory descriptor
    open to perform temporary creation, replacement, and cleanup descriptor-relatively
    without re-resolving the pathname.
    """
    dir_path = os.path.dirname(os.path.abspath(path))
    filename = os.path.basename(path)
    
    try:
        os.makedirs(dir_path, mode=0o700, exist_ok=True)
    except (OSError, IOError):
        return False
        
    dir_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        dir_fd = os.open(dir_path, dir_flags)
    except (OSError, IOError):
        return False
        
    tmp_filename = None
    try:
        st = os.fstat(dir_fd)
        if not stat.S_ISDIR(st.st_mode):
            return False
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            return False
            
        # Create temporary file descriptor-relatively in verified directory
        for _ in range(10):
            candidate = f".tmp_{filename}_{secrets.token_hex(8)}"
            try:
                tmp_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
                tmp_fd = os.open(candidate, tmp_flags, 0o600, dir_fd=dir_fd)
                tmp_filename = candidate
                break
            except FileExistsError:
                continue
        else:
            return False
            
        try:
            with open(tmp_fd, "w", encoding="utf-8", closefd=True) as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.unlink(tmp_filename, dir_fd=dir_fd)
            except OSError:
                pass
            return False

        # Atomically replace target file descriptor-relatively
        os.replace(tmp_filename, filename, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        tmp_filename = None
        return True
    except Exception as e:
        if tmp_filename is not None:
            try:
                os.unlink(tmp_filename, dir_fd=dir_fd)
            except OSError:
                pass
        return False
    finally:
        os.close(dir_fd)

def send_notification(title, message, urgency="normal"):
    icon = get_notification_icon()
    try:
        subprocess.run([
            "notify-send",
            "-a", "DevTrack",
            "-u", urgency,
            "-i", icon,
            str(title)[:100],
            str(message)[:350]
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
        if streak > 0:
            title = "DevTrack · Daily Streak Alert"
            msg = (
                f"<b>{streak}-Day Coding Streak at Risk</b>\n"
                f"It is past {rem_time_str}. No activity recorded today on LeetCode, Codeforces, or GitHub.\n"
                "Solve 1 problem or push a commit to preserve your streak."
            )
        else:
            title = "DevTrack · Coding Reminder"
            msg = (
                "<b>Start Your Coding Streak Today</b>\n"
                f"It is past {rem_time_str}. Solve a problem on LeetCode, Codeforces, or GitHub to begin your streak."
            )
            
        send_notification(title, msg, urgency="critical")
        
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
