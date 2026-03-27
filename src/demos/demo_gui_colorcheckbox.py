import tkinter as tk


class ColorCheckBox(tk.Canvas):
    def __init__(self, master, label_text="", variable=None, **kwargs):
        self.width = kwargs.pop("width", 150)
        self.height = kwargs.pop("height", 40)
        super().__init__(
            master,
            width=self.width,
            height=self.height,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )

        self.variable = variable if variable else tk.BooleanVar(value=False)

        # Colors: (Box Color, Background Color)
        self.off_colors = ("#e74c3c", "#fdedec")  # Red palette
        self.on_colors = ("#2ecc71", "#e8f8f0")  # Green palette

        # UI Elements
        self.rect = self.create_rectangle(10, 10, 30, 30, outline="#333333", width=1)
        self.text = self.create_text(
            40, 20, text=label_text, anchor="w", font=("Arial", 10, "bold")
        )

        # Animation state
        self._animation_job = None

        self.variable.trace_add("write", lambda *a: self.animate_transition())
        self._set_initial_state()

        self.bind("<Button-1>", lambda e: self.variable.set(not self.variable.get()))
        self.bind("<Enter>", lambda e: self.itemconfig(self.rect, width=2))
        self.bind("<Leave>", lambda e: self.itemconfig(self.rect, width=1))

    def _set_initial_state(self):
        box, bg = self.on_colors if self.variable.get() else self.off_colors
        self.itemconfig(self.rect, fill=box)
        self.config(bg=bg)

    def animate_transition(self):
        """Starts the color interpolation process."""
        if self._animation_job:
            self.after_cancel(self._animation_job)

        # Determine start and end targets
        if self.variable.get():
            start_box, start_bg = self.off_colors
            end_box, end_bg = self.on_colors
        else:
            start_box, start_bg = self.on_colors
            end_box, end_bg = self.off_colors

        self._step_transition(start_box, end_box, start_bg, end_bg, 0)

    def _step_transition(self, s_box, e_box, s_bg, e_bg, step):
        """Interpolates colors over 10 steps (200ms total)."""
        total_steps = 10
        ratio = step / total_steps

        # Calculate intermediate hex codes
        current_box = self._interpolate_color(s_box, e_box, ratio)
        current_bg = self._interpolate_color(s_bg, e_bg, ratio)

        self.itemconfig(self.rect, fill=current_box)
        self.config(bg=current_bg)

        if step < total_steps:
            self._animation_job = self.after(
                20, self._step_transition, s_box, e_box, s_bg, e_bg, step + 1
            )

    def _interpolate_color(self, c1, c2, ratio):
        """Mathematical blend between two hex colors."""
        r1, g1, b1 = self.winfo_rgb(c1)
        r2, g2, b2 = self.winfo_rgb(c2)

        # winfo_rgb returns 16-bit values (0-65535), we need 8-bit (0-255)
        r = int(r1 + (r2 - r1) * ratio) >> 8
        g = int(g1 + (g2 - g1) * ratio) >> 8
        b = int(b1 + (b2 - b1) * ratio) >> 8

        return f"#{r:02x}{g:02x}{b:02x}"


# --- Usage ---
root = tk.Tk()
root.title("Smooth Transition Checkbox")
root.geometry("300x200")

cb = ColorCheckBox(root, label_text="System Online")
cb.pack(pady=20)

tk.Label(root, text="Click the box above to see the fade!").pack()
root.mainloop()
