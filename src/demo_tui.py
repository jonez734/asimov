"""
Minimal runnable demo of:

conf.py  → runtime values
ui_schema() → editable metadata
UI → edits conf
Module → reads conf live
"""

# ------------------------------------------------------------
# 1. Runtime Configuration (conf.py equivalent)
# ------------------------------------------------------------

class conf:
    HAND = {
        "FILTER": {
            "FREQ": 30.0,
            "MIN_CUTOFF": 1.0,
            "BETA": 0.0,
        },
        "DRAW": {
            "SHOW_LANDMARKS": True
        }
    }

# ------------------------------------------------------------
# 2. Module (hand.py equivalent)
# ------------------------------------------------------------

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
                "label": "Filter Frequency"
            },
            "MIN_CUTOFF": {
                "type": "float",
                "default": f["MIN_CUTOFF"],
                "min": 0.01,
                "max": 10.0,
                "step": 0.1,
                "label": "Min Cutoff"
            },
            "BETA": {
                "type": "float",
                "default": f["BETA"],
                "min": 0.0,
                "max": 5.0,
                "step": 0.1,
                "label": "Beta"
            }
        },
        "DRAW": {
            "SHOW_LANDMARKS": {
                "type": "bool",
                "default": d["SHOW_LANDMARKS"],
                "label": "Draw Landmarks"
            }
        }
    }


def detect():
    """
    Simulate module behavior using conf values.
    """
    f = conf.HAND["FILTER"]
    d = conf.HAND["DRAW"]

    print("\n[HAND MODULE RUNNING]")
    print(f"  FREQ = {f['FREQ']}")
    print(f"  MIN_CUTOFF = {f['MIN_CUTOFF']}")
    print(f"  BETA = {f['BETA']}")
    print(f"  SHOW_LANDMARKS = {d['SHOW_LANDMARKS']}")


# ------------------------------------------------------------
# 3. Simple CLI UI Engine
# ------------------------------------------------------------

def edit_config(schema):
    """
    Very basic schema-driven editor.
    """

    for section_name, section in schema.items():
        print(f"\n--- {section_name} ---")

        for key, meta in section.items():
            current_value = conf.HAND[section_name][key]
            print(f"{key} ({meta['type']})")
            print(f"  Current: {current_value}")

            new_value = input("  Enter new value (or blank to skip): ").strip()
            if not new_value:
                continue

            try:
                if meta["type"] == "float":
                    val = float(new_value)
                    if not (meta["min"] <= val <= meta["max"]):
                        print("  ❌ Out of range")
                        continue

                elif meta["type"] == "int":
                    val = int(new_value)

                elif meta["type"] == "bool":
                    val = new_value.lower() in ("1", "true", "yes", "y")

                else:
                    val = new_value

                conf.HAND[section_name][key] = val
                print("  ✅ Updated")

            except Exception:
                print("  ❌ Invalid input")


# ------------------------------------------------------------
# 4. Main Demo Loop
# ------------------------------------------------------------

def main():
    while True:
        print("\n==============================")
        print("1) Run HAND module")
        print("2) Edit HAND config")
        print("3) Show raw conf")
        print("4) Exit")
        print("==============================")

        choice = input("Select: ").strip()

        if choice == "1":
            detect()

        elif choice == "2":
            schema = ui_schema()
            edit_config(schema)

        elif choice == "3":
            print("\nCurrent conf.HAND:")
            print(conf.HAND)

        elif choice == "4":
            break


if __name__ == "__main__":
    main()
