import tkinter as tk
from tkinter import ttk


class ModernSwitch(tk.Canvas):
    def __init__(self, parent, height=40, width=None, variable=None, command=None, enabled=True, **kwargs):
        self.height = height
        self.width = width if width else height * 2.2
        self.radius = height / 2
        self.thumb_diameter = height * 0.8
        self.thumb_radius = self.thumb_diameter / 2
        self.margin = (height - self.thumb_diameter) / 2

        super().__init__(parent, width=self.width, height=height, highlightthickness=0, **kwargs)

        self.variable = variable
        self.command = command

        self._on_color = "#2ecc71"
        self._off_color = "#e74c3c"
        self._disabled_color = "#cccccc"
        self._disabled_thumb_color = "#aaaaaa"
        self._thumb_color = "#ffffff"

        self._off_x = self.margin + self.thumb_radius
        self._on_x = self.width - self.margin - self.thumb_radius

        self._value = False
        self._animation_job = None
        self._animating = False

        self._track = self.create_oval(
            self.radius, self.margin,
            self.width - self.radius, self.height - self.margin,
            fill=self._off_color, outline=""
        )
        self._thumb = self.create_oval(
            self._off_x - self.thumb_radius, self.margin,
            self._off_x + self.thumb_radius, self.height - self.margin,
            fill=self._thumb_color, outline=""
        )

        self.enabled = enabled

        self.bind("<Button-1>", self._on_click)

        if self.variable:
            self.variable.trace_add("write", self._on_variable_change)
            self._value = self.variable.get()

        self._refresh_visuals()

    def _refresh_visuals(self):
        """Forces the widget to match current state (used for init and disabling)."""
        if not self._enabled:
            self.itemconfig(self._track, fill=self._disabled_color)
            self.itemconfig(self._thumb, fill=self._disabled_thumb_color)
        else:
            track_color = self._on_color if self._value else self._off_color
            self.itemconfig(self._track, fill=track_color)
            self.itemconfig(self._thumb, fill=self._thumb_color)

        thumb_x = self._on_x if self._value else self._off_x
        self.coords(self._thumb, thumb_x - self.thumb_radius, self.margin, thumb_x + self.thumb_radius, self.height - self.margin)

    def _on_click(self, event):
        if not self.enabled:
            return

        if self._animation_job:
            self.after_cancel(self._animation_job)

        self._value = not self._value

        if self.variable:
            self.variable.set(self._value)

        self._animate()

        if callable(self.command):
            self.command()

    def _on_variable_change(self, *args):
        new_value = bool(self.variable.get())
        if new_value != self._value:
            self._value = new_value
            self._animate()

    def _animate(self):
        if not self._enabled:
            self.itemconfig(self._track, fill=self._disabled_color)
            return

        steps = 12
        duration = 160

        start_x = self._off_x if self._value else self._on_x
        end_x = self._on_x if self._value else self._off_x
        start_color = self._on_color if self._value else self._off_color
        end_color = self._off_color if self._value else self._on_color

        start_rgb = self._hex_to_rgb(start_color)
        end_rgb = self._hex_to_rgb(end_color)

        def step(i):
            if i >= steps:
                self.coords(self._thumb, end_x - self.thumb_radius, self.margin, end_x + self.thumb_radius, self.height - self.margin)
                self.itemconfig(self._track, fill=end_color)
                self._animation_job = None
                return

            progress = i / (steps - 1)
            current_x = start_x + (end_x - start_x) * progress

            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * progress)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * progress)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * progress)
            current_color = self._rgb_to_hex(r, g, b)

            self.coords(self._thumb, current_x - self.thumb_radius, self.margin, current_x + self.thumb_radius, self.height - self.margin)
            self.itemconfig(self._track, fill=current_color)

            self._animation_job = self.after(int(duration / steps), lambda i=i: step(i))

        step(0)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, r, g, b):
        return f"#{r:02x}{g:02x}{b:02x}"

    def get(self):
        if self.variable:
            return self.variable.get()
        return self._value

    def set(self, value):
        if self._value != value:
            self._value = value
            if self.variable:
                self.variable.set(value)
            self._animate()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self._refresh_visuals()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Modern Switch Demo")

    var1 = tk.BooleanVar(value=True)
    var2 = tk.BooleanVar(value=False)
    var3 = tk.BooleanVar(value=False)

    frame = ttk.Frame(root, padding=20)
    frame.pack()

    ttk.Label(frame, text="Active Switch:").grid(row=0, column=0, sticky="w", pady=5)
    switch1 = ModernSwitch(frame, variable=var1, height=40)
    switch1.grid(row=0, column=1, pady=5)

    ttk.Label(frame, text="Disabled Switch:").grid(row=1, column=0, sticky="w", pady=5)
    switch2 = ModernSwitch(frame, variable=var2, height=40, enabled=False)
    switch2.grid(row=1, column=1, pady=5)

    ttk.Label(frame, text="Linked Switch:").grid(row=2, column=0, sticky="w", pady=5)
    switch3 = ModernSwitch(frame, variable=var3, height=40)
    switch3.grid(row=2, column=1, pady=5)

    status_label = ttk.Label(frame, text="Status: OFF")
    status_label.grid(row=3, column=0, columnspan=2, pady=10)

    def update_status(*args):
        status_label.config(text=f"Status: {'ON' if var3.get() else 'OFF'}")

    var3.trace_add("write", update_status)

    def on_close():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Escape>", lambda e: on_close())
    root.bind("<q>", lambda e: on_close())
    root.bind("<Q>", lambda e: on_close())

    root.mainloop()
