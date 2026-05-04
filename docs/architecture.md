# Architecture Overview

This project is a single-module Pygame simulation. The runtime behavior lives in [main.py](../main.py), and the rest of the repository is documentation and notes.

## Module Dependency Graph

```mermaid
flowchart LR
    Main["main.py"] --> Pygame["pygame"]
    Main --> Random["random"]
    Main --> Math["math"]
    Main --> TypedDict["typing.TypedDict"]
```

`main.py` is the only runtime module. It imports Pygame for rendering and input, and standard-library utilities for randomness, geometry, and typed data.

## Runtime Flow

```mermaid
flowchart TD
    Start["Program start"] --> Init["initialize_runtime()"]
    Init --> Loop["main() frame loop"]
    Loop --> Events["handle_events()"]
    Events --> QuitCheck{"Running?"}
    QuitCheck -->|No| Shutdown["pygame.quit()"]
    QuitCheck -->|Yes| Timing["clock.tick(FPS) and compute dt"]
    Timing --> SimTime{"Paused?"}
    SimTime -->|Yes| SimDtZero["sim_dt = 0.0"]
    SimTime -->|No| SimDtScaled["sim_dt = dt * sim_speed"]
    SimDtZero --> Update["Update circles and effects"]
    SimDtScaled --> Update
    Update --> Draw["draw_frame()"]
    Draw --> Loop
```

The loop is intentionally simple: process input, advance simulation time, update entities, render the frame, and repeat until the user quits.

## Function-Level Call Graph

```mermaid
flowchart TD
    Main["main()"] --> InitRuntime["initialize_runtime()"]
    Main --> HandleEvents["handle_events()"]
    Main --> UpdateCircle["update_circle()"]
    Main --> UpdateEffects["update_effects()"]
    Main --> DrawFrame["draw_frame()"]

    InitRuntime --> CreateInitial["create_initial_circles()"]
    CreateInitial --> CircleInit["Circle.__init__()"]

    UpdateCircle --> HandleLife["handle_lifecycle_and_respawn()"]
    HandleLife --> Respawn["Circle.respawn()"]
    Respawn --> SafePosition["find_safe_position()"]
    SafePosition --> Overlaps["overlaps_circle()"]
    HandleLife --> EffectCreate["Effect.__init__()"]

    UpdateCircle --> ApplyJitter["apply_jitter()"]
    UpdateCircle --> ApplyInteractions["apply_interactions()"]
    UpdateCircle --> ApplyChase["apply_chase_force()"]
    UpdateCircle --> ClampSpeed["clamp_circle_speed()"]
    UpdateCircle --> WallForces["apply_wall_forces_and_bounce()"]

    UpdateEffects --> EffectUpdate["Effect.update()"]
    UpdateEffects --> EffectDone["Effect.is_finished()"]

    DrawFrame --> HelpText["draw_help_text()"]
    DrawFrame --> EffectDraw["Effect.draw()"]
```

The important internal path is the circle update path: life-cycle handling, steering, interaction resolution, speed clamping, and wall handling all happen once per circle every frame.

## Primary Execution Sequence

```mermaid
sequenceDiagram
    participant User as "User"
    participant Pygame as "Pygame"
    participant Main as "main() loop"
    participant Circle as "Circle"
    participant Effects as "Effects list"
    participant Screen as "Screen"

    User->>Pygame: "Press keys or close window"
    Pygame-->>Main: "Event queue"
    loop "Each frame"
        Main->>Main: "clock.tick(FPS) and compute dt"
        Main->>Main: "handle_events(sim_speed, paused)"
        alt "QUIT event received"
            Main->>Main: "running = False"
        else "Key pressed"
            Main->>Main: "Adjust speed or pause state"
        end
        Main->>Main: "Compute sim_dt from dt and paused state"
        loop "For each circle"
            Main->>Circle: "update_circle(current, circles, effects, sim_dt)"
            Circle->>Circle: "handle_lifecycle_and_respawn()"
            alt "Circle expired and respawn succeeds"
                Circle->>Circle: "respawn()"
                Circle->>Circle: "find_safe_position()"
                Circle->>Circle: "overlaps_circle()"
                Circle->>Effects: "Append death/rebirth effects"
            else "Circle still alive or respawn delayed"
                Circle->>Circle: "Keep current state"
            end
            Circle->>Circle: "apply_jitter()"
            Circle->>Circle: "apply_interactions()"
            Circle->>Circle: "apply_chase_force()"
            Circle->>Circle: "clamp_circle_speed()"
            Circle->>Circle: "apply_wall_forces_and_bounce()"
        end
        Main->>Effects: "update_effects()"
        Main->>Screen: "draw_frame()"
        Screen-->>User: "Rendered frame"
    end
    Main->>Pygame: "pygame.quit()"
```

The primary path covers the real frame loop, including the respawn branch, optional effect creation, and the render step that presents the final frame.

## Notes

- `Circle` owns persistent state for radius, color, position, velocity, and lifespan.
- `Effect` is a temporary helper for death and rebirth visuals.
- The simulation is frame-rate independent because all motion uses delta time.
- The codebase has no internal package split yet, so the architecture is centered on one file.
