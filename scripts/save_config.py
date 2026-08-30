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
import secrets
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
