import QtQuick

Rectangle {
  id: root
  color: "#20232a"
  property bool shifted: false
  property bool symbols: false
  signal keyPressed(string key)
  signal hideRequested()

  readonly property var rows: symbols
    ? ["1234567890", "!@#$%^&*()", "-_=+[]{}\\|", ";:'\"`~,.<>/?"]
    : ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

  Column {
    anchors { fill: parent; margins: 6 }
    spacing: 5
    Repeater {
      model: root.rows
      Row {
        required property string modelData
        readonly property int keyCount: modelData.length
        width: parent.width
        spacing: 5
        Repeater {
          model: modelData.split("")
          Rectangle {
            required property string modelData
            width: (parent.width - 5 * (parent.keyCount - 1)) / parent.keyCount
            height: (root.height - 12 - 5 * root.rows.length) / (root.rows.length + 1)
            radius: 8
            color: keyTouch.pressed ? "#66748c" : "#343b48"
            Text {
              anchors.centerIn: parent
              text: root.shifted && !root.symbols ? modelData.toUpperCase() : modelData
              color: "white"
              font.pixelSize: 24
            }
            MouseArea {
              id: keyTouch
              anchors.fill: parent
              onClicked: root.keyPressed(root.shifted && !root.symbols ? modelData.toUpperCase() : modelData)
            }
          }
        }
      }
    }
    Row {
      width: parent.width
      spacing: 5
      Repeater {
        model: ["Shift", "123/ABC", "Space", "Backspace", "Enter", "Hide"]
        Rectangle {
          required property string modelData
          width: (parent.width - 25) / 6
          height: (root.height - 12 - 5 * root.rows.length) / (root.rows.length + 1)
          radius: 8
          color: specialTouch.pressed ? "#66748c" : modelData === "Enter" ? "#426852" : "#343b48"
          Text {
            anchors.centerIn: parent
            text: modelData === "Shift" && root.shifted ? "SHIFT" : modelData
            color: "white"
            font.pixelSize: Math.min(18, (parent.width - 8) / 5.5)
          }
          MouseArea {
            id: specialTouch
            anchors.fill: parent
            onClicked: {
              if (modelData === "Shift") root.shifted = !root.shifted
              else if (modelData === "123/ABC") root.symbols = !root.symbols
              else if (modelData === "Hide") root.hideRequested()
              else root.keyPressed(modelData === "Space" ? " " : modelData)
            }
          }
        }
      }
    }
  }
}
