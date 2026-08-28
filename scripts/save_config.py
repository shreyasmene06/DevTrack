#!/usr/bin/env python3
"""
DevTrack Config Saver
Validates, sanitizes, and atomically persists DevTrack configuration to ~/.config/omarchy/devtrack/config.json
Secured with O_NOFOLLOW file descriptors, atomic tempfile replacement, and oversized payload rejection.
"""

import os
import sys
import json
import re
import stat
import tempfile

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
MAX_FILE_BYTES = 1024 * 1024

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{0,64}$")
TIME_PATTERN = re.compile(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")

DEFAULT_CONFIG = {
    "platforms": {
        "leetcode": {
            "enabled": True,
            "username": ""
        },
        "codeforces": {
            "enabled": True,
            "handle": ""
        },
        "github": {
            "enabled": True,
            "username": ""
        }
    },
    "reminder": {
        "enabled": True,
        "time": "21:00",
        "last_notified_date": ""
    },
    "general": {
        "sync_interval_minutes": 15,
        "mode": "any"
    }
}

def sanitize_str(s, max_len=64):
    if not isinstance(s, str):
        return ""
    clean = s.strip()[:max_len]
    if USERNAME_PATTERN.match(clean):
        return clean
    return ""

def sanitize_time(t):
    if not isinstance(t, str):
        return "21:00"
    t_clean = t.strip()
    if TIME_PATTERN.match(t_clean):
        return t_clean
    return "21:00"

def secure_read_json(path, max_bytes=MAX_FILE_BYTES):
    """
    Securely reads and parses a JSON file without TOCTOU symlink races or unbounded reads.
    Opens the file with O_NOFOLLOW and reads max_bytes + 1 to strictly reject oversized files.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
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
    Verifies directory ownership and O_NOFOLLOW to avoid symlink redirection.
    """
    dir_path = os.path.dirname(os.path.abspath(path))
    
    try:
        os.makedirs(dir_path, mode=0o700, exist_ok=True)
    except (OSError, IOError):
        return False
        
    try:
        dir_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
        dir_fd = os.open(dir_path, dir_flags)
        try:
            st = os.fstat(dir_fd)
            if hasattr(os, "getuid") and st.st_uid != os.getuid():
                return False
        finally:
            os.close(dir_fd)
    except (OSError, IOError):
        return False

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".tmp_devtrack_")
    except (OSError, IOError):
        return False

    try:
        with open(tmp_fd, "w", encoding="utf-8", closefd=True) as f:
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
            except OSError:
                pass
        print(f"Error writing {path}: {e}", file=sys.stderr)
        return False

def save_config(new_cfg_dict):
    current = secure_read_json(CONFIG_PATH) or DEFAULT_CONFIG.copy()
    
    platforms = new_cfg_dict.get("platforms", {})
    
    lc = platforms.get("leetcode", {})
    lc_user = sanitize_str(lc.get("username", ""))
    current["platforms"]["leetcode"] = {
        "enabled": bool(lc.get("enabled", True) and len(lc_user) > 0),
        "username": lc_user
    }
    
    cf = platforms.get("codeforces", {})
    cf_handle = sanitize_str(cf.get("handle", ""))
    current["platforms"]["codeforces"] = {
        "enabled": bool(cf.get("enabled", True) and len(cf_handle) > 0),
        "handle": cf_handle
    }
    
    gh = platforms.get("github", {})
    gh_user = sanitize_str(gh.get("username", ""))
    current["platforms"]["github"] = {
        "enabled": bool(gh.get("enabled", True) and len(gh_user) > 0),
        "username": gh_user
    }
    
    rem = new_cfg_dict.get("reminder", {})
    if "reminder" not in current:
        current["reminder"] = {}
    current["reminder"]["enabled"] = bool(rem.get("enabled", True))
    current["reminder"]["time"] = sanitize_time(rem.get("time", "21:00"))
    
    if secure_write_json(CONFIG_PATH, current):
        print(json.dumps({"status": "success", "config": current}))
        return True
    else:
        print(json.dumps({"status": "error", "message": "Failed to save configuration"}))
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            raw_input = sys.argv[1][:16384]
            payload = json.loads(raw_input)
            save_config(payload)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)[:100]}))
            sys.exit(1)
    else:
        print(json.dumps({"status": "error", "message": "No payload provided"}))
        sys.exit(1)
