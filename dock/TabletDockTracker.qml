import QtQuick
import Quickshell
import Quickshell.Io

// This observes touches passively, leaving the dock widgets in control.
Item {
  id: tracker
  required property var bar
  property bool tracking: false
  property bool touchHeld: point.active
  function notify() {
    if (!tracking) return
    var held = touchHeld || bar.barHovered || bar.activePopout !== null
    Quickshell.execDetached([Quickshell.env("HOME") + "/.local/share/omarchy-tablet-mode/bin/tablet-mode", "dock", "interaction", held ? "held" : "released"])
  }
  onTrackingChanged: notify()
  onTouchHeldChanged: notify()
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy-tablet-mode/dock-state"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: tracker.tracking = text().trim() === "visible"
    onLoadFailed: tracker.tracking = false
  }
  Connections {
    target: tracker.bar
    function onBarHoveredChanged() { tracker.notify() }
    function onActivePopoutChanged() { tracker.notify() }
  }
  PointHandler {
    id: point
    target: null
    enabled: tracker.tracking
    acceptedDevices: PointerDevice.TouchScreen
  }
}
