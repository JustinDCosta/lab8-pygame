# Light Refactoring Plan

## 1. Overview
This project is a single-file Pygame simulation in `main.py`.
It already has a clear flow and good comments, but the file is large and mixes multiple responsibilities:
configuration, entity models, physics rules, effect rendering, event handling, and the game loop.

Main opportunities for beginner-friendly refactoring:
- Group related constants to reduce top-of-file noise.
- Separate data models from update/draw logic.
- Reduce repeated math patterns (`sqrt(dx**2 + dy**2)` and vector normalization).
- Make update stages explicit with small orchestrator helpers.
- Add lightweight validation and smoke checks around pure helper functions.

## 2. Refactoring Goals
- Improve readability by splitting large conceptual areas into small sections or modules.
- Keep behavior unchanged while reducing repetition.
- Make physics and lifecycle logic easier to test in isolation.
- Keep names and function boundaries understandable for first-year CS students.
- Preserve current comments style and beginner-oriented explanations.

## 3. Step-by-Step Refactoring Plan

### Step 1: Organize Constants by Domain
What to do:
- Move constants into grouped structures near the top of the file, such as:
  - display/timing
  - speed controls
  - behavior by size
  - physics tuning
  - effects toggles
- Keep existing constant names first, then optionally migrate to grouped containers later.

Why this helps:
- New readers can quickly find related settings.
- It reduces scanning overhead when tuning simulation behavior.

Inline comment requirement for final code:
- Add short comments explaining each constant group and why those values are grouped.

### Step 2: Introduce Small Vector Utility Helpers
What to do:
- Add simple helpers like:
  - `distance(dx, dy)`
  - `normalize(dx, dy)`
  - `clamp_magnitude(vx, vy, max_speed)`
- Replace repeated math in `apply_interactions`, `apply_chase_force`, and `clamp_circle_speed` with these helpers.

Why this helps:
- Removes duplicated formulas.
- Reduces bug risk in future edits.
- Makes intent clearer than repeating low-level math each time.

Inline comment requirement for final code:
- Add comments that explain what each helper returns and why normalization needs zero-distance safety.

### Step 3: Make Circle Update Stages Explicit
What to do:
- Keep `update_circle`, but call stage helpers with names that represent the pipeline:
  - lifecycle stage
  - movement stage
  - interaction stage
  - constraint stage
- Do not change the current execution order.

Why this helps:
- Students can trace the simulation as a pipeline.
- Easier to debug because each stage has one job.

Inline comment requirement for final code:
- Add one concise “why this order” comment near the stage pipeline.

### Step 4: Isolate Effect-Only Logic
What to do:
- Keep `Effect` class behavior unchanged, but separate effect creation from lifecycle checks with helper names like:
  - `spawn_death_effect(...)`
  - `spawn_rebirth_effect(...)`
- Keep toggles (`ENABLE_*`) in one place.

Why this helps:
- Clarifies what is simulation-critical versus purely visual.
- Makes optional effect behavior easier to toggle and extend.

Inline comment requirement for final code:
- Add comments explaining why visuals are optional and should not affect core physics.

### Step 5: Prepare for Module Split (Optional, Light)
What to do:
- Keep this optional for now, but define a target split plan:
  - `config.py` for constants
  - `entities.py` for `Circle`, `Effect`, and `Particle`
  - `physics.py` for update and interaction helpers
  - `ui.py` for drawing HUD/help text
  - `main.py` for runtime orchestration

Why this helps:
- Creates a growth path without forcing a large rewrite now.
- Lets students learn modular design gradually.

Inline comment requirement for final code:
- If this step is applied, each new module should start with a short “responsibility” comment.

### Step 6: Add Lightweight Behavior Checks
What to do:
- Add simple tests for pure helpers first (safe position logic, overlap checks, speed clamp math).
- Keep rendering and Pygame loop tests minimal.

Why this helps:
- Gives confidence that refactors do not change behavior.
- Focuses tests on deterministic logic that is easiest to verify.

Inline comment requirement for final code:
- Add comments in tests describing which behavior contract each test protects.

## 4. Final Output Requirements (Mandatory)
When this plan is executed, the output must:
- Contain only refactored code (no extra tutorial prose outside code comments).
- Preserve current simulation behavior and controls.
- Include concise inline comments that explain:
  - what changed
  - why the change improves readability/maintainability/correctness
  - which programming concept is being demonstrated
- Keep all comments beginner-friendly and short.

## 5. Key Concepts for Students
- Separation of concerns: each function/module should have one clear role.
- Refactoring without behavior change: improve structure first, keep outputs stable.
- Defensive programming: protect normalization and division operations from zero-distance cases.
- Data flow tracing: follow `dt -> sim_dt -> update stages -> render`.
- Incremental design: move from one large file toward small modules in safe steps.

## 6. Safety Notes
- Refactor in very small commits or checkpoints.
- After each step, run the app and verify controls, movement, respawn, and effects still behave the same.
- Do not change constants and structure in the same step; isolate one kind of change at a time.
- When extracting helpers, copy existing formulas first, then simplify once behavior is confirmed.
