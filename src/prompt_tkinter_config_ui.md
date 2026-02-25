# Tkinter Config UI Specification

**Role:** You are an expert Python developer specializing in Tkinter and modern UI component design.

**Task:** Create a Tkinter-based configuration editor application that mirrors the pattern from `demo_tui.py`. The app should provide a graphical interface for editing runtime configuration values defined by a schema.

**Core Requirements:**

1. **Architecture:**
   - Use the same `conf` class and `ui_schema()` pattern from `demo_tui.py`
   - Create a minimal class (or use functions) that reads the schema and generates appropriate widgets
   - Changes to widgets should immediately update `conf.HAND` values (live binding)

2. **Schema-Driven Widget Generation:**
   - For each section in the schema, create a labeled frame
   - **Float fields:** Use `tk.Scale` with a `Resolution` option
   - **Integer fields:** Use `tk.Scale` 
   - **Boolean fields:** Use `tk.Checkbutton` (consider the `ModernSwitch` widget if available)
   - Each widget should display the `label` from the schema
   - Show current value and allow direct editing

3. **No Exception-Based Validation:**
   - Validate inputs using `validatecommand` with `%P` (proposed value)
   - Return True if valid, False if invalid, None to show error state
   - Use a red border or error label to indicate invalid input (no try/except)

4. **Layout:**
   - Use `ttk.Notebook` or `ttk.Frame` tabs to organize config sections (FILTER, DRAW)
   - Add a "Run Module" button that calls `detect()` and displays output in a read-only text area
   - Add a "Show Raw Config" button to display `conf.HAND` as JSON/text

5. **Live Updates:**
   - Use `tk.StringVar` or `tk.DoubleVar`/`BooleanVar` with `trace_add` to sync widget changes to `conf`
   - When "Run Module" is clicked, it should read current `conf.HAND` values

6. **Technical Constraints:**
   - Use `ttk` widgets where possible for a modern look
   - Avoid try/except blocks - use validation callbacks instead
   - Return True/False/None from validation to indicate valid/invalid/error states
   - Ensure the app can be run standalone

**Output:** Provide the full Python application and a demo script showing the config editor with:
- FILTER section with FREQ, MIN_CUTOFF, BETA sliders/entries
- DRAW section with SHOW_LANDMARKS toggle
- "Run Module" button that prints current config values
- "Show Config" button to display raw config
