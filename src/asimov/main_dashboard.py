# asimov/main_dashboard.py

import argparse
import threading
import time
import queue
import cv2
import numpy as np
import pyvirtualcam
import tkinter as tk
from tkinter import ttk
import json
from PIL import Image, ImageTk
from cvzone.FPS import FPS as CVZoneFPS

from . import io, conf, common, scene, cap
from .common import ThreadSafeContext
from .playingcard import cards

context = ThreadSafeContext()
logic_lock = threading.Lock()

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
        length=200,
    )
    scale.pack(fill="x", pady=(0, 5))

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
        length=200,
    )
    scale.pack(fill="x", pady=(0, 5))

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


def build_field(parent, section, key, meta, config_obj, on_change=None):
    field_type = meta.get("type", "float")

    if field_type == "float":
        return make_scale_field(parent, section, key, meta, config_obj)
    elif field_type == "int":
        return make_int_field(parent, section, key, meta, config_obj)
    elif field_type == "bool":
        return make_bool_field(parent, section, key, meta, config_obj)
    elif field_type == "enum":
        return make_enum_field(parent, section, key, meta, config_obj, on_change)
    return None


# --- Dashboard Application ---


class DashboardApp:
    def __init__(self, root, modules):
        self.root = root
        self.modules = modules
        self.module_configs = {}
        self.running = True
        self.frame_queue = queue.Queue(maxsize=1)
        self.current_frame = None

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

        enable_frame = ttk.LabelFrame(self.right_content, text="Modules")
        enable_frame.pack(fill="x", padx=10, pady=5)

        self.module_vars = {}
        for item in self.modules:
            name = item["name"]
            var = tk.BooleanVar(value=item.get("config", {}).get("enabled", True))
            cb = ttk.Checkbutton(
                enable_frame,
                text=name,
                variable=var,
                command=lambda n=name, v=var: self._toggle_module(n, v.get()),
            )
            cb.pack(anchor="w", padx=20, pady=2)
            self.module_vars[name] = var

        self.notebook = ttk.Notebook(self.right_content)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self._build_module_tabs()

        output_frame = ttk.LabelFrame(self.right_content, text="Status Output")
        output_frame.pack(fill="x", padx=10, pady=5)

        self.output_text = tk.Text(output_frame, height=6, state="normal")
        self.output_text.pack(fill="x", padx=5, pady=5)

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
        """Called from render thread to push new frame."""
        self.current_frame = frame.copy()

    def _toggle_module(self, name, enabled):
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

        if name_lower == "hand":
            return conf.HAND
        elif name_lower == "indexfingertip":
            return conf.INDEXFINGERTIP
        elif name_lower == "face":
            return conf.FACE
        elif name_lower == "eyes_next":
            return conf.EYES
        elif name_lower == "glitch":
            return conf.GLITCH
        elif name_lower == "motionblur":
            return conf.MOTIONBLUR
        elif name_lower == "float_playingcard":
            return conf.FLOAT_PLAYINGCARD
        elif name_lower == "fps_overlay":
            return conf.FPS_OVERLAY
        elif name_lower == "rect":
            return conf.RECT
        elif name_lower == "rect_touch":
            return conf.RECT_TOUCH

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
        self.running = False
        self.root.quit()

    def update_status(self, message):
        self.status_label.config(text=message)


# --- Thread Logic ---


def _consumer(modules: list, args: argparse.Namespace):
    try:
        while True:
            with logic_lock:
                frame = context.get("SHARED_FRAME")

            if frame is not None:
                for item in modules:
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


def get_active_modules(args):
    global _current_scene

    scene_def = getattr(conf, "SCENE", None)
    if not scene_def:
        io.echo("No SCENE defined in conf", level="error")
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

        active.append(
            {
                "name": item["name"],
                "module_ref": mod,
                "config": item["config"],
                "can_detect": hasattr(mod, "detect"),
                "can_draw": hasattr(mod, "draw"),
            }
        )

    return active


def handle_hotkeys(key, modules):
    char = chr(key).lower()
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
    modules = get_active_modules(args)
    io.echo(f"Loaded {len(modules)} modules", level="debug")

    io.echo(f"Opening camera: {args.capture_device}")
    cap_handle = cap.open(args.capture_device, timeout=2)
    if cap_handle is None:
        io.echo(f"Failed to open camera device {args.capture_device}", level="error")
        return False

    cap_result = cap.configure(
        cap_handle, args.capture_width, args.capture_height, args.capture_fps
    )
    if cap_result is None:
        io.echo("Failed to configure capture", level="error")
        cap.release(cap_handle)
        return False

    actual_width, actual_height, actual_fps = cap_result

    if not cap.ready(cap_handle):
        io.echo("Camera hardware failed to initialize", level="error")
        cap.release(cap_handle)
        return False

    # Start logic thread
    t = threading.Thread(target=_consumer, args=(modules, args), daemon=True)
    t.start()

    # Start Tkinter dashboard
    root = tk.Tk()
    app = DashboardApp(root, modules)

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
                    for item in modules:
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
    render_thread.start()

    root.mainloop()

    return True
