# asimov/main_dashboard.py

import argparse
import threading
import time
import queue
import cv2
import numpy as np
import pyvirtualcam
import tkinter as tk
from tkinter import ttk, filedialog
import json
from PIL import Image, ImageTk
from cvzone.FPS import FPS as CVZoneFPS

from . import io
from . import conf
from .base import scene
from .base import cap
from .base.common import ThreadSafeContext
from asimov.playingcard import cards

context = ThreadSafeContext()
logic_lock = threading.Lock()
_stop_event = threading.Event()
_modules = []

logic_fps = CVZoneFPS(avgCount=30)
render_fps = CVZoneFPS(avgCount=30)


# --- Tkinter Dashboard UI Components ---


def validate_float(proposed, min_val, max_val):
    if proposed == "":
        return True

    if "." in proposed:
        parts = proposed.split(".")
        if len(parts) != 2:
            return None
        if not parts[0].isdigit() or not parts[1].isdigit():
            return None
    else:
        if not proposed.isdigit():
            return None

    val = float(proposed)
    if val < min_val or val > max_val:
        return False

    return True


def make_scale_field(parent, section, key, meta, config_obj):
    frame = ttk.Frame(parent)

    var = tk.DoubleVar(value=config_obj[section][key])

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    scale = ttk.Scale(
        frame,
        from_=meta["min"],
        to=meta["max"],
        orient="horizontal",
        variable=var,
    )
    scale.pack(fill="x", expand=True, pady=(0, 5))

    value_label = ttk.Label(frame, text=f"Value: {var.get():.2f}")
    value_label.pack(anchor="w")

    entry_var = tk.StringVar(value=str(config_obj[section][key]))

    def on_scale_change(*args):
        val = var.get()
        value_label.config(text=f"Value: {val:.2f}")
        entry_var.set(f"{val:.2f}")
        config_obj[section][key] = val

    def on_entry_validate(proposed):
        result = validate_float(proposed, meta["min"], meta["max"])
        if result is True:
            config_obj[section][key] = float(proposed)
            var.set(float(proposed))
            value_label.config(text=f"Value: {proposed}")
        elif result is False:
            entry_var.set(str(var.get()))
        return result

    vcmd = (frame.register(on_entry_validate), "%P")

    entry = ttk.Entry(
        frame, textvariable=entry_var, validate="key", validatecommand=vcmd
    )
    entry.pack(fill="x")

    var.trace_add("write", on_scale_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def make_bool_field(parent, section, key, meta, config_obj):
    frame = ttk.Frame(parent)

    var = tk.BooleanVar(value=config_obj[section][key])

    check = ttk.Checkbutton(
        frame,
        text=meta.get("label", key),
        variable=var,
        command=lambda: config_obj[section][key].__class__(var.get()),
    )
    check.pack(anchor="w", padx=10, pady=5)

    # Disable widget if "enabled": False in meta
    if meta.get("enabled", True) is False:
        check.config(state="disabled")

    def on_change(*args):
        config_obj[section][key] = var.get()

    var.trace_add("write", on_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def make_int_field(parent, section, key, meta, config_obj):
    frame = ttk.Frame(parent)

    var = tk.IntVar(value=int(config_obj[section][key]))

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    scale = ttk.Scale(
        frame,
        from_=meta["min"],
        to=meta["max"],
        orient="horizontal",
        variable=var,
    )
    scale.pack(fill="x", expand=True, pady=(0, 5))

    value_label = ttk.Label(frame, text=f"Value: {var.get()}")
    value_label.pack(anchor="w")

    entry_var = tk.StringVar(value=str(config_obj[section][key]))

    def on_scale_change(*args):
        val = var.get()
        value_label.config(text=f"Value: {val}")
        entry_var.set(str(val))
        config_obj[section][key] = val

    def on_entry_validate(proposed):
        if proposed == "":
            return True
        if not proposed.isdigit():
            return None
        val = int(proposed)
        if val < meta["min"] or val > meta["max"]:
            return False
        config_obj[section][key] = val
        var.set(val)
        value_label.config(text=f"Value: {proposed}")
        return True

    vcmd = (frame.register(on_entry_validate), "%P")

    entry = ttk.Entry(
        frame, textvariable=entry_var, validate="key", validatecommand=vcmd
    )
    entry.pack(fill="x")

    var.trace_add("write", on_scale_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def make_enum_field(parent, section, key, meta, config_obj, on_change=None):
    frame = ttk.Frame(parent)

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    var = tk.StringVar(value=config_obj[section].get(key, ""))

    combo = ttk.Combobox(
        frame, values=meta.get("enum", []), textvariable=var, state="readonly", width=20
    )
    combo.pack(anchor="w", padx=10, pady=5)

    def on_select(event):
        val = var.get()
        config_obj[section][key] = val if val else None
        if on_change:
            on_change(section, key, val)

    combo.bind("<<ComboboxSelected>>", on_select)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def make_radio_field(parent, section, key, meta, config_obj, on_change=None):
    frame = ttk.Frame(parent)

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    var = tk.StringVar(value=config_obj[section].get(key, ""))

    options = meta.get("enum", [])
    radio_frame = ttk.Frame(frame)
    radio_frame.pack(anchor="w", padx=10, pady=5)

    for opt in options:
        rb = ttk.Radiobutton(
            radio_frame,
            text=opt,
            variable=var,
            value=opt,
            command=lambda v=var: _on_radio_change(
                v, section, key, config_obj, on_change
            ),
        )
        rb.pack(side="left", padx=5)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def _on_radio_change(var, section, key, config_obj, on_change):
    val = var.get()
    config_obj[section][key] = val if val else None
    if on_change:
        on_change(section, key, val)


def make_color_field(parent, section, key, meta, config_obj, on_change=None):
    frame = ttk.Frame(parent)

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    current_color = config_obj[section].get(key, [0, 255, 0])
    if isinstance(current_color, tuple):
        b, g, r = current_color
    else:
        r, g, b = current_color[0], current_color[1], current_color[2]

    color_frame = ttk.Frame(frame)
    color_frame.pack(anchor="w", padx=10, pady=5)

    var_b = tk.IntVar(value=b)
    var_g = tk.IntVar(value=g)
    var_r = tk.IntVar(value=r)

    ttk.Label(color_frame, text="B:").pack(side="left", padx=2)
    entry_b = ttk.Spinbox(color_frame, from_=0, to=255, textvariable=var_b, width=5)
    entry_b.pack(side="left", padx=5)

    ttk.Label(color_frame, text="G:").pack(side="left", padx=2)
    entry_g = ttk.Spinbox(color_frame, from_=0, to=255, textvariable=var_g, width=5)
    entry_g.pack(side="left", padx=5)

    ttk.Label(color_frame, text="R:").pack(side="left", padx=2)
    entry_r = ttk.Spinbox(color_frame, from_=0, to=255, textvariable=var_r, width=5)
    entry_r.pack(side="left", padx=5)

    def on_color_change(*args):
        try:
            b = var_b.get()
            g = var_g.get()
            r = var_r.get()
        except (ValueError, tk.TclError):
            return
        color = (b, g, r)
        config_obj[section][key] = color
        if on_change:
            on_change(section, key, color)

    var_b.trace_add("write", on_color_change)
    var_g.trace_add("write", on_color_change)
    var_r.trace_add("write", on_color_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def make_file_field(parent, section, key, meta, config_obj, on_change=None):
    frame = ttk.Frame(parent)

    label = ttk.Label(frame, text=meta.get("label", key))
    label.pack(anchor="w")

    file_frame = ttk.Frame(frame)
    file_frame.pack(anchor="w", padx=10, pady=5)

    var = tk.StringVar(value=config_obj[section].get(key, ""))

    entry = ttk.Entry(file_frame, textvariable=var, width=40)
    entry.pack(side="left", padx=5)

    def browse_file():
        filters = meta.get("filters", [("All files", "*.*")])
        filename = filedialog.askopenfilename(
            title=meta.get("label", "Select File"),
            filetypes=filters,
        )
        if filename:
            var.set(filename)
            config_obj[section][key] = filename
            if on_change:
                on_change(section, key, filename)

    ttk.Button(file_frame, text="Browse...", command=browse_file).pack(
        side="left", padx=5
    )

    def on_var_change(*args):
        val = var.get()
        config_obj[section][key] = val
        if on_change:
            on_change(section, key, val)

    var.trace_add("write", on_var_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def build_field(parent, section, key, meta, config_obj, on_change=None):
    field_type = meta.get("type", "float")
    io.echo(
        f"[build_field] section={section}, key={key}, type={field_type}", level="debug"
    )

    if field_type == "float":
        return make_scale_field(parent, section, key, meta, config_obj)
    elif field_type == "int":
        return make_int_field(parent, section, key, meta, config_obj)
    elif field_type == "bool":
        return make_bool_field(parent, section, key, meta, config_obj)
    elif field_type == "enum":
        return make_enum_field(parent, section, key, meta, config_obj, on_change)
    elif field_type == "radio":
        return make_radio_field(parent, section, key, meta, config_obj, on_change)
    elif field_type == "color":
        return make_color_field(parent, section, key, meta, config_obj, on_change)
    elif field_type == "file":
        return make_file_field(parent, section, key, meta, config_obj, on_change)
    return None


# --- Dashboard Application ---


class DashboardApp:
    def __init__(self, root, modules):
        self.root = root
        self.modules = modules
        self.module_configs = {}
        self.running = True
        self._shutting_down = False
        self.frame_queue = queue.Queue(maxsize=1)
        self.current_frame = None
        self.current_scene_name = conf.CONF["SCENES"].get("active", "all")
        self._args = None

        self._build_ui()

    def _build_ui(self):
        self.root.title("Asimov Dashboard")
        self.root.geometry("1200x800")

        # Paned window: left for preview, right for controls
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # Left: Video preview canvas
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)

        self.canvas = tk.Canvas(left_frame, bg="black")
        self.canvas.pack(fill="both", expand=True)

        # Right: Control panel with scrollbar
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        right_scroll = ttk.Scrollbar(right_frame)
        right_scroll.pack(side="right", fill="y")

        self.right_canvas = tk.Canvas(right_frame, yscrollcommand=right_scroll.set)
        self.right_canvas.pack(side="left", fill="both", expand=True)
        right_scroll.config(command=self.right_canvas.yview)

        self.right_content = ttk.Frame(self.right_canvas)
        self.right_canvas.create_window((0, 0), window=self.right_content, anchor="nw")

        control_frame = ttk.Frame(self.right_content)
        control_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            control_frame, text="Asimov Control Panel", font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)

        self.status_label = ttk.Label(control_frame, text="Running", foreground="green")
        self.status_label.pack(side="right", padx=5)

        scene_frame = ttk.LabelFrame(self.right_content, text="Scene")
        scene_frame.pack(fill="x", padx=10, pady=5)

        self.scene_var = tk.StringVar(value=self.current_scene_name)

        scenes_dict = conf.CONF.get("SCENES", {})
        available_scenes = [k for k in scenes_dict.keys() if k != "active"]

        for scene_name in available_scenes:
            rb = ttk.Radiobutton(
                scene_frame,
                text=scene_name,
                variable=self.scene_var,
                value=scene_name,
            )
            rb.pack(anchor="w", padx=20, pady=2)

        scene_btn_frame = ttk.Frame(scene_frame)
        scene_btn_frame.pack(fill="x", padx=20, pady=5)
        ttk.Button(scene_btn_frame, text="Change Scene", command=self._on_scene_changed).pack(
            side="left", padx=5
        )
        ttk.Button(scene_btn_frame, text="Refresh Scenes", command=self._refresh_scenes).pack(
            side="left", padx=5
        )

        self.scene_frame = scene_frame

        self.enable_frame = ttk.LabelFrame(self.right_content, text="Modules")
        self.enable_frame.pack(fill="x", padx=10, pady=5)

        self.module_vars = {}
        for item in self.modules:
            name = item["name"]
            var = tk.BooleanVar(value=item.get("config", {}).get("enabled", True))
            cb = ttk.Checkbutton(
                self.enable_frame,
                text=name,
                variable=var,
                command=lambda n=name, v=var: self._toggle_module(n, v.get()),
            )
            cb.pack(anchor="w", padx=20, pady=2)
            self.module_vars[name] = var

        self.notebook = ttk.Notebook(self.right_content)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        output_frame = ttk.LabelFrame(self.right_content, text="Status Output")
        output_frame.pack(fill="x", padx=10, pady=5)

        self.output_text = tk.Text(output_frame, height=6, state="normal")
        self.output_text.pack(fill="x", padx=5, pady=5)

        self._build_module_tabs()

        btn_frame = ttk.Frame(self.right_content)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Refresh Schema", command=self._refresh_schema).pack(
            side="left", padx=5
        )
        ttk.Button(
            btn_frame, text="Show All Config", command=self._show_all_config
        ).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Stop", command=self._stop).pack(
            side="right", padx=5
        )

        self.right_content.update_idletasks()
        self.right_canvas.config(scrollregion=self.right_canvas.bbox("all"))

        # Update scale lengths on canvas resize
        def update_all_scales(event=None):
            try:
                canvas_width = self.right_canvas.winfo_width()
                if canvas_width > 100:
                    for child in self.right_content.winfo_children():
                        _update_scales_in_frame(child, canvas_width - 40)
            except Exception:
                pass

        def _update_scales_in_frame(frame, width):
            try:
                for child in frame.winfo_children():
                    if hasattr(child, "winfo_class"):
                        if child.winfo_class() == "TScale":
                            try:
                                child.config(length=width)
                            except Exception:
                                pass
                    try:
                        _update_scales_in_frame(child, width)
                    except Exception:
                        pass
            except Exception:
                pass

        self.right_canvas.bind("<Configure>", update_all_scales)
        self.root.after_idle(update_all_scales)

        # Bind mouse wheel to scroll the control panel
        def on_mousewheel(event):
            self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.root.bind_all("<MouseWheel>", on_mousewheel)
        # Linux uses Button-4/Button-5
        self.root.bind_all(
            "<Button-4>", lambda e: self.right_canvas.yview_scroll(-3, "units")
        )
        self.root.bind_all(
            "<Button-5>", lambda e: self.right_canvas.yview_scroll(3, "units")
        )

        self.root.bind("<Escape>", lambda e: self._stop())

        # Start frame update loop
        self._update_canvas()

    def _update_canvas(self):
        """Periodically update canvas with latest frame."""
        if not self.running:
            return

        frame = self.current_frame
        if frame is not None:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]

                canvas_w = self.canvas.winfo_width()
                canvas_h = self.canvas.winfo_height()

                if canvas_w > 1 and canvas_h > 1:
                    scale = min(canvas_w / w, canvas_h / h, 1.0)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    rgb = cv2.resize(rgb, (new_w, new_h))

                self.photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))

                self.canvas.delete("all")
                cw = self.canvas.winfo_width()
                ch = self.canvas.winfo_height()
                self.canvas.create_image(
                    cw // 2, ch // 2, image=self.photo, anchor=tk.CENTER
                )
            except Exception:
                pass

        self.root.after(33, self._update_canvas)

    def push_frame(self, frame):
        def _update():
            if not self._shutting_down:
                self.current_frame = frame.copy()

        if not self._shutting_down:
            self.root.after(0, _update)

    def _toggle_module(self, name, enabled):
        with logic_lock:
            for item in self.modules:
                if item["name"] == name:
                    item["config"]["enabled"] = enabled
                    self._log(f"Module '{name}' {'enabled' if enabled else 'disabled'}")
                    break

    def _build_module_tabs(self):
        for item in self.modules:
            name = item["name"]
            mod = item["module_ref"]

            config_obj = self._get_module_config(name)
            if config_obj is None:
                continue

            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=name)

            if hasattr(mod, "ui_schema"):
                try:
                    schema = mod.ui_schema(args=None, context=context)
                    if schema:
                        self.module_configs[name] = (schema, config_obj)
                        io.echo(
                            f"[Dashboard] Loaded ui_schema for {name}: {list(schema.keys())}",
                            level="debug",
                        )
                        for section_name, section in schema.items():
                            section_frame = ttk.LabelFrame(tab, text=section_name)
                            section_frame.pack(
                                fill="both", expand=True, padx=10, pady=10
                            )

                            for key, meta in section.items():
                                if (
                                    section_name in config_obj
                                    and key in config_obj[section_name]
                                ):
                                    io.echo(
                                        f"[Dashboard] Building field: {name}.{section_name}.{key}",
                                        level="debug",
                                    )
                                    on_change = None
                                    if (
                                        name.lower() == "float_playingcard"
                                        and section_name == "Card"
                                    ):

                                        def on_change(s, k, v):
                                            self._log_card_filename(config_obj)

                                    build_field(
                                        section_frame,
                                        section_name,
                                        key,
                                        meta,
                                        config_obj,
                                        on_change,
                                    )
                except Exception as e:
                    self._log(f"Error loading schema for {name}: {e}")

    def _log_card_filename(self, config_obj):
        import os

        card_config = config_obj.get("Card", {})
        rank = card_config.get("rank")
        suit = card_config.get("suit")
        if rank and suit:
            full_path = cards.get_card_path(rank, suit)
            filename = full_path.split("/")[-1]
            self._log(f"Card: {filename}")
            self._log(f"Path: {full_path}")
            if os.path.exists(full_path):
                if os.access(full_path, os.R_OK):
                    self._log("Status: OK (file exists and readable)")
                else:
                    self._log("Status: WARNING (file exists but not readable)")
            else:
                self._log("Status: ERROR (file not found)")

    def _get_module_config(self, name):
        name_lower = name.lower()

        key_map = {
            "hand": "HAND",
            "indexfingertip": "INDEXFINGERTIP",
            "face": "FACE",
            "facemask": "FACEMASK",
            "eyes_next": "EYES",
            "glitch": "GLITCH",
            "motionblur": "MOTIONBLUR",
            "float_playingcard": "FLOAT_PLAYINGCARD",
            "fps_overlay": "FPS_OVERLAY",
            "rect": "RECT",
            "rect_touch": "RECT_TOUCH",
        }

        key = key_map.get(name_lower)
        if key and key in conf.CONF:
            return conf.CONF[key]
        return None

    def _refresh_schema(self):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)

        self.module_configs = {}
        self._build_module_tabs()
        self._log("Schema refreshed")

    def _show_all_config(self):
        output = {}
        for name in self.module_vars.keys():
            config_obj = self._get_module_config(name)
            if config_obj:
                output[name] = config_obj

        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", json.dumps(output, indent=2, default=str))

    def _log(self, message):
        self.output_text.insert("end", f"{message}\n")
        self.output_text.see("end")

    def _stop(self):
        self._shutting_down = True
        self.running = False
        self.root.quit()

    def update_status(self, message):
        def _update():
            if not self._shutting_down:
                self.status_label.config(text=message)

        if not self._shutting_down:
            self.root.after(0, _update)

    def _on_scene_changed(self):
        """Handle scene selection change."""
        new_scene = self.scene_var.get()
        if new_scene != self.current_scene_name:
            self._reload_scene(new_scene)

    def _refresh_scenes(self):
        """Re-scan scenes directory and update UI."""
        new_scenes, active = conf.reload_scenes()

        for widget in self.scene_frame.winfo_children():
            widget.destroy()

        self.scene_var.set(active)
        self.current_scene_name = active

        available_scenes = [k for k in new_scenes.keys() if k != "active"]
        for scene_name in available_scenes:
            rb = ttk.Radiobutton(
                self.scene_frame,
                text=scene_name,
                variable=self.scene_var,
                value=scene_name,
                command=self._on_scene_changed,
            )
            rb.pack(anchor="w", padx=20, pady=2)

        self._log(f"Scenes refreshed. Active: {active}")

    def _reload_scene(self, scene_name):
        """Dynamically switch to a different scene."""
        global _modules

        self._log(f"Switching to scene: {scene_name}")

        with logic_lock:
            for item in self.modules:
                m = item.get("module_ref")
                if m and hasattr(m, "close"):
                    try:
                        m.close(self._args, context=context)
                    except Exception as e:
                        self._log(f"Error closing {item['name']}: {e}")

        known_prefixes = [
            "HAND",
            "FACE",
            "INDEXFINGER",
            "CARD",
            "RECT",
            "EYES",
            "GLITCH",
            "MOTION",
        ]
        existing_keys = set()
        for key in context.keys():
            if any(key.startswith(p) for p in known_prefixes):
                existing_keys.add(key)

        if hasattr(context, "card"):
            existing_keys.add("CARD")

        declared_keys = set()
        for item in self.modules:
            m = item.get("module_ref")
            if m and hasattr(m, "get_stateful_keys"):
                try:
                    keys = m.get_stateful_keys()
                    declared_keys.update(keys)
                except Exception:
                    pass

        for key in declared_keys:
            if key in context:
                del context[key]
            if key == "CARD" and hasattr(context, "card"):
                delattr(context, "card")

        leftover_keys = existing_keys - declared_keys
        if leftover_keys:
            self._log(
                f"Warning: Undeclared context keys remain: {sorted(leftover_keys)}. Module may need get_stateful_keys()"
            )

        conf.set_scenes("active", scene_name)

        new_modules = get_active_modules(self._args, scene_name)

        _modules = new_modules
        self.modules = new_modules
        self.current_scene_name = scene_name

        self._rebuild_module_checkboxes()

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.module_configs = {}
        self._build_module_tabs()

        self.right_content.update_idletasks()
        self.right_canvas.config(scrollregion=self.right_canvas.bbox("all"))

        self._log(f"Scene changed to: {scene_name}")

    def _rebuild_module_checkboxes(self):
        """Rebuild the module enable/disable checkboxes."""
        for widget in self.enable_frame.winfo_children():
            widget.destroy()

        self.module_vars = {}
        for item in self.modules:
            name = item["name"]
            var = tk.BooleanVar(value=item.get("config", {}).get("enabled", True))
            cb = ttk.Checkbutton(
                self.enable_frame,
                text=name,
                variable=var,
                command=lambda n=name, v=var: self._toggle_module(n, v.get()),
            )
            cb.pack(anchor="w", padx=20, pady=2)
            self.module_vars[name] = var


# --- Thread Logic ---


def _consumer(args: argparse.Namespace):
    global _modules
    try:
        while not _stop_event.is_set():
            with logic_lock:
                frame = context.get("SHARED_FRAME")

            if frame is not None:
                for item in _modules:
                    if not item.get("config", {}).get("enabled", True):
                        continue

                    try:
                        m = item["module_ref"]

                        if hasattr(m, "detect"):
                            with logic_lock:
                                m.detect(frame, context)

                    except Exception:
                        io.echo_traceback(
                            f"Logic Thread Error in module: {item['name']}"
                        )

            logic_fps_val, _ = logic_fps.update()
            context["FPS"] = {"logic": logic_fps_val}
            time.sleep(0.01)

    except Exception:
        io.echo_traceback("CRITICAL: Consumer thread collapsed")


_current_scene = None


# --- Helper Functions ---


def get_active_modules(args, scene_name=None):
    global _current_scene

    scenes_def = conf.CONF.get("SCENES")
    if not scenes_def:
        io.echo("No SCENES defined in conf", level="error")
        return []

    active_name = scene_name or scenes_def.get("active", "float_card")
    scene_def = scenes_def.get(active_name)
    if not scene_def:
        io.echo(f"Scene '{active_name}' not found in SCENES", level="error")
        return []

    try:
        _current_scene = scene.load(args, scene_def)
    except Exception:
        io.echo_traceback("Failed to load scene")
        return []

    if not scene.init(args, _current_scene):
        io.echo("Scene init failed", level="error")
        return []

    if not scene.main(args, _current_scene):
        io.echo("Scene main failed", level="error")
        return []

    active = []
    for item in _current_scene["modules"]:
        mod = item["module"]
        cfg = item["config"].copy()
        cfg["enabled"] = item.get("enabled", True)

        active.append(
            {
                "name": item["name"],
                "module_ref": mod,
                "config": cfg,
                "can_detect": hasattr(mod, "detect"),
                "can_draw": hasattr(mod, "draw"),
            }
        )

    return active


def handle_hotkeys(key, modules):
    char = chr(key).lower()
    with logic_lock:
        for item in modules:
            if item.get("config", {}).get("hotkey") == char:
                item["config"]["enabled"] = not item["config"]["enabled"]
                io.echo(
                    f"TOGGLE: {item['name']} is now {item['config']['enabled']}",
                    level="info",
                )


# --- Lifecycle ---


def init(args, **kwargs):
    return True


def access(args, op="run", **kwargs):
    return op == "run"


def buildargs(args=None, **kwargs):
    return None


# --- Main ---


def main(args, **kwargs):
    global _modules

    _modules = get_active_modules(args)
    if getattr(args, "debug", False):
        io.echo(f"Loaded {len(_modules)} modules", level="debug")

    io.echo(f"Opening camera: {args.capture_device}")
    cap_handle, error = cap.open_ready(
        args.capture_device, open_timeout=2, ready_timeout=5
    )
    if cap_handle is None:
        io.echo(f"Cannot open camera: {error}", level="error")
        return False

    cap_result = cap.configure(
        cap_handle, args.capture_width, args.capture_height, args.capture_fps
    )
    if cap_result is None:
        io.echo("Failed to configure capture", level="error")
        cap.release(cap_handle)
        return False

    actual_width, actual_height, actual_fps = cap_result

    _stop_event.clear()
    _threads = []

    # Start logic thread
    consumer_thread = threading.Thread(target=_consumer, args=(args,), daemon=True)
    _threads.append(consumer_thread)
    consumer_thread.start()

    # Start Tkinter dashboard
    root = tk.Tk()
    app = DashboardApp(root, _modules)
    app._args = args

    # Render loop - pushes frames to dashboard
    def render_loop():
        try:
            with pyvirtualcam.Camera(
                width=actual_width, height=actual_height, fps=actual_fps
            ) as vcam:
                io.echo(
                    f"Virtual Camera: {actual_width}x{actual_height} @ {actual_fps}fps",
                    level="ok",
                )
                app.update_status("Running")

                while app.running:
                    success, raw_frame = cap_handle.read()
                    if not success:
                        break

                    frame = raw_frame.copy()
                    # Flip before modules run so flipType=True correctly handles labels
                    frame = cv2.flip(frame, 1)

                    with logic_lock:
                        context["SHARED_FRAME"] = frame

                    # Rendering phase
                    for item in _modules:
                        if not item.get("config", {}).get("enabled", True):
                            continue
                        if not item.get("can_draw", False):
                            continue

                        try:
                            result = item["module_ref"].draw(frame, context)
                            if isinstance(result, np.ndarray):
                                frame = result
                        except Exception:
                            io.echo_traceback(
                                f"draw() failure in module '{item['name']}'"
                            )

                    # Update render FPS
                    render_fps_val, _ = render_fps.update()
                    fps_data = context.get("FPS")
                    if fps_data is None:
                        fps_data = {}
                    fps_data["render"] = render_fps_val
                    context["FPS"] = fps_data

                    # Send to virtual camera
                    vcam.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    vcam.sleep_until_next_frame()

                    # Push frame to dashboard canvas
                    app.push_frame(frame)

        except Exception:
            io.echo_traceback("Render loop crash")

        finally:
            app.update_status("Stopped")
            app.running = False
            cap.release(cap_handle)

    render_thread = threading.Thread(target=render_loop, daemon=True)
    _threads.append(render_thread)
    render_thread.start()

    root.mainloop()

    _stop_event.set()

    for th in _threads:
        if th.is_alive():
            th.join(timeout=2.0)

    # Shutdown modules that have close() methods
    for item in _modules:
        m = item.get("module_ref")
        if m and hasattr(m, "close"):
            try:
                m.close(args, context=context)
            except Exception:
                io.echo_traceback(f"Error closing module '{item['name']}'")

    return True
