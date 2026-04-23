# Magnetic Circles (Pygame)

## Overview
Magnetic Circles is a real-time 2D simulation written in Python with Pygame.
You will see circles of different sizes moving around, reacting to each other, and respawning over time.

The project is designed to be readable and easy to modify for learning purposes.

## What You Will See
When the program runs, the window shows:
- A black background.
- 30 circles by default.
- FPS (frames per second) at the top-left.
- Current simulation speed multiplier (for example, 1.00x).
- A PAUSED label when paused.
- A control hint near the bottom.

Each circle has:
- A radius chosen from 8, 16, or 32 pixels.
- A random color.
- A velocity (vx, vy).
- A life timer (age and lifespan).

## Core Features
- Frame-rate independent movement with delta time.
- Size-based behavior:
  - Smaller circles flee from larger nearby circles.
  - Larger circles chase smaller circles in range.
- Overlap correction (circles push apart if they intersect).
- Soft wall repulsion and hard edge bounce.
- Circle life cycle with respawn logic.
- Optional death/rebirth visual effects and particles.
- Runtime controls for speed and pause.

## Project Files
- [main.py](main.py): simulation logic, input, rendering, and program entry point.
- [README.md](README.md): setup and usage guide.
- [REPORT.md](REPORT.md): project report/documentation.
- [JOURNAL.md](JOURNAL.md): chronological development log.

## Requirements
- Python 3.10 or newer (Python 3.12 is also supported).
- One graphics package:
  - pygame (recommended), or
  - pygame-ce

## Setup Guide

### Windows (PowerShell)
1. Open PowerShell and move into the project folder(wherever you want). Example:
```powershell
cd "c:\Users\USERNAME\Projects\Magnetic_Circles_pygame"
```

2. Create a virtual environment.
```powershell
python -m venv .venv
```

3. Activate it.
```powershell
.\.venv\Scripts\Activate.ps1
```

4. Upgrade pip.
```powershell
python -m pip install --upgrade pip
```

5. Install one package option.
```powershell
python -m pip install pygame
```

Alternative:
```powershell
python -m pip install pygame-ce
```

### macOS/Linux (Terminal)
1. Open a terminal and move into the project folder.
```bash
cd /path/to/lab8-pygame
```

2. Create a virtual environment.
```bash
python3 -m venv .venv
```

3. Activate it.
```bash
source .venv/bin/activate
```

4. Install dependencies.
```bash
python -m pip install --upgrade pip
python -m pip install pygame
```

## How To Run
From the project root:

```powershell
python main.py
```

If your system uses python3 command:

```bash
python3 main.py
```

To stop the app:
- Close the window, or
- Use your terminal interrupt shortcut.

## Runtime Controls
- + or numpad +: increase simulation speed.
- - or numpad -: decrease simulation speed.
- R: reset speed to 1.00x.
- SPACE: pause/resume.
- Window close button: quit.

## Configuration Reference
Main configuration values are near the top of [main.py](main.py).

### Display and timing
- WIDTH, HEIGHT: window size in pixels.
- FPS: target frame rate.
- NUM_CIRCLES: number of circles in the simulation.

### Simulation speed controls
- SIM_SPEED_DEFAULT: starting speed multiplier.
- SIM_SPEED_MIN, SIM_SPEED_MAX: clamp range for speed.
- SIM_SPEED_STEP: amount changed per key press.

### Effect toggles
- ENABLE_SPECIAL_EFFECTS: master switch for all effects.
- ENABLE_DEATH_EFFECT: ring/particles on death.
- ENABLE_REBIRTH_EFFECT: pulse on respawn.
- ENABLE_PARTICLES: particle burst for death effect.

### Behavior by circle size
- CIRCLE_SIZES: allowed radii.
- CHASE_RADIUS_BY_SIZE: how far each size can detect smaller targets.
- MAX_SPEED_BY_SIZE: speed cap for each radius.

### Physics tuning
- SPAWN_PADDING: extra spacing when checking spawn overlap.
- FLEE_RANGE and FLEE_FORCE: flee distance and acceleration strength.
- CHASE_FORCE: acceleration strength toward target.
- WALL_MARGIN and WALL_REPEL_FORCE: soft push from boundaries.
- OVERLAP_PUSH_FACTOR: how strongly overlap correction separates circles.
- TARGET_TIE_DISTANCE: distance threshold for chase target tie-breaks.
- JITTER_* constants: probability and angle range for random turning.
- RESPAWN_RETRY_DELAY_SECONDS: delay before retrying failed respawn.

## How It Works (Detailed)

### 1) Program flow
The simulation runs inside a loop in [main.py](main.py):
1. Process keyboard/window events.
2. Update simulation state using elapsed time.
3. Draw circles and overlays.

### 2) Delta time and frame-rate independence
The code computes delta time each frame:

dt = clock.tick(FPS) / 1000.0

Why this matters:
- If a frame takes longer, dt is larger.
- Position updates use dt, so movement remains consistent across different frame rates.

The simulation also uses sim_dt:
- sim_dt is 0 when paused.
- sim_dt is scaled by runtime speed multiplier when not paused.

### 3) Circle life cycle
Every circle has:
- age: how long it has been alive.
- lifespan: random life duration.

When age reaches lifespan, respawn is attempted:
- Choose a new radius.
- Try random positions first.
- If needed, scan all valid positions.
- If no position is free, respawn fails for now and retry is delayed.

This prevents forced overlapping respawns.

### 4) Pairwise interaction rules
For each circle, the simulation checks every other circle.

Overlap correction:
- If distance between centers is less than sum of radii, move the current circle away.

Flee rule:
- If current circle is smaller and the larger one is within flee range, accelerate away.

Chase rule:
- If current circle is larger and a smaller one is within chase radius, choose a target and accelerate toward it.

Tie-breaking avoids unstable target switching when distances are very close.

### 5) Random jitter
At random intervals, each circle rotates its velocity by a small angle.
This adds natural variation so trajectories are less mechanical.

### 6) Speed limiting and wall handling
Speed limiting:
- Velocity is clamped by size-specific max speed.

Wall behavior uses two layers:
- Soft repulsion in a margin area near edges.
- Hard bounce if circle touches/passes the boundary.

This keeps circles inside the window while preserving dynamic movement.

### 7) Visual effects system
Effect objects are created on circle death/respawn (if enabled).

Death effect:
- Expanding ring.
- Optional outward-moving particles.

Rebirth effect:
- Soft pulse ring.

Effects store age and lifespan, then fade out and remove themselves automatically.

## Troubleshooting

### ModuleNotFoundError: No module named pygame
Install dependencies in the same interpreter used to run the app:
```powershell
python -m pip install pygame
```

### Wrong interpreter in VS Code
Pick the interpreter from .venv in VS Code.
Then run the program again from that environment.

### App is too fast or too slow
- Use +, -, or R while running.
- Or edit SIM_SPEED_* constants in [main.py](main.py).

### Circles are too crowded
Decrease NUM_CIRCLES in [main.py](main.py).

### Window does not open on remote/headless environment
Pygame needs a graphical display.
Run locally on a machine with GUI support.

## Suggested Next Improvements
- Add automated tests for helper functions (spawn checks, targeting, speed clamp).
- Split simulation into modules (physics, rendering, effects, input).
- Add a small in-app settings panel to toggle effects at runtime.
- Add optional data overlays (circle count by size, average speed, respawn rate).
