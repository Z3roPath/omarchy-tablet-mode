#!/usr/bin/env python3
"""Build review-only touch sign-in UI; never modify system authentication files."""
import difflib
import shutil
from pathlib import Path

here = Path(__file__).resolve().parent
theme = here / "theme"
source = Path("/usr/share/sddm/themes/omarchy")
shutil.copytree(source, theme, dirs_exist_ok=True)
shutil.copy2(here / "TouchKeyboard.qml", theme / "TouchKeyboard.qml")
main = (source / "Main.qml").read_text()
for anchor in ['  property bool loginFailed: false', '  Component.onCompleted: password.forceActiveFocus()', 'sddm.login(root.currentUser, password.text, root.sessionIndex)']:
    if main.count(anchor) != 1:
        raise SystemExit('Unsupported SDDM Omarchy theme; review before generating: ' + anchor)
main = main.replace('  property bool loginFailed: false', '  property bool loginFailed: false\n  property bool keyboardVisible: false')
main = main.replace('    anchors.centerIn: parent', '    anchors.centerIn: parent\n    anchors.verticalCenterOffset: root.keyboardVisible ? -touchKeys.height / 2 : -40', 1)
main = main.replace('      id: logo', '      id: logo\n      visible: !root.keyboardVisible')

touch_area = '''
  MultiPointTouchArea {
    anchors.fill: parent
    z: 100
    mouseEnabled: false
    minimumTouchPoints: 4
    maximumTouchPoints: 4
    property real startY: 0
    property bool triggered: false
    function centerY(points) {
      var sum = 0
      for (var i = 0; i < points.length; ++i) sum += points[i].y
      return sum / points.length
    }
    onPressed: function(points) { startY = centerY(points); triggered = false }
    onUpdated: function(points) {
      if (triggered || points.length !== 4) return
      var delta = centerY(points) - startY
      if (delta < -60) { root.keyboardVisible = true; triggered = true }
      else if (delta > 60) { root.keyboardVisible = false; triggered = true }
    }
    onGestureStarted: function(gesture) { gesture.grab() }
  }
'''
main = main.replace('  Component.onCompleted: password.forceActiveFocus()', '''
  Rectangle {
    width: 210; height: 64; radius: 12; color: "#343b48"
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: touchKeys.visible ? touchKeys.top : parent.bottom
    anchors.bottomMargin: 12
    Text { anchors.centerIn: parent; text: root.keyboardVisible ? "Hide keyboard" : "Keyboard"; color: "white"; font.pixelSize: 24 }
    MouseArea { anchors.fill: parent; onClicked: root.keyboardVisible = !root.keyboardVisible }
  }
  TouchKeyboard {
    id: touchKeys
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
    height: Math.min(270, root.height * 0.32)
    visible: root.keyboardVisible
    onHideRequested: root.keyboardVisible = false
    onKeyPressed: function(key) {
      if (key === "Backspace") password.remove(Math.max(0, password.cursorPosition - 1), password.cursorPosition)
      else if (key === "Enter") sddm.login(root.currentUser, password.text, root.sessionIndex)
      else password.insert(password.cursorPosition, key)
    }
  }
''' + touch_area + '\n  Component.onCompleted: password.forceActiveFocus()')
(theme / "Main.qml").write_text(main)

lock_source = Path("/usr/share/omarchy/shell/plugins/lock/LockView.qml")
lock = lock_source.read_text()
for anchor in ['  property bool syncingPasswordText: false', '  onInputEnabledChanged: {']:
    if lock.count(anchor) != 1:
        raise SystemExit('Unsupported Omarchy lock view; review before generating: ' + anchor)
lock_new = lock.replace('  property bool syncingPasswordText: false', '  property bool syncingPasswordText: false\n  property bool keyboardVisible: false')
lock_new = lock_new.replace('      anchors.centerIn: parent', '      anchors.centerIn: parent\n      anchors.verticalCenterOffset: root.keyboardVisible ? -touchKeys.height / 2 : 0', 1)
lock_addition = '''
  Rectangle {
    width: 210; height: 64; radius: 12; color: "#343b48"
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: touchKeys.visible ? touchKeys.top : parent.bottom
    anchors.bottomMargin: 16
    Text { anchors.centerIn: parent; text: root.keyboardVisible ? "Hide keyboard" : "Keyboard"; color: "white"; font.pixelSize: 24 }
    MouseArea { anchors.fill: parent; onClicked: { root.keyboardVisible = !root.keyboardVisible; root.wakeRequested() } }
  }
  TouchKeyboard {
    id: touchKeys
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
    height: Math.min(270, root.height * 0.32)
    visible: root.keyboardVisible
    enabled: root.inputEnabled && !root.authenticatingPassword
    onHideRequested: root.keyboardVisible = false
    onKeyPressed: function(key) {
      root.wakeRequested()
      if (key === "Backspace") passwordInput.remove(Math.max(0, passwordInput.cursorPosition - 1), passwordInput.cursorPosition)
      else if (key === "Enter") {
        var submitted = root.passwordText
        root.passwordTextEdited("")
        if (submitted.length > 0) root.submitPassword(submitted)
      } else passwordInput.insert(passwordInput.cursorPosition, key)
    }
  }
'''
lock_new = lock_new.rstrip()[:-1] + lock_addition + touch_area + '\n}\n'
lock_new = lock_new.replace('  onInputEnabledChanged: {', '  onInputEnabledChanged: {\n    if (!inputEnabled) keyboardVisible = false')
(here / "LockView.proposed.qml").write_text(lock_new)
(here / "lock-screen.patch").write_text(''.join(difflib.unified_diff(lock.splitlines(True), lock_new.splitlines(True), fromfile='LockView.qml', tofile='LockView.qml')))
(here / "zz-omarchy-tablet.conf.proposed").write_text('[Theme]\nCurrent=omarchy-tablet\nThemeDir=/usr/local/share/sddm/themes\n')
service_source = Path('/usr/share/omarchy/shell/plugins/lock/Service.qml').read_text()
for anchor in ['  property bool pendingSessionLock: false', '        onWakeRequested: root.runWake()', '    function isLocked(): string {']:
    if service_source.count(anchor) != 1:
        raise SystemExit('Unsupported Omarchy lock service; review before generating: ' + anchor)
service_new = service_source.replace('  property bool pendingSessionLock: false', '  signal keyboardRequested(bool visible)\n  property bool pendingSessionLock: false')
service_new = service_new.replace('        onWakeRequested: root.runWake()', '''        onWakeRequested: root.runWake()
        Connections {
          target: root
          function onKeyboardRequested(visible) { lockView.keyboardVisible = visible }
        }''', 1)
service_new = service_new.replace('    function isLocked(): string {', '''    function showKeyboard(): string {
      if (!root.locked) return "not-locked"
      root.keyboardRequested(true)
      return "ok"
    }
    function hideKeyboard(): string {
      if (!root.locked) return "not-locked"
      root.keyboardRequested(false)
      return "ok"
    }
    function isLocked(): string {''', 1)
(here / 'Service.proposed.qml').write_text(service_new)
(here / 'lock-service.patch').write_text(''.join(difflib.unified_diff(service_source.splitlines(True), service_new.splitlines(True), fromfile='Service.qml', tofile='Service.qml')))
print("Prepared SDDM theme and isolated lock-view UI proposal; nothing installed.")
