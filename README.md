# Omarchy Tablet Mode

A local touch controller for **Omarchy's Quickshell side bar and Hyprland Lua configuration**. Experimental: verified on Hyprland 0.56.2 with a Surface touchscreen, scale 2, portrait and landscape. Other hardware needs testing. Legacy Waybar, older Hyprland `.conf` setups, arbitrary docks, and other authentication agents are not supported by this installer.

## What it does

- A large tablet icon on the ordinary side dock enters Tablet Mode.
- Individual buttons float on a transparent 80 logical pixel bottom surface providing Apps, Browser, Files, Terminal, E-Ink, Keyboard, Previous, Next, and Exit.
- Desktop wvkbd uses a compact 250 pixel height. The keyboard and bottom controls reserve separate screen areas.
- Four fingers up shows the keyboard and enters Tablet Mode; four down hides it. The existing Hyprgrass Lua plugin must already be loaded.
- Swipe horizontally across the bottom bar to hide it without exiting Tablet Mode. Swipe inward from either bottom corner to reveal it.
- The ordinary side dock hides only in Tablet Mode. Drag inward from the middle of its screen edge to reveal it. It hides after six idle seconds and stays open during dock interaction.
- Reveal targets are **completely invisible**, reserve no layout space, and exist only in Tablet Mode: 60×72 pixels at each bottom corner, and 18×180 pixels at the middle of the dock edge. Corners move just above the OSK when it is open.
- Exit restores the previous dock visibility, screen shader, and keyboard visibility. Login begins with Tablet Mode off. A service crash restarts the UI and preserves bottom-bar hidden state.
- Optional embedded keyboards support the official Omarchy lock screen, Polkit administrator dialog, and SDDM Omarchy login theme.

**Existing gestures are preserved.** This package does not replace your touchscreen mapping, rotation daemon, three-finger workspace bindings, or two-finger twist implementation. A custom Hyprgrass twist plugin is still required if your existing touchscreen setup uses it; this project does not distribute machine-specific plugin binaries. Stock touchscreen twist support is not promised.

## Prerequisites and inspection

Use a current Omarchy installation with its Quickshell bar positioned left or right, Lua `hyprland.lua` sourcing `input.lua`, a Wayland session, systemd user services, `qs`, `jq`, `flock`, and a compatible **wvkbd** executable. Keep your existing OSK service if it uses wvkbd; another OSK backend is refused. The installer reports compositor version, touchscreen count, loaded Hyprgrass, and keyboard path before changing anything. It never downloads dependencies automatically.

For four-finger gestures, install a Hyprgrass build matching your exact Hyprland ABI and Lua API using its upstream instructions. Existing three-finger and twist settings remain untouched. An upward four-finger gesture currently matches **anywhere**: Hyprgrass does not offer a pattern combining a bottom-edge start with a finger count. Keyboard buttons are the fallback if your hardware cannot track four fingers.

## Install

Clone this repository and run as your regular desktop user:

```sh
python3 install.py --dry-run --with-lock --with-polkit
python3 install.py --with-lock --with-polkit
```

Omit either optional flag to leave that authentication UI alone. The installer makes backups before changing files, clones built-in plugins through `omarchy plugin clone`, and adds a modular gesture include. It keeps your other bar entries and input settings. After optional authentication changes, while unlocked with no administrator dialog open, run:

```sh
omarchy restart shell
```

This restarts the Omarchy shell, not Hyprland. The installer never locks, logs out, reboots, or restarts the compositor. Open the tablet icon to begin. Re-running updates managed files while retaining the original backup; if you edited them afterward, it stops for review.

Runtime files: `~/.local/share/omarchy-tablet-mode/`. Backups and installation manifest: `~/.local/state/omarchy-tablet-mode/`. Original backups are retained after uninstall. On an existing manual installation, rollback returns to the configuration immediately before this installer first ran; use older manual backups for earlier history.

## Optional startup login keyboard

Only the **Omarchy SDDM theme on the inspected Wayland greeter stack** is supported. Generate a theme from the installed version; generation stops if expected source anchors changed:

```sh
python3 review/login/prepare.py
sddm-greeter-qt6 --test-mode --theme "$PWD/review/login/theme"
python3 install-login.py install --dry-run
sudo python3 install-login.py install
```

`pkexec /usr/bin/python3 "$PWD/install-login.py" install` is another legitimate authentication route after the touch Polkit clone is loaded. Select **Keyboard** on the sign-in screen, then use Enter on its keyboard to submit. Authentication still uses the original `sddm.login` route. No PAM, credentials, autologin, or greeter compositor settings are changed. The new theme applies at the next user-initiated sign-in; SDDM is not restarted by the installer.

The optional system installer manages only `/usr/local/share/sddm/themes/omarchy-tablet` and `/etc/sddm.conf.d/zz-omarchy-tablet.conf`. Root backup/hash records are under `/var/lib/omarchy-tablet-mode/`. Keep a recovery route until you have tested real sign-in on your machine.

## Authentication keyboards

A desktop layer-shell keyboard cannot receive taps beneath Omarchy's full-screen exclusive Polkit surface or protected session-lock surface. The optional supported clones embed their keyboard **inside the authentication surface**. The normal password submission, masking, and authorization remain unchanged; no unrestricted key injection is used. Four-finger commands route to the active administrator keyboard when the touch Polkit clone is present, with guarded IPC that cannot open the dialog while idle.

These embedded keyboards provide printable **ASCII**: lower/uppercase, digits, punctuation, space, Backspace, Enter, and Hide. Credentials using another alphabet require a suitable locale keyboard before relying on touch-only login. Other agents, greetd, GDM, and other OSKs need separate integrations. Real touchscreen authentication and sign-in must be tested by the user; software loading is not proof of successful authentication.

## Configuration

Create `~/.config/omarchy-tablet-mode/settings` for the tablet UI service:

```ini
OMARCHY_TABLET_BAR_HEIGHT=80
OMARCHY_TABLET_DOCK_TIMEOUT=6000
```

Restart `omarchy-tablet-mode-ui.service` while Tablet Mode is active to apply UI values. Bar height is clamped to 64–120 pixels; dock timeout is in milliseconds with a minimum of 2000. Keyboard height is `-H`/`-L` in `tablet-keyboard.service`; reload systemd and restart that service after editing. The installer defaults to 250 and resets it on a managed update. Nine buttons need a screen roughly 720 logical pixels wide for comfortable labels. Settings use Omarchy's usual directories under HOME.

The existing `~/.local/bin/omarchy-reader-mode` is used if present. Otherwise bundled reader shaders provide normal paper, inverted paper, and off modes. This is a shader effect, not hardware E-Ink. Browser/terminal use Omarchy launchers; Files uses your default file manager. Workspace navigation uses Hyprland's Lua focus dispatcher.

## Troubleshooting and physical checks

```sh
~/.local/share/omarchy-tablet-mode/bin/tablet-mode status
systemctl --user status omarchy-tablet-mode-ui.service tablet-keyboard.service
hyprctl configerrors
cat ~/.local/state/omarchy-tablet-mode/gesture.log
journalctl --user -u omarchy-tablet-mode-ui.service
```

Gesture logs contain only receipt, show/hide intent, and result: no coordinates, typed keys, or passwords. No log entry means the gesture recognizer did not fire. An error result means the controller or OSK failed. A failed configuration reload or changed plugin source requires reviewing compatibility before proceeding.

Test on your own hardware: tablet-icon tap reliability; all bottom actions; four-finger up/down; sideways bottom-bar dismissal; inward corner and side-edge reveals; both orientations; dock timeout; UI service restart; reader/keyboard/dock restoration on exit. Separately test lock/unlock, touch typing at a real administrator request, cancellation, and startup sign-in. Never use a real password in a mock preview.

## Uninstall and rollback

```sh
python3 install.py --uninstall --dry-run
python3 install.py --uninstall
# Optional system greeter rollback:
sudo python3 install-login.py rollback
```

Uninstall checks for edits since installation and refuses to overwrite them. Review any conflicts first. `--force` on desktop uninstall explicitly allows restoring old snapshots over newer edits. The system rollback has no force bypass and stops if its protected files changed. Restart the unlocked Omarchy shell after restoring cloned services. Original customizations and service state are restored; backup files remain available.

## Development and validation

```sh
python3 tests/check.py
```

The check covers syntax and backup/rollback behavior, including preservation of existing files and refusal to erase later edits. Local validation also checked live layer geometry, explicit keyboard show/hide, dock timeout, hidden state across UI restart, and clean exit. No claim of universal hardware or authentication compatibility is made. Generated copies of installed themes and authentication plugins are intentionally excluded from Git; the generators apply minimal changes to the local Omarchy version.
