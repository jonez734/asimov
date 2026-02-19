# Asimov Dashboard

An Asimov module runner with an integrated Tkinter dashboard UI for real-time configuration and preview.

## Quick Start

```bash
python -m asimov main_dashboard
```

## Features

- **Live Preview**: Video preview embedded in the dashboard window
- **Real-time Config**: Adjust module settings via sliders and checkboxes
- **Module Toggle**: Enable/disable modules on the fly
- **Virtual Camera Output**: Streams to a virtual camera for use in other apps

## Requirements

- Python 3.x
- OpenCV (`cv2`)
- NumPy
- pyvirtualcam
- Pillow (PIL)
- cvzone (for hand tracking modules)

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--capture-device` | 0 | Camera device index |
| `--capture-width` | 640 | Frame width |
| `--capture-height` | 480 | Frame height |
| `--capture-fps` | 30 | Target FPS |

Example:
```bash
python -m asimov main_dashboard --capture-device 1 --capture-width 1280 --capture-height 720
```

## Dashboard Controls

### Preview Panel (Left)
- Shows live camera feed with module overlays
- Auto-scales to fit window

### Control Panel (Right)

**Module Checkboxes**
- Toggle each module on/off
- Status reflected immediately in output

**Configuration Tabs**
- Each module has its own tab
- Edit settings in real-time:
  - **float/int**: Slider + text entry
  - **bool**: Checkbox

**Buttons**
- **Refresh Schema**: Reload configuration UI
- **Show All Config**: Display current config as JSON
- **Stop**: Exit the application

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Stop and exit |

## Modules

The dashboard automatically loads modules from `conf.OVERLAYS`. Each module that provides a `ui_schema()` function gets a tab in the dashboard.

### Included Modules

- **hand**: Hand detection (cvzone/MediaPipe)
- **indexfingertip**: Index finger tip tracking
- **face**: Face detection
- **eyes_next**: Eye/privacy bar overlay

## Architecture

See `main_dashboard.spec` for detailed technical specification.

```
┌─────────────────────────────────────┐
│         Dashboard Window             │
│  ┌───────────┬─────────────────┐   │
│  │ Preview   │ Control Panel   │   │
│  │ Canvas    │ - Modules       │   │
│  │           │ - Config Tabs  │   │
│  │           │ - Status       │   │
│  └───────────┴─────────────────┘   │
└─────────────────────────────────────┘
         ▲                  ▲
    Camera Input      Virtual Cam Output
         │                  │
    ┌────┴────┐        ┌─────┴─────┐
    │ Logic   │        │ Render    │
    │ Thread  │        │ Thread    │
    │ (detect)│        │ (draw)    │
    └─────────┘        └───────────┘
```

## Troubleshooting

**No preview showing**
- Check camera is connected: `python -m asimov main_dashboard --capture-device 0`

**Virtual camera not working**
- Install a virtual camera driver (e.g., OBS Virtual Camera on Linux/Mac, ManyCam on Windows)

**Modules not loading**
- Check `conf.OVERLAYS` in `asimov/conf.py`
- Run with `--debug` for verbose output

## Files

- `main_dashboard.py` - Main application
- `main_dashboard.spec` - Technical specification
- `README_dashboard.md` - This file
