#!/usr/bin/env python3
"""
DevTrack Config Updater
Updates ~/.config/omarchy/devtrack/config.json with values passed via JSON or arguments.
"""

import os
import sys
import json

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def update_config(payload):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
            
    if "platforms" not in cfg:
        cfg["platforms"] = {}
        
    if "platforms" in payload:
        for p, val in payload["platforms"].items():
            if p not in cfg["platforms"]:
                cfg["platforms"][p] = {}
            cfg["platforms"][p].update(val)
            
    if "reminder" in payload:
        if "reminder" not in cfg:
            cfg["reminder"] = {}
        cfg["reminder"].update(payload["reminder"])
        
    if "general" in payload:
        if "general" not in cfg:
            cfg["general"] = {}
        cfg["general"].update(payload["general"])
        
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        
    return cfg

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_json = sys.argv[1]
        try:
            parsed = json.loads(raw_json)
            updated = update_config(parsed)
            print(json.dumps({"status": "success", "config": updated}))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps({"status": "error", "message": "No JSON provided"}), file=sys.stderr)
        sys.exit(1)
