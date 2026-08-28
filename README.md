# DevTrack: Omarchy Coding Activity & Streak Tracker

A native **Omarchy Quattro** shell plugin for tracking daily coding activity and streaks across **LeetCode**, **Codeforces**, and **GitHub**. It displays your live streak directly in your Omarchy top bar, renders a 14-week contribution heatmap in an interactive popout dashboard, and provides automated evening reminders if your daily streak is pending.

---

## Features

- **Top Bar Status Widget**: Displays your composite streak on your Omarchy bar with real-time indicators for today's active completion status.
- **Multi-Platform Support**:
  - **LeetCode**: Problems solved today, acceptance counts, total solved, and streak.
  - **Codeforces**: Accepted submissions today, current rating, rank badge, and streak.
  - **GitHub**: Daily commit/push/PR activity and public contribution streak.
- **14-Week Contribution Heatmap**: High-density activity matrix with hover tooltips displaying exact dates and contribution counts.
- **Automated Evening Reminders**: Proactive desktop notifications at your configured reminder hour (default 21:00) if no activity has been logged.
- **In-Panel Settings Interface**: Configure your usernames and reminder preferences directly from the popout dashboard.
- **Background Synchronization**: Headless synchronization service running every 15 minutes with local disk caching (`~/.config/omarchy/devtrack/data.json`).

---

## Installation

Clone or link the repository to your Omarchy plugins directory:

```bash
# Clone into plugins directory
git clone https://github.com/shreyasmene06/DevTrack.git ~/.config/omarchy/plugins/devtrack.streak

# Enable in Omarchy
omarchy plugin enable devtrack.streak

# Rescan shell plugins
omarchy-shell shell rescanPlugins
```

---

## Commands & IPC

```bash
# Open or close the details panel
omarchy-shell devtrack.streak toggle

# Trigger an immediate background synchronization
omarchy-shell devtrack.streak refresh

# Validate plugin manifest
omarchy plugin validate /path/to/DevTrack
```

---

## Configuration

You can configure your platform usernames through the in-panel settings interface (click the settings icon in the panel header) or by modifying `~/.config/omarchy/devtrack/config.json`:

```json
{
  "platforms": {
    "leetcode": {
      "enabled": true,
      "username": "NightmareYT007"
    },
    "codeforces": {
      "enabled": true,
      "handle": "shreyasmene06"
    },
    "github": {
      "enabled": true,
      "username": "shreyasmene06"
    }
  },
  "reminder": {
    "enabled": true,
    "time": "21:00"
  },
  "general": {
    "sync_interval_minutes": 15,
    "mode": "any"
  }
}
```

---

## License

This project is licensed under the [MIT License](LICENSE).
