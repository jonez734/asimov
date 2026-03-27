"""
Tkinter Config UI Demo

conf.py → runtime values
ui_schema() → editable metadata
UI → edits conf
Module → reads conf live
"""

import tkinter as tk
from tkinter import ttk
import json


class conf:
    HAND = {
        "FILTER": {
            "FREQ": 30.0,
            "MIN_CUTOFF": 1.0,
            "BETA": 0.0,
        },
        "DRAW": {"SHOW_LANDMARKS": True},
    }


def ui_schema(args=None, context=None):
    f = conf.HAND["FILTER"]
    d = conf.HAND["DRAW"]

    return {
        "FILTER": {
            "FREQ": {
                "type": "float",
                "default": f["FREQ"],
                "min": 1.0,
                "max": 240.0,
                "step": 1.0,
                "label": "Filter Frequency",
            },
            "MIN_CUTOFF": {
                "type": "float",
                "default": f["MIN_CUTOFF"],
                "min": 0.01,
                "max": 10.0,
                "step": 0.1,
                "label": "Min Cutoff",
            },
            "BETA": {
                "type": "float",
                "default": f["BETA"],
                "min": 0.0,
                "max": 5.0,
                "step": 0.1,
                "label": "Beta",
            },
        },
        "DRAW": {
            "SHOW_LANDMARKS": {
                "type": "bool",
                "default": d["SHOW_LANDMARKS"],
                "label": "Draw Landmarks",
            }
        },
    }


def detect():
    f = conf.HAND["FILTER"]
    d = conf.HAND["DRAW"]

    lines = []
    lines.append("[HAND MODULE RUNNING]")
    lines.append(f"  FREQ = {f['FREQ']}")
    lines.append(f"  MIN_CUTOFF = {f['MIN_CUTOFF']}")
    lines.append(f"  BETA = {f['BETA']}")
    lines.append(f"  SHOW_LANDMARKS = {d['SHOW_LANDMARKS']}")

    return "\n".join(lines)


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


def make_scale_field(parent, section, key, meta):
    frame = ttk.Frame(parent)

    var = tk.DoubleVar(value=conf.HAND[section][key])

    label = ttk.Label(frame, text=meta["label"])
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

    entry_var = tk.StringVar(value=str(conf.HAND[section][key]))

    def on_scale_change(*args):
        val = var.get()
        value_label.config(text=f"Value: {val}")
        entry_var.set(f"{val:.2f}")
        conf.HAND[section][key] = val

    def on_entry_validate(proposed):
        result = validate_float(proposed, meta["min"], meta["max"])
        if result is True:
            conf.HAND[section][key] = float(proposed)
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


def make_bool_field(parent, section, key, meta):
    frame = ttk.Frame(parent)

    var = tk.BooleanVar(value=conf.HAND[section][key])

    check = ttk.Checkbutton(
        frame,
        text=meta["label"],
        variable=var,
        command=lambda: conf.HAND[section][key].__class__(var.get()),
    )
    check.pack(anchor="w", padx=10, pady=5)

    def on_change(*args):
        conf.HAND[section][key] = var.get()

    var.trace_add("write", on_change)

    frame.pack(fill="x", padx=10, pady=5)
    return frame


def build_field(parent, section, key, meta):
    field_type = meta["type"]

    if field_type in ("float", "int"):
        return make_scale_field(parent, section, key, meta)
    elif field_type == "bool":
        return make_bool_field(parent, section, key, meta)
    return None


def run_module(output_text):
    result = detect()
    output_text.delete("1.0", "end")
    output_text.insert("1.0", result)


def show_config(output_text):
    output_text.delete("1.0", "end")
    output_text.insert("1.0", json.dumps(conf.HAND, indent=2))


def main():
    root = tk.Tk()
    root.title("Config Editor")
    root.geometry("500x600")

    schema = ui_schema()

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    output_frame = ttk.Frame(root)
    output_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    output_text = tk.Text(output_frame, height=8, state="normal")
    output_text.pack(fill="both", expand=True)

    button_frame = ttk.Frame(root)
    button_frame.pack(fill="x", padx=10, pady=(0, 10))

    run_btn = ttk.Button(
        button_frame, text="Run Module", command=lambda: run_module(output_text)
    )
    run_btn.pack(side="left", padx=5)

    config_btn = ttk.Button(
        button_frame, text="Show Config", command=lambda: show_config(output_text)
    )
    config_btn.pack(side="left", padx=5)

    for section_name, section in schema.items():
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=section_name)

        for key, meta in section.items():
            build_field(tab, section_name, key, meta)

    root.mainloop()


if __name__ == "__main__":
    main()
