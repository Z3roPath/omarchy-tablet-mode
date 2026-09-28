#!/usr/bin/env python3
"""Generate touch UI inside Omarchy's own authenticated Polkit surface."""
from pathlib import Path

here=Path(__file__).resolve().parent
source=Path('/usr/share/omarchy/shell/plugins/polkit/PolkitAgent.qml').read_text()
anchors=['  property bool closing: false','    submitted = false\n    passwordInput.text = ""\n    refreshLidState()', '      anchors.horizontalCenterOffset: root.shakeOffset']
for anchor in anchors:
    if source.count(anchor)!=1: raise SystemExit('Unsupported Omarchy Polkit source; inspect before patching: '+anchor)
text=source.replace(anchors[0],'  property bool keyboardVisible: true\n'+anchors[0])
text=text.replace(anchors[1],'    keyboardVisible = true\n'+anchors[1])
text=text.replace(anchors[2],anchors[2]+'\n      anchors.verticalCenterOffset: touchKeys.visible ? -touchKeys.height / 2 : 0')
text=text.replace('  property bool keyboardVisible: true', '''  IpcHandler {
    target: "tablet-auth"
    function showKeyboard(): string {
      if (!root.dialogVisible) return "not-active"
      root.keyboardVisible = true
      return "ok"
    }
    function hideKeyboard(): string {
      if (!root.dialogVisible) return "not-active"
      root.keyboardVisible = false
      return "ok"
    }
  }
  property bool keyboardVisible: true''')
addition='''
    // Keyboard lives inside the same exclusive authentication surface.
    Row {
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.bottom: touchKeys.visible ? touchKeys.top : parent.bottom
      anchors.bottomMargin: 12
      spacing: 8
      Repeater {
        model: ["Keyboard", "Authenticate", "Cancel"]
        Rectangle {
          required property string modelData
          width: Math.min(180, (panel.width - 32) / 3); height: 52; radius: 10
          color: modelData === "Cancel" ? "#683e45" : "#343b48"
          Text {
            anchors.centerIn: parent; color: "white"; font.pixelSize: 18
            text: modelData === "Keyboard" && root.keyboardVisible ? "Hide keyboard" : modelData
          }
          MouseArea {
            anchors.fill: parent
            onClicked: {
              if (modelData === "Keyboard") root.keyboardVisible = !root.keyboardVisible
              else if (modelData === "Cancel") root.cancelRequest()
              else if (root.responseRequired && !root.submitted && !root.errorFlash) root.submitResponse()
            }
          }
        }
      }
    }
    TouchKeyboard {
      id: touchKeys
      anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
      height: Math.min(270, panel.height * 0.32)
      visible: root.keyboardVisible && !root.fingerprintMode
      enabled: root.responseRequired && !root.submitted && !root.errorFlash
      onHideRequested: root.keyboardVisible = false
      onKeyPressed: function(key) {
        root.refocus()
        if (key === "Backspace") passwordInput.remove(Math.max(0, passwordInput.cursorPosition - 1), passwordInput.cursorPosition)
        else if (key === "Enter") root.submitResponse()
        else passwordInput.insert(passwordInput.cursorPosition, key)
      }
    }
'''
# Append inside PanelWindow, preserving exclusive focus, masking and flow.submit.
assert text.rstrip().endswith('  }\n}')
text=text.rstrip()[:-5]+addition+'  }\n}\n'
(here/'PolkitAgent.proposed.qml').write_text(text)
print('Prepared embedded Polkit keyboard; authorization and password masking unchanged')
