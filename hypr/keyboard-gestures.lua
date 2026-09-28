-- Touchscreen gestures handled by the already loaded Hyprgrass plugin.
-- Hyprgrass's edge matcher has no finger count, so these use its four-finger swipe matcher.
local controller = string.format("%q", os.getenv("HOME") .. "/.local/share/omarchy-tablet-mode/bin/tablet-mode")
if hl.plugin.hyprgrass then
  hl.plugin.hyprgrass.bind({
    pattern = { kind = "swipe", fingers = 4, direction = "up" },
    action = hl.dsp.exec_cmd(controller .. " gesture show"),
  })
  hl.plugin.hyprgrass.bind({
    pattern = { kind = "swipe", fingers = 4, direction = "down" },
    action = hl.dsp.exec_cmd(controller .. " gesture hide"),
  })
  hl.plugin.hyprgrass.bind({
    pattern = { kind = "swipe", fingers = 4, direction = "up" },
    locked = true,
    action = hl.dsp.exec_cmd("omarchy-shell lock showKeyboard"),
  })
  hl.plugin.hyprgrass.bind({
    pattern = { kind = "swipe", fingers = 4, direction = "down" },
    locked = true,
    action = hl.dsp.exec_cmd("omarchy-shell lock hideKeyboard"),
  })
  hl.exec_cmd(controller .. " bindings-ready")
end
