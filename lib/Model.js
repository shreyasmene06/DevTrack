// Model.js - Helper functions for DevTrack streak data and formatting

.pragma library

function formatStreak(streak) {
  var s = Number(streak) || 0;
  return s === 1 ? "1 day" : s + " days";
}

function platformColor(platform) {
  switch (String(platform).toLowerCase()) {
    case "leetcode":
      return "#FFA116";
    case "codeforces":
      return "#3B82F6";
    case "github":
      return "#2EA043";
    default:
      return "#A855F7";
  }
}

function platformGlyph(platform) {
  switch (String(platform).toLowerCase()) {
    case "leetcode":
      return "󰘐";
    case "codeforces":
      return "󰲋";
    case "github":
      return "󰊤";
    default:
      return "󰈸";
  }
}

function timeAgo(epochSeconds) {
  if (!epochSeconds) return "Never";
  var now = Math.floor(Date.now() / 1000);
  var diff = now - Number(epochSeconds);
  if (diff < 60) return "Just now";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  var days = Math.floor(diff / 86400);
  return days === 1 ? "1d ago" : days + "d ago";
}

function timeUntilMidnight() {
  var now = new Date();
  var midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
  var diffMs = midnight.getTime() - now.getTime();
  var hours = Math.floor(diffMs / (1000 * 60 * 60));
  var mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  return hours + "h " + mins + "m left";
}
