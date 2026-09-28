import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick

ShellRoot {
  id: root
  readonly property string controller: Quickshell.env("HOME") + "/.local/share/omarchy-tablet-mode/bin/tablet-mode"
  property bool barVisible: false
  property bool stateReady: false
  property int keyboardHeight: 0
  property bool dockVisible: false
  property bool dockHeld: false
  property string dockPosition: "left"
  readonly property int barHeight: Math.max(64, Math.min(120, Number(Quickshell.env("OMARCHY_TABLET_BAR_HEIGHT") || 80)))
  function scheduleDockHide() {
    dockTimer.stop()
    if (dockVisible && !dockHeld) dockTimer.restart()
  }
  onDockVisibleChanged: scheduleDockHide()
  onDockHeldChanged: scheduleDockHide()
  Component.onCompleted: root.command(["dock", "hide"])
  function command(args) { Quickshell.execDetached([root.controller].concat(args)) }
  IpcHandler {
    target: "tablet"
    function revealBar(): void { root.barVisible = true }
    function hideBar(): void { root.barVisible = false }
  }
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy-tablet-mode/dock-state"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.dockVisible = text().trim() === "visible"
    onLoadFailed: root.dockVisible = false
  }
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy-tablet-mode/dock-interaction"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.dockHeld = text().trim() === "held"
    onLoadFailed: root.dockHeld = false
  }
  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/shell.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      try { root.dockPosition = JSON.parse(text()).bar.position || "left" } catch (e) {}
    }
  }
  Timer { id: dockTimer; interval: Math.max(2000, Number(Quickshell.env("OMARCHY_TABLET_DOCK_TIMEOUT") || 6000)); onTriggered: root.command(["dock", "hide"]) }
  FileView {
    id: hiddenFile
    path: Quickshell.env("HOME") + "/.local/state/omarchy-tablet-mode/bar-hidden"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: { root.barVisible = text().trim() !== "hidden"; root.stateReady = true }
    onLoadFailed: { root.barVisible = true; root.stateReady = true }
  }
  Process {
    id: keyboardProbe
    command: ["hyprctl", "-j", "layers"]
    stdout: StdioCollector {
      onStreamFinished: {
        var height = 0
        try {
          var layers = JSON.parse(text)
          for (var monitor in layers) {
            for (var level in layers[monitor].levels) {
              var entries = layers[monitor].levels[level]
              for (var i = 0; i < entries.length; ++i)
                if (entries[i].namespace === "wvkbd") height = Math.max(height, entries[i].h || 0)
            }
          }
        } catch (e) {}
        root.keyboardHeight = height
      }
    }
  }
  Timer {
    interval: 500; repeat: true; triggeredOnStart: true
    running: !root.barVisible
    onTriggered: if (!keyboardProbe.running) keyboardProbe.running = true
  }
  readonly property var buttons: [
    { label: "Apps", symbol: "☰", action: "launcher" },
    { label: "Browser", symbol: "◎", action: "browser" },
    { label: "Files", symbol: "▣", action: "files" },
    { label: "Terminal", symbol: ">_", action: "terminal" },
    { label: "E-Ink", symbol: "E", action: "reader" },
    { label: "Keyboard", symbol: "⌨", action: "keyboard" },
    { label: "Previous", symbol: "◀", action: "previous" },
    { label: "Next", symbol: "▶", action: "next" },
    { label: "Exit", symbol: "×", action: "exit" }
  ]

  PanelWindow {
    id: rail
    visible: root.stateReady && root.barVisible
    anchors { right: true; left: true; bottom: true }
    implicitHeight: root.barHeight
    color: "transparent"
    focusable: false
    WlrLayershell.namespace: "omarchy-tablet-mode"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Auto

    Row {
      anchors { fill: parent; margins: 5 }
      spacing: 4

      Repeater {
        model: root.buttons
        Rectangle {
          required property var modelData
          width: (rail.width - 10 - 4 * (root.buttons.length - 1)) / root.buttons.length
          height: rail.height - 10
          radius: 14
          color: press.pressed ? "#59677c" : modelData.action === "exit" ? "#683e45" : "#343b48"
          border.color: "#697586"
          border.width: 1

          Column {
            anchors.centerIn: parent
            spacing: 2
            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: modelData.symbol
              color: "white"
              font.pixelSize: 24
              font.bold: true
            }
            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: modelData.label
              color: "white"
              font.pixelSize: 13
              font.bold: true
            }
          }
          TapHandler {
            id: press
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad | PointerDevice.Stylus
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onTapped: root.command(["action", modelData.action])
          }
        }
      }
    }
    MultiPointTouchArea {
      anchors.fill: parent
      minimumTouchPoints: 1; maximumTouchPoints: 1
      mouseEnabled: false
      property real startX: 0
      property real startY: 0
      property real lastX: 0
      property real lastY: 0
      property bool dismissed: false
      onPressed: function(points) {
        startX = points[0].x; startY = points[0].y
        lastX = startX; lastY = startY; dismissed = false
      }
      onUpdated: function(points) {
        lastX = points[0].x; lastY = points[0].y
        if (!dismissed && Math.abs(lastX - startX) > 55 && Math.abs(lastY - startY) < 32) {
          dismissed = true
          root.command(["bar", "hide"])
        }
      }
      onReleased: function(points) {
        if (dismissed || Math.abs(lastX - startX) > 20 || Math.abs(lastY - startY) > 25) return
        var index = Math.floor((startX - 5) / ((rail.width - 10) / root.buttons.length))
        if (index >= 0 && index < root.buttons.length) root.command(["action", root.buttons[index].action])
      }
      onGestureStarted: function(gesture) { gesture.grab() }
    }
  }

  PanelWindow {
    id: edgeHandle
    visible: root.stateReady && !root.dockVisible && (root.dockPosition === "left" || root.dockPosition === "right")
    anchors { left: root.dockPosition === "left"; right: root.dockPosition === "right" }
    implicitWidth: 18; implicitHeight: 180
    color: "transparent"
    focusable: false
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "tablet-dock-edge"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    TapHandler {
      acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad | PointerDevice.Stylus
      onTapped: root.command(["dock", "reveal"])
    }
    MultiPointTouchArea {
      anchors.fill: parent
      minimumTouchPoints: 1; maximumTouchPoints: 1
      mouseEnabled: false
      property real startX: 0
      property real startY: 0
      property real lastX: 0
      property real lastY: 0
      property bool triggered: false
      onPressed: function(points) {
        startX = points[0].x; startY = points[0].y
        lastX = startX; lastY = startY; triggered = false
      }
      onUpdated: function(points) {
        lastX = points[0].x; lastY = points[0].y
        var dx = lastX - startX
        if (!triggered && Math.abs(lastY - startY) < 40 && (root.dockPosition === "left" ? dx > 28 : dx < -28)) {
          triggered = true
          root.command(["dock", "reveal"])
        }
      }
      onReleased: if (!triggered && Math.abs(lastX - startX) < 15 && Math.abs(lastY - startY) < 15) root.command(["dock", "reveal"])
      onGestureStarted: function(gesture) { gesture.grab() }
    }
  }

  Variants {
    model: [false, true]
    delegate: PanelWindow {
      id: corner
      required property bool modelData
      visible: root.stateReady && !root.barVisible
      anchors { left: !modelData; right: modelData; bottom: true }
      margins.bottom: root.keyboardHeight
      implicitWidth: 60; implicitHeight: 72
      color: "transparent"
      focusable: false
      exclusionMode: ExclusionMode.Ignore
      WlrLayershell.namespace: modelData ? "tablet-reveal-right" : "tablet-reveal-left"
      WlrLayershell.layer: WlrLayer.Overlay
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      TapHandler {
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad | PointerDevice.Stylus
        onTapped: root.command(["bar", "reveal"])
      }
      MultiPointTouchArea {
        anchors.fill: parent
        minimumTouchPoints: 1; maximumTouchPoints: 1
        mouseEnabled: false
        property real startX: 0
        property real startY: 0
        property real lastX: 0
        property real lastY: 0
        property bool triggered: false
        onPressed: function(points) {
          startX = points[0].x; startY = points[0].y
          lastX = startX; lastY = startY; triggered = false
        }
        onUpdated: function(points) {
          lastX = points[0].x; lastY = points[0].y
          var dx = lastX - startX
          if (!triggered && Math.abs(lastY - startY) < 32 && (corner.modelData ? dx < -40 : dx > 40)) {
            triggered = true
            root.command(["bar", "reveal"])
          }
        }
        onReleased: if (!triggered && Math.abs(lastX - startX) < 15 && Math.abs(lastY - startY) < 15) root.command(["bar", "reveal"])
        onGestureStarted: function(gesture) { gesture.grab() }
      }
    }
  }
}
