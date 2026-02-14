import tkinter as tk

class ColorCheckBox(tk.Canvas):
    def __init__(self, master, label_text="", variable=None, command=None, **kwargs):
        self.width = kwargs.pop('width', 100)  # Wider to accommodate text
        self.height = kwargs.pop('height', 30)
        
        super().__init__(master, width=self.width, height=self.height, 
                         highlightthickness=0, bd=0, **kwargs)
        
        self.command = command
        self.variable = variable if variable else tk.BooleanVar(value=False)
        
        # Draw the checkbox (the small square)
        # Positioned at the left (x=5)
        self.rect = self.create_rectangle(5, 5, 25, 25, outline="black", width=1)
        
        # Draw the text label next to the box
        self.text_id = self.create_text(35, 15, text=label_text, anchor="w", font=("Arial", 10))
        
        self.variable.trace_add("write", self._update_color)
        self._update_color()
        
        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)

    def _update_color(self, *args):
        """Updates both the box and the widget background."""
        if self.variable.get():
            main_color = "#2ecc71"    # Vivid Green
            bg_color = "#e8f8f0"      # Very Light Green
        else:
            main_color = "#e74c3c"    # Vivid Red
            bg_color = "#fdedec"      # Very Light Red
            
        # Update the box fill
        self.itemconfig(self.rect, fill=main_color)
        # Update the entire widget's background
        self.config(bg=bg_color)

    def _on_click(self, event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command(self.variable.get())

    def _on_hover_enter(self, event=None):
        self.itemconfig(self.rect, width=2)
        self.config(cursor="hand2")

    def _on_hover_leave(self, event=None):
        self.itemconfig(self.rect, width=1)

# --- Usage Example ---
root = tk.Tk()
root.geometry("300x150")
root.title("Themed Widget")

# Create two instances with different labels
cb1 = ColorCheckBox(root, label_text="Power System", width=150)
cb1.pack(pady=10)

cb2 = ColorCheckBox(root, label_text="Safety Lock", width=150)
cb2.pack(pady=10)

root.mainloop()
