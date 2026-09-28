# Optional touch authentication integrations

`TouchKeyboard.qml` is embedded in the official Omarchy lock and Polkit user clones and an optional generated SDDM Omarchy theme. `prepare.py` generates local theme/lock copies; `prepare-polkit.py` generates the administrator-dialog clone UI. Generated files and theme artwork are not published. Run the desktop installer with `--with-lock --with-polkit`, then restart the unlocked Omarchy shell. Source anchor checks refuse unsupported versions.

The root theme installer and rollback manage only the added theme and theme selection file; they preserve existing PAM, credentials, autologin, and session configuration. See the main README for exact commands and supported environments. The keyboard covers printable ASCII. Real touchscreen unlock, administrator authentication, and login remain user hardware tests. Never type a real password into a mock preview.
