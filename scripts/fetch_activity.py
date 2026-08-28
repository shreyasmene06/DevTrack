#!/usr/bin/env python3
"""
DevTrack - Activity Fetcher & Streak Engine
Fetches coding activity from LeetCode, Codeforces, and GitHub.
Computes daily activity, streaks, 14-week (98-day) GitHub contribution heatmap, and statistics.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta

CONFIG_DIR = os.path.expanduser("~/.config/omarchy/devtrack")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")

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

def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return DEFAULT_CONFIG

def load_previous_data():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def fetch_url(url, data=None, headers=None, timeout=12):
    req_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def get_local_date_str(ts=None):
    if ts is None:
        return date.today().isoformat()
    return datetime.fromtimestamp(ts).date().isoformat()

# ----------------- LEETCODE -----------------
def fetch_leetcode(username):
    if not username or not username.strip():
        return {"enabled": False, "status": "no_username", "today_count": 0, "streak": 0, "total_solved": 0, "history": {}}
    
    username = username.strip()
    result = {
        "platform": "leetcode",
        "username": username,
        "enabled": True,
        "today_count": 0,
        "streak": 0,
        "total_solved": 0,
        "history": {},
        "recent": [],
        "last_active": None,
        "error": None
    }
    
    query = """
    query userProfile($username: String!) {
      matchedUser(username: $username) {
        username
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        submissionCalendar
        userCalendar {
          streak
          totalActiveDays
        }
      }
      recentAcSubmissionList(username: $username, limit: 20) {
        id
        title
        titleSlug
        timestamp
      }
    }
    """
    try:
        body = json.dumps({"query": query, "variables": {"username": username}}).encode("utf-8")
        raw = fetch_url("https://leetcode.com/graphql", data=body, headers={"Content-Type": "application/json"})
        data = json.loads(raw.decode("utf-8"))
        
        user_data = data.get("data", {}).get("matchedUser")
        if not user_data:
            result["error"] = "User not found"
            return result
        
        stats = user_data.get("submitStats", {}).get("acSubmissionNum", [])
        for item in stats:
            if item.get("difficulty") == "All":
                result["total_solved"] = item.get("count", 0)
        
        cal_str = user_data.get("submissionCalendar")
        today_iso = date.today().isoformat()
        history = {}
        
        if cal_str:
            cal_dict = json.loads(cal_str)
            for ts_str, count in cal_dict.items():
                d_str = get_local_date_str(int(ts_str))
                history[d_str] = history.get(d_str, 0) + int(count)
        
        recent_list = data.get("data", {}).get("recentAcSubmissionList", []) or []
        for sub in recent_list:
            ts = int(sub.get("timestamp", 0))
            d_str = get_local_date_str(ts)
            history[d_str] = max(history.get(d_str, 0), 1)
            result["recent"].append({
                "title": sub.get("title"),
                "timestamp": ts,
                "date": d_str
            })
            if result["last_active"] is None or ts > result["last_active"]:
                result["last_active"] = ts
                
        result["history"] = history
        result["today_count"] = history.get(today_iso, 0)
        
        cur_streak = 0
        check_date = date.today()
        if history.get(check_date.isoformat(), 0) > 0:
            cur_streak += 1
        check_date -= timedelta(days=1)
        while history.get(check_date.isoformat(), 0) > 0:
            cur_streak += 1
            check_date -= timedelta(days=1)
            
        official_streak = user_data.get("userCalendar", {}).get("streak", 0) if user_data.get("userCalendar") else 0
        result["streak"] = max(cur_streak, official_streak)
        
    except Exception as e:
        result["error"] = str(e)
        print(f"LeetCode error: {e}", file=sys.stderr)
        
    return result

# ----------------- CODEFORCES -----------------
def fetch_codeforces(handle):
    if not handle or not handle.strip():
        return {"enabled": False, "status": "no_handle", "today_count": 0, "streak": 0, "rating": 0, "rank": "unrated", "history": {}}
        
    handle = handle.strip()
    result = {
        "platform": "codeforces",
        "username": handle,
        "enabled": True,
        "today_count": 0,
        "streak": 0,
        "rating": 0,
        "rank": "unrated",
        "history": {},
        "recent": [],
        "last_active": None,
        "error": None
    }
    
    today_iso = date.today().isoformat()
    
    try:
        info_raw = fetch_url(f"https://codeforces.com/api/user.info?handles={handle}")
        info_data = json.loads(info_raw.decode("utf-8"))
        if info_data.get("status") == "OK" and info_data.get("result"):
            uinfo = info_data["result"][0]
            result["rating"] = uinfo.get("rating", 0)
            result["rank"] = uinfo.get("rank", "unrated")
            
        sub_raw = fetch_url(f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=100")
        sub_data = json.loads(sub_raw.decode("utf-8"))
        if sub_data.get("status") == "OK":
            history = {}
            for sub in sub_data.get("result", []):
                verdict = sub.get("verdict")
                ts = sub.get("creationTimeSeconds", 0)
                d_str = get_local_date_str(ts)
                if verdict == "OK":
                    history[d_str] = history.get(d_str, 0) + 1
                    prob = sub.get("problem", {})
                    prob_name = f"{prob.get('contestId', '')}{prob.get('index', '')} - {prob.get('name', '')}"
                    result["recent"].append({
                        "title": prob_name,
                        "timestamp": ts,
                        "date": d_str
                    })
                if result["last_active"] is None or ts > result["last_active"]:
                    result["last_active"] = ts
                    
            result["history"] = history
            result["today_count"] = history.get(today_iso, 0)
            
            cur_streak = 0
            check_date = date.today()
            if history.get(check_date.isoformat(), 0) > 0:
                cur_streak += 1
            check_date -= timedelta(days=1)
            while history.get(check_date.isoformat(), 0) > 0:
                cur_streak += 1
                check_date -= timedelta(days=1)
                
            result["streak"] = cur_streak
        else:
            result["error"] = sub_data.get("comment", "API error")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"Codeforces error: {e}", file=sys.stderr)
        
    return result

# ----------------- GITHUB -----------------
def fetch_github(username):
    if not username or not username.strip():
        return {"enabled": False, "status": "no_username", "today_count": 0, "streak": 0, "history": {}}
        
    username = username.strip()
    result = {
        "platform": "github",
        "username": username,
        "enabled": True,
        "today_count": 0,
        "streak": 0,
        "history": {},
        "recent": [],
        "last_active": None,
        "error": None
    }
    
    today_iso = date.today().isoformat()
    
    try:
        events_raw = fetch_url(f"https://api.github.com/users/{username}/events")
        events = json.loads(events_raw.decode("utf-8"))
        
        if isinstance(events, list):
            history = {}
            for ev in events:
                ev_type = ev.get("type")
                created_at_str = ev.get("created_at")
                if not created_at_str:
                    continue
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).astimezone()
                ts = int(dt.timestamp())
                d_str = dt.date().isoformat()
                
                if ev_type in ["PushEvent", "CreateEvent", "PullRequestEvent", "IssuesEvent", "CommitCommentEvent"]:
                    count = 1
                    if ev_type == "PushEvent":
                        commits = ev.get("payload", {}).get("commits", [])
                        count = max(1, len(commits))
                    history[d_str] = history.get(d_str, 0) + count
                    
                    repo_name = ev.get("repo", {}).get("name", "")
                    result["recent"].append({
                        "title": f"{ev_type.replace('Event', '')} in {repo_name}",
                        "timestamp": ts,
                        "date": d_str
                    })
                    if result["last_active"] is None or ts > result["last_active"]:
                        result["last_active"] = ts
                        
            result["history"] = history
            result["today_count"] = history.get(today_iso, 0)
            
            cur_streak = 0
            check_date = date.today()
            if history.get(check_date.isoformat(), 0) > 0:
                cur_streak += 1
            check_date -= timedelta(days=1)
            while history.get(check_date.isoformat(), 0) > 0:
                cur_streak += 1
                check_date -= timedelta(days=1)
                
            result["streak"] = cur_streak
        elif isinstance(events, dict) and "message" in events:
            result["error"] = events.get("message")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"GitHub error: {e}", file=sys.stderr)
        
    return result

# ----------------- AGGREGATOR & 14-WEEK HEATMAP -----------------
def aggregate_activity(config):
    prev_data = load_previous_data() or {}
    platforms_cfg = config.get("platforms", {})
    
    platforms_data = {}
    total_today = 0
    combined_history = {}
    active_platforms_count = 0
    
    # 1. LeetCode
    lc_cfg = platforms_cfg.get("leetcode", {})
    if lc_cfg.get("enabled", True) and lc_cfg.get("username"):
        active_platforms_count += 1
        lc_data = fetch_leetcode(lc_cfg.get("username"))
        if lc_data.get("error") and prev_data.get("platforms", {}).get("leetcode"):
            cached = prev_data["platforms"]["leetcode"]
            lc_data["history"] = cached.get("history", {})
            lc_data["streak"] = cached.get("streak", 0)
            lc_data["today_count"] = cached.get("today_count", 0)
            lc_data["total_solved"] = cached.get("total_solved", 0)
        platforms_data["leetcode"] = lc_data
        for d, c in lc_data.get("history", {}).items():
            combined_history[d] = combined_history.get(d, 0) + c
    else:
        platforms_data["leetcode"] = {"enabled": False, "username": lc_cfg.get("username", "")}
        
    # 2. Codeforces
    cf_cfg = platforms_cfg.get("codeforces", {})
    if cf_cfg.get("enabled", True) and cf_cfg.get("handle"):
        active_platforms_count += 1
        cf_data = fetch_codeforces(cf_cfg.get("handle"))
        if cf_data.get("error") and prev_data.get("platforms", {}).get("codeforces"):
            cached = prev_data["platforms"]["codeforces"]
            cf_data["history"] = cached.get("history", {})
            cf_data["streak"] = cached.get("streak", 0)
            cf_data["today_count"] = cached.get("today_count", 0)
            cf_data["rating"] = cached.get("rating", 0)
            cf_data["rank"] = cached.get("rank", "unrated")
        platforms_data["codeforces"] = cf_data
        for d, c in cf_data.get("history", {}).items():
            combined_history[d] = combined_history.get(d, 0) + c
    else:
        platforms_data["codeforces"] = {"enabled": False, "handle": cf_cfg.get("handle", "")}
        
    # 3. GitHub
    gh_cfg = platforms_cfg.get("github", {})
    if gh_cfg.get("enabled", True) and gh_cfg.get("username"):
        active_platforms_count += 1
        gh_data = fetch_github(gh_cfg.get("username"))
        if gh_data.get("error") and prev_data.get("platforms", {}).get("github"):
            cached = prev_data["platforms"]["github"]
            gh_data["history"] = cached.get("history", {})
            gh_data["streak"] = cached.get("streak", 0)
            gh_data["today_count"] = cached.get("today_count", 0)
        platforms_data["github"] = gh_data
        for d, c in gh_data.get("history", {}).items():
            combined_history[d] = combined_history.get(d, 0) + c
    else:
        platforms_data["github"] = {"enabled": False, "username": gh_cfg.get("username", "")}
        
    today_obj = date.today()
    today_iso = today_obj.isoformat()
    total_today = combined_history.get(today_iso, 0)
    
    # Calculate composite streak
    composite_streak = 0
    check_d = date.today()
    if combined_history.get(check_d.isoformat(), 0) > 0:
        composite_streak += 1
    check_d -= timedelta(days=1)
    while combined_history.get(check_d.isoformat(), 0) > 0:
        composite_streak += 1
        check_d -= timedelta(days=1)
        
    # Calculate longest streak & total active days in history
    longest_streak = 0
    curr_run = 0
    total_active_days_90 = 0
    total_solves_90 = 0
    
    for i in range(120, -1, -1):
        d_check = today_obj - timedelta(days=i)
        iso_c = d_check.isoformat()
        cnt = combined_history.get(iso_c, 0)
        if cnt > 0:
            curr_run += 1
            longest_streak = max(longest_streak, curr_run)
            if i <= 90:
                total_active_days_90 += 1
                total_solves_90 += cnt
        else:
            curr_run = 0
            
    longest_streak = max(longest_streak, composite_streak)
    
    # Build 14-Week GitHub Grid (98 days)
    # Sunday to Saturday columns
    NUM_WEEKS = 14
    current_weekday = (today_obj.weekday() + 1) % 7  # 0=Sunday, 1=Monday... 6=Saturday
    start_of_current_week = today_obj - timedelta(days=current_weekday)
    grid_start = start_of_current_week - timedelta(weeks=NUM_WEEKS - 1)
    
    weeks = []
    month_labels = []
    last_month = None
    
    for w in range(NUM_WEEKS):
        week_days = []
        week_first_day = grid_start + timedelta(days=w*7)
        month_str = week_first_day.strftime("%b")
        if month_str != last_month:
            month_labels.append({"week_idx": w, "month": month_str})
            last_month = month_str
            
        for d in range(7):
            day_cell_date = grid_start + timedelta(days=w*7 + d)
            iso = day_cell_date.isoformat()
            is_future = day_cell_date > today_obj
            count = combined_history.get(iso, 0) if not is_future else 0
            
            level = 0
            if count > 0:
                if count >= 6:
                    level = 4
                elif count >= 4:
                    level = 3
                elif count >= 2:
                    level = 2
                else:
                    level = 1
                    
            cell = {
                "date": iso,
                "formatted_date": day_cell_date.strftime("%d %b %Y"),
                "day_name": day_cell_date.strftime("%a"),
                "month_name": day_cell_date.strftime("%b"),
                "day_num": day_cell_date.day,
                "count": count,
                "level": level,
                "active": count > 0,
                "is_today": (iso == today_iso),
                "is_future": is_future
            }
            week_days.append(cell)
        weeks.append(week_days)
        
    is_done_today = (total_today > 0)
    
    output = {
        "updated_at": int(time.time()),
        "updated_at_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "today_date": today_iso,
        "is_done_today": is_done_today,
        "total_today": total_today,
        "composite_streak": composite_streak,
        "longest_streak": longest_streak,
        "total_active_days_90": total_active_days_90,
        "total_solves_90": total_solves_90,
        "active_platforms_count": active_platforms_count,
        "platforms": platforms_data,
        "weeks": weeks,
        "month_labels": month_labels,
        "config": config
    }
    
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    except Exception as e:
        print(f"Failed to write data: {e}", file=sys.stderr)
        
    return output

if __name__ == "__main__":
    cfg = load_config()
    res = aggregate_activity(cfg)
    print(json.dumps(res))
