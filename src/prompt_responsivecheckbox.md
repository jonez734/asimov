Role: You are an expert Python developer specializing in Tkinter and UI/UX design.

Task: Create a custom, production-ready Tkinter widget class named ResponsiveCheckbox that inherits from tk.Canvas.

Core Requirements:

    Visual Logic: The widget should be a checkbox where the background and indicator change color based on state: Green (#2ecc71) for Checked/True, Red (#e74c3c) for Unchecked/False, and Gray (#95a5a6) for Disabled.

    Smooth Animation: * Implement color interpolation (fading) using root.after over 10 steps (approx. 200ms).

        Implement an animated "hand-drawn" checkmark that grows from left-to-right when checked and disappears when unchecked.

    Responsiveness: All internal coordinates (box size, checkmark path, and font size) must be calculated as percentages of the widget’s height to ensure it scales perfectly at any size.

    State Management:

        The widget must accept a tk.BooleanVar via a variable parameter.

        Include a command parameter for a callback function.

        Best Practice: Before executing the callback, use if callable(command): to verify it is a function.

    Interactive Elements:

        Support an enabled state. If enabled=False, ignore clicks and apply a grayscale theme.

        Include hover effects (<Enter>/<Leave>) that thicken the box border and change the cursor to hand2 only when enabled.

    Code Quality:

        Use modern Python 3.6+ trace_add for variable tracking.

        Ensure the code is encapsulated within a single class for easy import.

        Use bit-shifting logic to convert 16-bit winfo_rgb values to 8-bit hex strings for interpolation.

Output: Provide the full Python code, including a clear usage example in a if __name__ == "__main__": block that demonstrates a normal checkbox, a disabled checkbox, and a toggle button to enable/disable them.
