import tkinter as tk

class ResponsiveCheckbox(tk.Canvas):
    def __init__(self, master, label_text="", variable=None, enabled=True, **kwargs):
        height = kwargs.pop('height', 40)
        width = kwargs.pop('width', 220)
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, **kwargs)

        self.variable = variable if variable else tk.BooleanVar(value=False)
        self.enabled = enabled
        self.h = height
        self.padding = self.h * 0.2
        self.box_dim = self.h - (self.padding * 2)

        # Color Palettes
        self.off_colors = ("#e74c3c", "#fdedec") # Red
        self.on_colors  = ("#2ecc71", "#e8f8f0") # Green
        self.disabled_colors = ("#95a5a6", "#ecf0f1") # Gray

        self.rel_points = [(0.25, 0.5), (0.45, 0.75), (0.75, 0.35)]

        # UI Elements
        self.rect = self.create_rectangle(
            self.padding, self.padding, 
            self.padding + self.box_dim, self.padding + self.box_dim, 
            outline="#333333", width=1
        )

        self.check_line = self.create_line(0, 0, 0, 0, fill="white", 
                                          width=max(2, int(self.h/15)), 
                                          capstyle="round", joinstyle="round", state="hidden")

        self.text = self.create_text(self.padding * 2 + self.box_dim, self.h/2, 
                                     text=label_text, anchor="w", 
                                     font=("Arial", int(self.h/3), "bold"))

        self._animation_job = None
        self.variable.trace_add("write", lambda *a: self.animate())
        self._refresh_visuals()

        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)

    def _refresh_visuals(self):
        """Forces the widget to match current state (used for init and disabling)."""
        if not self.enabled:
            box_c, bg_c = self.disabled_colors
            txt_c = "#bdc3c7"
        else:
            is_on = self.variable.get()
            box_c, bg_c = self.on_colors if is_on else self.off_colors
            txt_c = "black"

        self.itemconfig(self.rect, fill=box_c)
        self.config(bg=bg_c)
        self.itemconfig(self.text, fill=txt_c)

        if self.variable.get() and self.enabled:
            self.itemconfig(self.check_line, state="normal")
            self.coords(self.check_line, *self._get_abs_check_coords(1.0))
        else:
            self.itemconfig(self.check_line, state="hidden")

    def set_state(self, enabled=True):
        """Public method to enable or disable the widget."""
        self.enabled = enabled
        self._refresh_visuals()

    def _on_click(self, event):
        if self.enabled:
            self.variable.set(not self.variable.get())

    def _on_hover_enter(self, event):
        if self.enabled:
            self.itemconfig(self.rect, width=2)
            self.config(cursor="hand2")

    def _on_hover_leave(self, event):
        self.itemconfig(self.rect, width=1)
        self.config(cursor="")

    def _get_abs_check_coords(self, ratio):
        bx, by, d = self.padding, self.padding, self.box_dim
        p1, p2, p3 = self.rel_points
        if ratio < 0.4:
            sub = ratio / 0.4
            ex = bx + (p1[0] + (p2[0] - p1[0]) * sub) * d
            ey = by + (p1[1] + (p2[1] - p1[1]) * sub) * d
            return (bx+p1[0]*d, by+p1[1]*d, ex, ey)
        else:
            sub = (ratio - 0.4) / 0.6
            ex = bx + (p2[0] + (p3[0] - p2[0]) * sub) * d
            ey = by + (p2[1] + (p3[1] - p2[1]) * sub) * d
            return (bx+p1[0]*d, by+p1[1]*d, bx+p2[0]*d, by+p2[1]*d, ex, ey)

    def animate(self):
        if not self.enabled: return
        if self._animation_job: self.after_cancel(self._animation_job)
        is_on = self.variable.get()
        s_box, s_bg = self.on_colors if not is_on else self.off_colors
        e_box, e_bg = self.off_colors if not is_on else self.on_colors
        self._step(s_box, e_box, s_bg, e_bg, 0, is_on)

    def _step(self, s_box, e_box, s_bg, e_bg, step, becoming_on):
        total = 10
        ratio = step / total
        self.itemconfig(self.rect, fill=self._interpolate(s_box, e_box, ratio))
        self.config(bg=self._interpolate(s_bg, e_bg, ratio))
        
        if becoming_on:
            self.itemconfig(self.check_line, state="normal")
            self.coords(self.check_line, *self._get_abs_check_coords(ratio))
        elif step == 0:
            self.itemconfig(self.check_line, state="hidden")

        if step < total:
            self._animation_job = self.after(20, self._step, s_box, e_box, s_bg, e_bg, step+1, becoming_on)

    def _interpolate(self, c1, c2, ratio):
        r1, g1, b1 = self.winfo_rgb(c1)
        r2, g2, b2 = self.winfo_rgb(c2)
        r, g, b = [int(start + (end - start) * ratio) >> 8 for start, end in [(r1, r2), (g1, g2), (b1, b2)]]
        return f'#{r:02x}{g:02x}{b:02x}'

# --- Usage Example ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Disabled State Demo")

    cb = ResponsiveCheckbox(root, label_text="Main Reactor", height=50)
    cb.pack(pady=20)

    # Toggle button to enable/disable the checkbox
    def toggle_lock():
        new_state = not cb.enabled
        cb.set_state(new_state)
        btn.config(text="Enable Widget" if not new_state else "Disable Widget")

    btn = tk.Button(root, text="Disable Widget", command=toggle_lock)
    btn.pack()

    root.mainloop()
