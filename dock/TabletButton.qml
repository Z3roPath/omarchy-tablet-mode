import Quickshell
import QtQuick

Item {
  id: root
  property var bar: null
  property string moduleName: "tablet-mode"
  property var settings: ({})
  property double lastActivation: 0
  implicitWidth: bar ? bar.barSize : 64
  implicitHeight: 94
  function activate() {
    if (Date.now() - lastActivation < 650) return
    lastActivation = Date.now()
    Quickshell.execDetached([Quickshell.env("HOME") + "/.local/share/omarchy-tablet-mode/bin/tablet-mode", "dock-toggle"])
  }
  function triggerPress(button) { root.activate() }

  Rectangle {
    anchors.centerIn: parent
    width: 40; height: 58; radius: 7
    color: tap.pressed ? "#526781" : "transparent"
    border.width: 3
    border.color: root.bar ? root.bar.foreground : "white"
    Rectangle {
      anchors { top: parent.top; left: parent.left; right: parent.right; margins: 7 }
      height: 34; radius: 2; color: root.bar ? root.bar.foreground : "white"
      opacity: 0.7
    }
    Rectangle {
      anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 5 }
      width: 5; height: 5; radius: 3
      color: root.bar ? root.bar.foreground : "white"
    }
  }
  TapHandler {
    id: tap
    gesturePolicy: TapHandler.ReleaseWithinBounds
    onTapped: root.activate()
  }
  HoverHandler {
    onHoveredChanged: {
      if (!root.bar) return
      if (hovered) root.bar.showTooltip(root, "Tablet Mode — tap for touch controls")
      else root.bar.hideTooltip(root)
    }
  }
}
