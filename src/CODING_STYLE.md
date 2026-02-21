# Coding Style Guide

## Git Configuration

Configure git to warn about problematic whitespace:

```bash
git config --global core.whitespace "trailing-space,space-before-tab"
```

This enables warnings for:
- **trailing-space**: trailing whitespace at end of lines
- **space-before-tab**: spaces before tabs in indentation

Note: This project uses spaces (not tabs) for indentation, so `indent-with-non-tab` is intentionally excluded.

## Python

- Use 4 spaces for indentation (no tabs)
- Max line length: 100 characters
- Use type hints where beneficial
- Prefer f-strings over .format() and % formatting

## OpenGL/GLSL

- Use modern OpenGL 3.3+ core profile
- Use VAOs for geometry
- Use explicit attribute locations in shaders
