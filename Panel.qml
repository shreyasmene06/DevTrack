import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "devtrack.streak"

  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root

  readonly property var service: bar && bar.shell ? bar.shell.serviceFor("devtrack.streak") : null
  readonly property var trackerData: service ? service.trackerData : ({})
  readonly property int streak: service ? service.streakCount : 0
  readonly property int longestStreak: (trackerData && trackerData.longest_streak) ? trackerData.longest_streak : 0
  readonly property int totalActive90: (trackerData && trackerData.total_active_days_90) ? trackerData.total_active_days_90 : 0
  readonly property bool doneToday: service ? service.isDoneToday : false
  readonly property int totalToday: service ? service.totalToday : 0
  readonly property var platforms: service ? service.platforms : ({})
  readonly property var weeks: (trackerData && trackerData.weeks) ? trackerData.weeks : []
  readonly property var config: (trackerData && trackerData.config) ? trackerData.config : ({})

  readonly property color contentForeground: bar ? bar.foreground : Color.foreground
  readonly property string contentFontFamily: bar ? bar.fontFamily : Style.font.family

  property int viewMode: 0 // 0 = Dashboard & Heatmap, 1 = Settings

  // Draft settings
  property string draftGhUser: ""
  property string draftLcUser: ""
  property string draftCfUser: ""
  property string draftRemTime: "21:00"

  function sanitizeHandle(str) {
    if (!str) return ""
    return String(str).replace(/[^a-zA-Z0-9_\-\.]/g, "").slice(0, 64)
  }

  function openSafeUrl(url) {
    if (!url) return
    Qt.openUrlExternally(url)
  }

  function populateDraft() {
    var p = (root.config && root.config.platforms) ? root.config.platforms : {}
    root.draftLcUser = (p.leetcode && p.leetcode.username) ? p.leetcode.username : ""
    root.draftCfUser = (p.codeforces && p.codeforces.handle) ? p.codeforces.handle : ""
    root.draftGhUser = (p.github && p.github.username) ? p.github.username : ""
    var rem = (root.config && root.config.reminder) ? root.config.reminder : {}
    root.draftRemTime = rem.time || "21:00"
  }

  function saveSettings() {
    var lcClean = sanitizeHandle(root.draftLcUser)
    var cfClean = sanitizeHandle(root.draftCfUser)
    var ghClean = sanitizeHandle(root.draftGhUser)
    var remClean = root.draftRemTime.trim() || "21:00"

    var payload = {
      "platforms": {
        "leetcode": {
          "enabled": lcClean.length > 0,
          "username": lcClean
        },
        "codeforces": {
          "enabled": cfClean.length > 0,
          "handle": cfClean
        },
        "github": {
          "enabled": ghClean.length > 0,
          "username": ghClean
        }
      },
      "reminder": {
        "enabled": true,
        "time": remClean
      }
    }
    if (root.service) {
      root.service.saveConfig(payload)
    }
    root.viewMode = 0
  }

  function open() {
    populateDraft()
    root.controller.show()
  }

  function close() {
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.open()
  }

  function scrollBy(dy) {
    var flick = panelScroll
    if (!flick || flick.contentHeight <= flick.height) return
    flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + dy))
  }

  onOpenedChanged: {
    if (root.opened) {
      populateDraft()
      if (root.service) root.service.refresh()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(400))
    contentHeight: panel.fittedContentHeight(panelColumn.implicitHeight, Style.space(560))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onMoveRequested: function(dx, dy) {
        if (dy !== 0) root.scrollBy(-dy * Style.space(24))
      }
      onCloseRequested: root.close()

      Flickable {
        id: panelScroll
        anchors.fill: parent
        contentWidth: panelColumn.width
        contentHeight: panelColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height || contentWidth > width

        Column {
          id: panelColumn
          width: panelScroll.width
          spacing: Style.space(12)

          // ---------------- TOP HEADER ----------------
          Item {
            width: parent.width
            height: Style.space(26)

            Row {
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(8)

              Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "DEVTRACK"
                color: root.contentForeground
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.body
                font.letterSpacing: 2
                font.weight: Font.Bold
              }

              Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                radius: Style.space(4)
                color: root.viewMode === 1 ? Qt.rgba(0.2, 0.5, 1, 0.2) : Qt.rgba(1, 0.6, 0.1, 0.2)
                height: Style.space(18)
                width: modeBadgeText.implicitWidth + Style.space(8)

                Text {
                  id: modeBadgeText
                  anchors.centerIn: parent
                  text: root.viewMode === 1 ? "SETTINGS" : "STREAK"
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.space(9)
                  font.weight: Font.Bold
                  font.letterSpacing: 1
                  color: root.viewMode === 1 ? "#60A5FA" : "#F59E0B"
                }
              }
            }

            Row {
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(8)

              // Refresh Button
              Rectangle {
                width: Style.space(26)
                height: Style.space(26)
                radius: Style.space(5)
                color: refreshMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"

                Text {
                  anchors.centerIn: parent
                  text: "󰑓"
                  color: (root.service && root.service.isRefreshing) ? (Color.accent || "#38BDF8") : root.contentForeground
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.body
                }

                MouseArea {
                  id: refreshMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: if (root.service) root.service.refresh()
                }
              }

              // Settings Toggle Button
              Rectangle {
                width: Style.space(26)
                height: Style.space(26)
                radius: Style.space(5)
                color: (root.viewMode === 1 || settingsMouse.containsMouse) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"

                Text {
                  anchors.centerIn: parent
                  text: root.viewMode === 1 ? "󰅖" : "󰒓"
                  color: root.viewMode === 1 ? (Color.accent || "#38BDF8") : root.contentForeground
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.body
                }

                MouseArea {
                  id: settingsMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: {
                    if (root.viewMode === 1) {
                      root.viewMode = 0
                    } else {
                      root.populateDraft()
                      root.viewMode = 1
                    }
                  }
                }
              }

              // Close Button
              Rectangle {
                width: Style.space(26)
                height: Style.space(26)
                radius: Style.space(5)
                color: closeMouse.containsMouse ? Qt.rgba(1, 0.2, 0.2, 0.2) : "transparent"

                Text {
                  anchors.centerIn: parent
                  text: "✕"
                  color: closeMouse.containsMouse ? "#EF4444" : root.contentForeground
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.caption
                }

                MouseArea {
                  id: closeMouse
                  anchors.fill: parent
                  hoverEnabled: true
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.close()
                }
              }
            }
          }

          // Separator
          Rectangle {
            width: parent.width
            height: 1
            color: Color.popups.border || Qt.rgba(1, 1, 1, 0.12)
          }

          // ---------------- VIEW 0: DASHBOARD & HEATMAP ----------------
          Column {
            width: parent.width
            spacing: Style.space(12)
            visible: root.viewMode === 0

            // HERO STREAK STATUS BANNER
            Rectangle {
              width: parent.width
              implicitHeight: heroRow.implicitHeight + Style.space(18)
              radius: Style.space(10)
              color: Color.card || Qt.rgba(1, 1, 1, 0.05)
              border.color: root.doneToday ? Qt.rgba(0.06, 0.72, 0.5, 0.4) : Qt.rgba(0.96, 0.62, 0.04, 0.3)
              border.width: 1

              RowLayout {
                id: heroRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(10)
                spacing: Style.space(10)

                // Leading Flame Icon Badge
                Rectangle {
                  Layout.preferredWidth: Style.space(42)
                  Layout.preferredHeight: Style.space(42)
                  Layout.alignment: Qt.AlignVCenter
                  radius: Style.space(8)
                  color: root.doneToday ? Qt.rgba(0.06, 0.72, 0.5, 0.2) : Qt.rgba(0.96, 0.62, 0.04, 0.18)

                  Text {
                    anchors.centerIn: parent
                    text: "󰈸"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.space(26)
                    color: root.doneToday ? "#10B981" : (root.streak > 0 ? "#F59E0B" : (Color.accent || "#38BDF8"))
                  }
                }

                // Main Info
                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: Style.space(2)

                  RowLayout {
                    spacing: Style.space(6)
                    Text {
                      text: root.streak > 0 ? (root.streak + " Days Streak") : "0 Day Streak"
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.title
                      font.weight: Font.Bold
                      color: root.contentForeground
                    }

                    Rectangle {
                      radius: Style.space(4)
                      color: root.doneToday ? Qt.rgba(0.06, 0.72, 0.5, 0.25) : Qt.rgba(0.96, 0.62, 0.04, 0.22)
                      Layout.preferredHeight: Style.space(18)
                      Layout.preferredWidth: heroBadge.implicitWidth + Style.space(10)

                      Text {
                        id: heroBadge
                        anchors.centerIn: parent
                        text: root.doneToday ? "✓ Active Today" : "Pending"
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.space(10)
                        font.weight: Font.Bold
                        color: root.doneToday ? "#10B981" : "#F59E0B"
                      }
                    }
                  }

                  Text {
                    text: root.doneToday 
                      ? (root.totalToday + " activities logged today · Streak preserved")
                      : ("Reminder at " + (root.config.reminder ? root.config.reminder.time : "21:00") + " · Solve to keep streak")
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                    color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.65)
                  }
                }

                // Right Stats Column (Fixed geometry & unclipped)
                Column {
                  Layout.preferredWidth: Style.space(76)
                  Layout.alignment: Qt.AlignVCenter
                  spacing: Style.space(4)

                  Row {
                    spacing: Style.space(4)
                    Text { text: "󰓥"; font.pixelSize: Style.space(11); color: "#F59E0B"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                      text: root.longestStreak + "d best"
                      font.pixelSize: Style.space(10)
                      font.weight: Font.Bold
                      color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.85)
                      anchors.verticalCenter: parent.verticalCenter
                    }
                  }
                  Row {
                    spacing: Style.space(4)
                    Text { text: "󰃭"; font.pixelSize: Style.space(10); color: "#60A5FA"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                      text: root.totalActive90 + "d in 90d"
                      font.pixelSize: Style.space(9)
                      color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.6)
                      anchors.verticalCenter: parent.verticalCenter
                    }
                  }
                }
              }
            }

            // GITHUB-STYLE CONTRIBUTION HEATMAP (14 WEEKS)
            Rectangle {
              width: parent.width
              implicitHeight: heatmapLayout.implicitHeight + Style.space(20)
              radius: Style.space(10)
              color: Color.card || Qt.rgba(1, 1, 1, 0.05)
              border.color: Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              Column {
                id: heatmapLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(12)
                spacing: Style.space(8)

                RowLayout {
                  width: parent.width
                  Text {
                    text: "Contribution Heatmap"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    font.weight: Font.Bold
                    color: root.contentForeground
                  }
                  Item { Layout.fillWidth: true }
                  Text {
                    text: root.totalToday + " today · 14 Weeks"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                    color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.5)
                  }
                }

                // Grid Row (Day labels + 14 Week columns)
                Row {
                  spacing: Style.space(6)
                  anchors.horizontalCenter: parent.horizontalCenter

                  // Day of week labels perfectly matching cell height
                  Column {
                    spacing: Style.space(4)
                    anchors.verticalCenter: parent.verticalCenter

                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "S"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.25) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "M"; font.pixelSize: Style.space(9); font.weight: Font.Bold; color: Qt.rgba(1,1,1,0.65) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "T"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.25) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "W"; font.pixelSize: Style.space(9); font.weight: Font.Bold; color: Qt.rgba(1,1,1,0.65) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "T"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.25) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "F"; font.pixelSize: Style.space(9); font.weight: Font.Bold; color: Qt.rgba(1,1,1,0.65) } }
                    Item { width: Style.space(10); height: Style.space(16); Text { anchors.centerIn: parent; text: "S"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.25) } }
                  }

                  // 14 Week Columns
                  Repeater {
                    model: root.weeks

                    Column {
                      id: weekCol
                      required property var modelData
                      spacing: Style.space(4)

                      Repeater {
                        model: weekCol.modelData

                        Rectangle {
                          id: cellRect
                          required property var modelData
                          width: Style.space(16)
                          height: Style.space(16)
                          radius: Style.space(3)
                          color: {
                            if (cellRect.modelData && cellRect.modelData.level === 4) return "#39D353"
                            if (cellRect.modelData && cellRect.modelData.level === 3) return "#26A641"
                            if (cellRect.modelData && cellRect.modelData.level === 2) return "#006D32"
                            if (cellRect.modelData && cellRect.modelData.level === 1) return "#0E4429"
                            return Qt.rgba(1, 1, 1, 0.07)
                          }
                          border.color: (cellRect.modelData && cellRect.modelData.is_today) ? (Color.accent || "#38BDF8") : "transparent"
                          border.width: (cellRect.modelData && cellRect.modelData.is_today) ? 1.5 : 0

                          MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: {
                              if (root.bar && cellRect.modelData) {
                                var dt = cellRect.modelData.formatted_date || cellRect.modelData.date
                                var cnt = cellRect.modelData.count
                                var label = cnt === 1 ? "1 contribution" : cnt + " contributions"
                                root.bar.showTooltip(cellRect, dt + ": " + label)
                              }
                            }
                            onExited: if (root.bar) root.bar.hideTooltip(cellRect)
                          }
                        }
                      }
                    }
                  }
                }

                // Legend & Summary Footer
                RowLayout {
                  width: parent.width

                  Text {
                    text: root.totalActive90 + " active days in 90d"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.space(10)
                    color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.5)
                  }

                  Item { Layout.fillWidth: true }

                  Row {
                    spacing: Style.space(3)
                    Text { text: "Less"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.4); anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { width: Style.space(9); height: Style.space(9); radius: 2; color: Qt.rgba(1,1,1,0.07) }
                    Rectangle { width: Style.space(9); height: Style.space(9); radius: 2; color: "#0E4429" }
                    Rectangle { width: Style.space(9); height: Style.space(9); radius: 2; color: "#006D32" }
                    Rectangle { width: Style.space(9); height: Style.space(9); radius: 2; color: "#26A641" }
                    Rectangle { width: Style.space(9); height: Style.space(9); radius: 2; color: "#39D353" }
                    Text { text: "More"; font.pixelSize: Style.space(9); color: Qt.rgba(1,1,1,0.4); anchors.verticalCenter: parent.verticalCenter }
                  }
                }
              }
            }

            // PLATFORMS SECTION TITLE
            Text {
              text: "Connected Platforms"
              font.family: root.contentFontFamily
              font.pixelSize: Style.font.bodySmall
              font.weight: Font.Bold
              color: root.contentForeground
            }

            // 1. LEETCODE CARD
            Rectangle {
              id: lcCard
              width: parent.width
              height: Style.space(48)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: lcCardMouse.containsMouse ? Qt.rgba(1, 0.63, 0.09, 0.3) : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              readonly property var lc: (root.platforms && root.platforms.leetcode) ? root.platforms.leetcode : ({})
              readonly property bool hasUser: lc.username !== undefined && String(lc.username).length > 0

              MouseArea {
                id: lcCardMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: lcCard.hasUser ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: if (lcCard.hasUser) root.openSafeUrl("https://leetcode.com/u/" + encodeURIComponent(lcCard.lc.username))
              }

              RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                spacing: Style.space(10)

                Rectangle {
                  Layout.preferredWidth: Style.space(32)
                  Layout.preferredHeight: Style.space(32)
                  radius: Style.space(6)
                  color: Qt.rgba(1, 0.63, 0.09, 0.15)

                  Text {
                    anchors.centerIn: parent
                    text: "󰘐"
                    font.pixelSize: Style.space(18)
                    color: "#FFA116"
                  }
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: 0

                  RowLayout {
                    spacing: Style.space(6)
                    Text {
                      text: lcCard.hasUser ? ("LeetCode · @" + lcCard.lc.username) : "LeetCode · Not Configured"
                      font.pixelSize: Style.font.caption
                      font.weight: Font.Bold
                      color: root.contentForeground
                    }
                  }

                  Text {
                    text: lcCard.hasUser
                      ? (lcCard.lc.today_count > 0 
                          ? ("✓ " + lcCard.lc.today_count + " solved today · Streak: " + (lcCard.lc.streak || 0) + "d")
                          : ("0 solved today · Total: " + (lcCard.lc.total_solved || 0) + " solved · Streak: " + (lcCard.lc.streak || 0) + "d"))
                      : "Click ⚙ to configure handle"
                    font.pixelSize: Style.space(10)
                    color: (lcCard.lc.today_count > 0) ? "#10B981" : Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.55)
                  }
                }

                Rectangle {
                  Layout.preferredWidth: Style.space(26)
                  Layout.preferredHeight: Style.space(26)
                  radius: Style.space(4)
                  color: lcCardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                  visible: lcCard.hasUser

                  Text {
                    anchors.centerIn: parent
                    text: "󰌹"
                    font.pixelSize: Style.font.caption
                    color: lcCardMouse.containsMouse ? (Color.accent || "#38BDF8") : Qt.rgba(1, 1, 1, 0.5)
                  }
                }
              }
            }

            // 2. CODEFORCES CARD
            Rectangle {
              id: cfCard
              width: parent.width
              height: Style.space(48)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: cfCardMouse.containsMouse ? Qt.rgba(0.23, 0.51, 0.96, 0.3) : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              readonly property var cf: (root.platforms && root.platforms.codeforces) ? root.platforms.codeforces : ({})
              readonly property bool hasUser: cf.username !== undefined && String(cf.username).length > 0

              MouseArea {
                id: cfCardMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: cfCard.hasUser ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: if (cfCard.hasUser) root.openSafeUrl("https://codeforces.com/profile/" + encodeURIComponent(cfCard.cf.username))
              }

              RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                spacing: Style.space(10)

                Rectangle {
                  Layout.preferredWidth: Style.space(32)
                  Layout.preferredHeight: Style.space(32)
                  radius: Style.space(6)
                  color: Qt.rgba(0.23, 0.51, 0.96, 0.15)

                  Text {
                    anchors.centerIn: parent
                    text: "󰲋"
                    font.pixelSize: Style.space(18)
                    color: "#3B82F6"
                  }
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: 0

                  RowLayout {
                    spacing: Style.space(6)
                    Text {
                      text: cfCard.hasUser ? ("Codeforces · @" + cfCard.cf.username) : "Codeforces · Not Configured"
                      font.pixelSize: Style.font.caption
                      font.weight: Font.Bold
                      color: root.contentForeground
                    }
                  }

                  Text {
                    text: cfCard.hasUser
                      ? (cfCard.cf.today_count > 0 
                          ? ("✓ " + cfCard.cf.today_count + " AC today · Rating: " + (cfCard.cf.rating || 0))
                          : ("0 AC today · Rating: " + (cfCard.cf.rating || 0) + " · Rank: " + (cfCard.cf.rank || "unrated")))
                      : "Click ⚙ to configure handle"
                    font.pixelSize: Style.space(10)
                    color: (cfCard.cf.today_count > 0) ? "#10B981" : Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.55)
                  }
                }

                Rectangle {
                  Layout.preferredWidth: Style.space(26)
                  Layout.preferredHeight: Style.space(26)
                  radius: Style.space(4)
                  color: cfCardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                  visible: cfCard.hasUser

                  Text {
                    anchors.centerIn: parent
                    text: "󰌹"
                    font.pixelSize: Style.font.caption
                    color: cfCardMouse.containsMouse ? (Color.accent || "#38BDF8") : Qt.rgba(1, 1, 1, 0.5)
                  }
                }
              }
            }

            // 3. GITHUB CARD
            Rectangle {
              id: ghCard
              width: parent.width
              height: Style.space(48)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: ghCardMouse.containsMouse ? Qt.rgba(0.06, 0.72, 0.5, 0.3) : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              readonly property var gh: (root.platforms && root.platforms.github) ? root.platforms.github : ({})
              readonly property bool hasUser: gh.username !== undefined && String(gh.username).length > 0

              MouseArea {
                id: ghCardMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: ghCard.hasUser ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: if (ghCard.hasUser) root.openSafeUrl("https://github.com/" + encodeURIComponent(ghCard.gh.username))
              }

              RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                spacing: Style.space(10)

                Rectangle {
                  Layout.preferredWidth: Style.space(32)
                  Layout.preferredHeight: Style.space(32)
                  radius: Style.space(6)
                  color: Qt.rgba(0.06, 0.72, 0.5, 0.15)

                  Text {
                    anchors.centerIn: parent
                    text: "󰊤"
                    font.pixelSize: Style.space(18)
                    color: "#10B981"
                  }
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: 0

                  RowLayout {
                    spacing: Style.space(6)
                    Text {
                      text: ghCard.hasUser ? ("GitHub · @" + ghCard.gh.username) : "GitHub · Not Configured"
                      font.pixelSize: Style.font.caption
                      font.weight: Font.Bold
                      color: root.contentForeground
                    }
                  }

                  Text {
                    text: ghCard.hasUser
                      ? (ghCard.gh.today_count > 0 
                          ? ("✓ " + ghCard.gh.today_count + " contributions today · Streak: " + (ghCard.gh.streak || 0) + "d")
                          : ("0 commits today · Streak: " + (ghCard.gh.streak || 0) + "d · Active in 90d"))
                      : "Click ⚙ to configure handle"
                    font.pixelSize: Style.space(10)
                    color: (ghCard.gh.today_count > 0) ? "#10B981" : Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.55)
                  }
                }

                Rectangle {
                  Layout.preferredWidth: Style.space(26)
                  Layout.preferredHeight: Style.space(26)
                  radius: Style.space(4)
                  color: ghCardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                  visible: ghCard.hasUser

                  Text {
                    anchors.centerIn: parent
                    text: "󰌹"
                    font.pixelSize: Style.font.caption
                    color: ghCardMouse.containsMouse ? (Color.accent || "#38BDF8") : Qt.rgba(1, 1, 1, 0.5)
                  }
                }
              }
            }
          }

          // ---------------- VIEW 1: SETTINGS VIEW ----------------
          Column {
            width: parent.width
            spacing: Style.space(10)
            visible: root.viewMode === 1

            Text {
              text: "Configure platforms and reminder schedule:"
              font.pixelSize: Style.font.caption
              color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.7)
            }

            // LeetCode Input Card
            Rectangle {
              width: parent.width
              implicitHeight: lcInputCol.implicitHeight + Style.space(14)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: lcIn.activeFocus ? "#FFA116" : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              Column {
                id: lcInputCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(8)
                spacing: Style.space(4)

                Row {
                  spacing: Style.space(8)
                  Text { text: "󰘐"; font.pixelSize: Style.space(14); color: "#FFA116"; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: "LeetCode Username"; font.pixelSize: Style.space(11); font.weight: Font.Bold; color: "#FFA116"; anchors.verticalCenter: parent.verticalCenter }
                }

                Rectangle {
                  width: parent.width
                  height: Style.space(32)
                  radius: Style.space(5)
                  color: Qt.rgba(0, 0, 0, 0.4)
                  border.color: lcIn.activeFocus ? "#FFA116" : Qt.rgba(1, 1, 1, 0.12)

                  TextInput {
                    id: lcIn
                    anchors.fill: parent
                    anchors.leftMargin: Style.space(8)
                    anchors.rightMargin: Style.space(8)
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.draftLcUser
                    color: root.contentForeground
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    selectByMouse: true
                    onTextChanged: root.draftLcUser = text
                  }
                }
              }
            }

            // Codeforces Input Card
            Rectangle {
              width: parent.width
              implicitHeight: cfInputCol.implicitHeight + Style.space(14)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: cfIn.activeFocus ? "#3B82F6" : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              Column {
                id: cfInputCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(8)
                spacing: Style.space(4)

                Row {
                  spacing: Style.space(8)
                  Text { text: "󰲋"; font.pixelSize: Style.space(14); color: "#3B82F6"; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: "Codeforces Handle"; font.pixelSize: Style.space(11); font.weight: Font.Bold; color: "#3B82F6"; anchors.verticalCenter: parent.verticalCenter }
                }

                Rectangle {
                  width: parent.width
                  height: Style.space(32)
                  radius: Style.space(5)
                  color: Qt.rgba(0, 0, 0, 0.4)
                  border.color: cfIn.activeFocus ? "#3B82F6" : Qt.rgba(1, 1, 1, 0.12)

                  TextInput {
                    id: cfIn
                    anchors.fill: parent
                    anchors.leftMargin: Style.space(8)
                    anchors.rightMargin: Style.space(8)
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.draftCfUser
                    color: root.contentForeground
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    selectByMouse: true
                    onTextChanged: root.draftCfUser = text
                  }
                }
              }
            }

            // GitHub Input Card
            Rectangle {
              width: parent.width
              implicitHeight: ghInputCol.implicitHeight + Style.space(14)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: ghIn.activeFocus ? "#10B981" : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              Column {
                id: ghInputCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(8)
                spacing: Style.space(4)

                Row {
                  spacing: Style.space(8)
                  Text { text: "󰊤"; font.pixelSize: Style.space(14); color: "#10B981"; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: "GitHub Username"; font.pixelSize: Style.space(11); font.weight: Font.Bold; color: "#10B981"; anchors.verticalCenter: parent.verticalCenter }
                }

                Rectangle {
                  width: parent.width
                  height: Style.space(32)
                  radius: Style.space(5)
                  color: Qt.rgba(0, 0, 0, 0.4)
                  border.color: ghIn.activeFocus ? "#10B981" : Qt.rgba(1, 1, 1, 0.12)

                  TextInput {
                    id: ghIn
                    anchors.fill: parent
                    anchors.leftMargin: Style.space(8)
                    anchors.rightMargin: Style.space(8)
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.draftGhUser
                    color: root.contentForeground
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    selectByMouse: true
                    onTextChanged: root.draftGhUser = text
                  }
                }
              }
            }

            // Reminder Time Input Card
            Rectangle {
              width: parent.width
              implicitHeight: remInputCol.implicitHeight + Style.space(14)
              radius: Style.space(8)
              color: Color.card || Qt.rgba(1, 1, 1, 0.04)
              border.color: remIn.activeFocus ? "#F59E0B" : Qt.rgba(1, 1, 1, 0.08)
              border.width: 1

              Column {
                id: remInputCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(8)
                spacing: Style.space(4)

                Row {
                  spacing: Style.space(8)
                  Text { text: "󰀠"; font.pixelSize: Style.space(14); color: "#F59E0B"; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: "Daily Reminder Time (e.g. 21:00)"; font.pixelSize: Style.space(11); font.weight: Font.Bold; color: "#F59E0B"; anchors.verticalCenter: parent.verticalCenter }
                }

                Rectangle {
                  width: parent.width
                  height: Style.space(32)
                  radius: Style.space(5)
                  color: Qt.rgba(0, 0, 0, 0.4)
                  border.color: remIn.activeFocus ? "#F59E0B" : Qt.rgba(1, 1, 1, 0.12)

                  TextInput {
                    id: remIn
                    anchors.fill: parent
                    anchors.leftMargin: Style.space(8)
                    anchors.rightMargin: Style.space(8)
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.draftRemTime
                    color: root.contentForeground
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    selectByMouse: true
                    onTextChanged: root.draftRemTime = text
                  }
                }
              }
            }

            // Buttons: Save & Sync / Cancel
            RowLayout {
              width: parent.width
              spacing: Style.space(10)

              Rectangle {
                Layout.fillWidth: true
                height: Style.space(34)
                radius: Style.space(6)
                color: Color.accent || "#38BDF8"

                Text {
                  anchors.centerIn: parent
                  text: "Save & Sync Now"
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.caption
                  font.weight: Font.Bold
                  color: "#000000"
                }

                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.saveSettings()
                }
              }

              Rectangle {
                Layout.preferredWidth: Style.space(80)
                height: Style.space(34)
                radius: Style.space(6)
                color: Qt.rgba(1, 1, 1, 0.1)

                Text {
                  anchors.centerIn: parent
                  text: "Back"
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.caption
                  color: root.contentForeground
                }

                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.viewMode = 0
                }
              }
            }
          }

        }
      }
    }
  }
}
