# Master Widget Prompt: Modern Animated Switch

**Role:** You are an expert Python developer specializing in Tkinter and modern UI component design.

**Task:** Create a custom, high-performance Tkinter widget class named `ModernSwitch` that inherits from `tk.Canvas`. This widget should mimic a "pill-shaped" toggle switch found in modern mobile operating systems.

**Core Requirements:**
1. **Visual Logic:**
   - The widget should consist of a pill-shaped track and a circular "thumb" (slider).
   - **Colors:** When ON, the track should be Green (`#2ecc71`). When OFF, the track should be Red (`#e74c3c`). When DISABLED, the track should be Gray (`#bdc3c7`).
   - The thumb should be white (`#ffffff`) and slightly smaller than the track height to create a margin.

2. **Smooth Animation:**
   - Implement **simultaneous** animations: The thumb must slide horizontally while the track background color interpolates (fades).
   - Use `root.after` to manage a 10-15 step animation sequence over approximately 150-200ms.
   - Ensure the animation is "non-blocking" to the main GUI thread.

3. **Responsive Geometry:**
   - All dimensions (track radius, thumb diameter, sliding distance) must be calculated relative to the widget `height`.
   - The width should default to `height * 2.2` unless specified otherwise.
   - Use percentage-based positioning to determine the thumb's "On" and "Off" coordinates.

4. **State & Interaction:**
   - Support `tk.BooleanVar` for state tracking via a `variable` parameter.
   - Support an optional `command` callback. **Best Practice:** Verify the command using `if callable(command):` before execution.
   - Handle an `enabled` state: if `False`, clicks must be ignored and the widget must use a grayscale palette.

5. **Technical Constraints:**
   - Use `trace_add("write", ...)` to ensure the switch moves even if the variable is changed externally.
   - Handle rapid clicking by canceling any existing `after` jobs (`after_cancel`) before starting a new animation.
   - Use the `coords()` method for movement and `itemconfig()` for color updates.

**Output:** Provide the full Python class and a demo script showing three switches: one active, one disabled, and one linked to a label displaying the current status.
