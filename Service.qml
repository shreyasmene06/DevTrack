import QtQuick
import Quickshell
import Quickshell.Io
import "lib/Model.js" as Model

Item {
  id: root

  // Injected by omarchy-shell
  property var shell: null

  readonly property string home: Quickshell.env("HOME")
  readonly property string dataDir: home + "/.config/omarchy/devtrack"
  readonly property string dataPath: dataDir + "/data.json"
  readonly property string configPath: dataDir + "/config.json"

  readonly property string fetcherPath: {
    var u = Qt.resolvedUrl("scripts/fetch_activity.py").toString()
    return u.startsWith("file://") ? u.slice(7) : u
  }

  readonly property string notifyPath: {
    var u = Qt.resolvedUrl("scripts/notify.py").toString()
    return u.startsWith("file://") ? u.slice(7) : u
  }

  readonly property string saveConfigPath: {
    var u = Qt.resolvedUrl("scripts/save_config.py").toString()
    return u.startsWith("file://") ? u.slice(7) : u
  }

  // Reactive state
  property var trackerData: ({})
  property int streakCount: (trackerData && trackerData.composite_streak !== undefined) ? trackerData.composite_streak : 0
  property bool isDoneToday: (trackerData && trackerData.is_done_today === true)
  property int totalToday: (trackerData && trackerData.total_today !== undefined) ? trackerData.total_today : 0
  property var platforms: (trackerData && trackerData.platforms) ? trackerData.platforms : ({})
  property var weeks: (trackerData && trackerData.weeks) ? trackerData.weeks : []
  property var config: (trackerData && trackerData.config) ? trackerData.config : ({})

  readonly property string glyph: "󰈸"
  readonly property string barLabel: streakCount > 0 ? (streakCount + "d") : (isDoneToday ? "1d" : "0d")
  readonly property string tooltip: {
    if (streakCount > 0) {
      return "DevTrack · " + streakCount + " day streak" + (isDoneToday ? " (Done today ✓)" : " (Pending today ⚠)")
    }
    return isDoneToday ? "DevTrack · Active today ✓" : "DevTrack · No activity yet today"
  }

  property bool isRefreshing: false
  property bool ready: false

  function parseData(jsonText) {
    if (!jsonText) return
    var str = String(jsonText).trim()
    if (!str || str.length === 0) return
    try {
      var parsed = JSON.parse(str)
      if (parsed) {
        root.trackerData = parsed
        root.ready = true
      }
    } catch (e) {
      console.warn("DevTrack: JSON parse error: " + e)
    }
  }

  function refresh() {
    if (fetchProc.running) return
    root.isRefreshing = true
    fetchProc.running = true
  }

  function checkReminder() {
    if (notifyProc.running) return
    notifyProc.running = true
  }

  function saveConfig(cfg) {
    saveProc.command = ["python3", root.saveConfigPath, JSON.stringify(cfg)]
    saveProc.running = true
  }

  // Main Activity Fetcher Process
  Process {
    id: fetchProc
    command: ["python3", root.fetcherPath]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        root.isRefreshing = false
        if (text) root.parseData(text)
      }
    }
    onExited: {
      root.isRefreshing = false
      root.checkReminder()
    }
  }

  // Notification Process
  Process {
    id: notifyProc
    command: ["python3", root.notifyPath]
  }

  // Config Saving Process
  Process {
    id: saveProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        root.refresh()
      }
    }
  }

  // Periodic Fetcher Timer (every 15 minutes)
  Timer {
    id: syncTimer
    interval: 15 * 60 * 1000
    repeat: true
    running: true
    onTriggered: root.refresh()
  }

  // Reminder schedule check (every 1 minute)
  Timer {
    id: reminderTimer
    interval: 60 * 1000
    repeat: true
    running: true
    onTriggered: root.checkReminder()
  }

  Component.onCompleted: {
    root.refresh()
  }
}
