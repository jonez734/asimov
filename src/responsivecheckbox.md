# ResponsiveCheckbox Documentation

The `ResponsiveCheckbox` is a custom, high-fidelity Tkinter widget designed to replace the standard checkbox with a modern, animated toggle. It features smooth color transitions, a dynamic "hand-drawn" checkmark, and full responsiveness to varying dimensions.

---

## Overview

Unlike the native `tk.Checkbutton`, this widget is built on a `tk.Canvas`. This allows for complete control over the "box" aesthetic, enabling a green (active), red (inactive), and gray (disabled) color scheme that applies to both the indicator and the widget's background.

### Key Features
* **Smooth RGB Transitions:** Colors fade linearly between states rather than snapping instantly.
* **Proportional Scaling:** Internal elements (box size, checkmark thickness, and font) are calculated as percentages of the widget's height.
* **Event-Driven:** Supports `BooleanVar` tracking and a `command` callback.
* **Input Safety:** Utilizes `callable()` checks to ensure stability when executing callbacks.

---

## Technical Specifications

### Initialization Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `master` | `tk.Widget` | *Required* | The parent container (Frame, Root, etc.). |
| `label_text` | `str` | `""` | The text displayed next to the checkbox. |
| `variable` | `tk.BooleanVar` | `None` | Tracks the state. A new one is created if not provided. |
| `command` | `function` | `None` | A function called when the state changes. Receives one `bool` argument. |
| `enabled` | `bool` | `True` | Sets the initial interactivity state of the widget. |
| `height` | `int` | `40` | The total height of the widget (used for scaling). |
| `width` | `int` | `220` | The total width of the canvas. |

### Public Methods

* **`set_state(enabled=True)`**
    * Toggles the widget between active and disabled modes. 
    * When `False`, the widget ignores clicks, changes to a gray palette, and fades the text.
* **`animate()`**
    * Triggered automatically via variable traces, but can be called manually to refresh the visual state based on the current `BooleanVar` value.

---

## Architecture & Logic

The widget operates on a state-machine principle. Every state change triggers a 10-step interpolation process via the `root.after` event loop.

1. **Coordinate Interpolation:** The checkmark is drawn in two phases: the "down-stroke" (0–40% of the animation) and the "up-stroke" (40–100%).
2. **Color Blending:** Hexadecimal colors are converted to 16-bit RGB, blended mathematically, and bit-shifted back to 8-bit hex for rendering.
3. **Input Handling:** Hover events (`<Enter>`, `<Leave>`) modify the rectangle's outline width to provide a "focus" effect.

---

## Implementation Example

```python
import tkinter as tk
from custom_widgets import ResponsiveCheckbox

def on_toggle(state):
    print(f"System is now {'Active' if state else 'Offline'}")

root = tk.Tk()

# Standard implementation
system_check = ResponsiveCheckbox(
    root, 
    label_text="Enable Propulsion", 
    height=50, 
    command=on_toggle
)
system_check.pack(pady=20)

# Disabling the widget externally
system_check.set_state(enabled=False)

root.mainloop()
```
