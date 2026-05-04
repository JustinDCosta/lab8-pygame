import pygame
import random
import math
from typing import TypedDict

# Window and simulation timing settings.
# WIDTH and HEIGHT define the drawing area in pixels.
WIDTH = 800
HEIGHT = 600
# FPS is the visual refresh target. The simulation still uses dt so movement is frame-rate independent.
FPS = 60
# Number of circles that exist at all times.
NUM_CIRCLES = 45

# Runtime speed controls used by keyboard input.
# 1.0 means real-time, 2.0 means double speed, 0.5 means half speed.
SIM_SPEED_DEFAULT = 1.0
SIM_SPEED_MIN = 0.25
SIM_SPEED_MAX = 3.0
SIM_SPEED_STEP = 0.25

# Feature toggles for optional visual effects.
ENABLE_SPECIAL_EFFECTS = True
ENABLE_DEATH_EFFECT = True
ENABLE_REBIRTH_EFFECT = True
ENABLE_PARTICLES = True

# Circle behavior scales with size.
# Small circles are faster and usually flee; large circles are slower and can chase from farther away.
CIRCLE_SIZES: tuple[int, int, int] = (4, 10, 25)
CHASE_RADIUS_BY_SIZE: dict[int, float] = {
    4: 0.0,
    10: 200.0,
    25: 350.0,
}
MAX_SPEED_BY_SIZE: dict[int, float] = {
    4: 250.0,
    10: 200.0,
    25: 150.0,
}

# Physics tuning constants.
# These values control overlap handling and flee/chase strength.
SPAWN_PADDING = 3
FLEE_RANGE = 180.0
FLEE_FORCE = 800.0
CHASE_FORCE = 600.0
OVERLAP_PUSH_FACTOR = 0.5
TARGET_TIE_DISTANCE = 5.0

# Jitter adds a small random direction change over time so movement looks organic.
JITTER_CHANCE_BASE_60FPS = 0.05
JITTER_MIN_ANGLE = -0.1
JITTER_MAX_ANGLE = 0.1

# If respawn fails because there is no space, wait briefly before retrying.
RESPAWN_RETRY_DELAY_SECONDS = 0.25


Color = tuple[int, int, int]
Position = tuple[int, int]


class Particle(TypedDict):
    """Data shape for one explosion particle used in death effects."""

    vx: float
    vy: float
    size: int


def overlaps_circle(
    x: float,
    y: float,
    radius: int,
    circles: list["Circle"],
    ignore_circle: "Circle | None" = None,
) -> bool:
    """Check whether a circle at (x, y) with given radius overlaps existing circles.

    ignore_circle is used during respawn so a circle does not compare against itself.
    """

    for other in circles:
        if other is ignore_circle:
            continue

        dx = x - other.x
        dy = y - other.y
        min_distance = radius + other.radius + SPAWN_PADDING

        if math.hypot(dx, dy) < min_distance:
            return True

    return False


def find_safe_position(
    radius: int,
    circles: list["Circle"],
    ignore_circle: "Circle | None" = None,
) -> Position | None:
    """Find a non-overlapping spawn position for a circle.

    Strategy:
    1. Try random points first (fast in most cases).
    2. If random attempts fail, do a deterministic full-screen scan.
    3. Return None if no valid point exists right now.
    """

    for _ in range(60):
        x = random.randint(radius, WIDTH - radius)
        y = random.randint(radius, HEIGHT - radius)

        if not overlaps_circle(x, y, radius, circles, ignore_circle):
            return x, y

    # Slow fallback: brute-force scan ensures we do not miss rare free positions.
    for y in range(radius, HEIGHT - radius + 1):
        for x in range(radius, WIDTH - radius + 1):
            if not overlaps_circle(x, y, radius, circles, ignore_circle):
                return x, y

    # Returning None lets the caller retry later without forcing overlap.
    return None


def draw_help_text(
    screen: pygame.Surface,
    font: pygame.font.Font,
    lines: list[str],
    start_x: int,
    start_y: int,
    color: Color,
) -> None:
    """Render multiple UI hint lines with consistent vertical spacing."""

    y = start_y
    for line in lines:
        text_surface = font.render(line, True, color)
        screen.blit(text_surface, (start_x, y))
        y += 22


class Effect:
    """Transient visual effect shown when circles die or respawn."""

    def __init__(
        self,
        kind: str,
        x: float,
        y: float,
        color: Color,
        radius: int,
    ) -> None:
        # Store what to draw and where to draw it.
        self.kind = kind
        self.x = x
        self.y = y
        self.color = color
        self.radius = radius
        # age increases each frame until it reaches lifespan.
        self.age = 0.0

        # Different effect types last for slightly different times.
        if self.kind == "death":
            self.lifespan = 0.35
        else:
            self.lifespan = 0.30

        # Death effects optionally spawn particles that travel outward.
        self.particles: list[Particle] = []
        if self.kind == "death" and ENABLE_PARTICLES:
            particle_count = 8
            for _ in range(particle_count):
                angle = random.uniform(0.0, 2.0 * math.pi)
                speed = random.uniform(70.0, 170.0)
                self.particles.append(
                    {
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "size": random.randint(2, 4),
                    }
                )

    def update(self, dt: float) -> None:
        """Advance effect time by dt seconds."""
        self.age += dt

    def is_finished(self) -> bool:
        """Return True when this effect should be removed."""
        return self.age >= self.lifespan

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the effect using age-based animation and fade-out."""

        # Convert age into normalized progress in [0, 1].
        progress = 0.0
        if self.lifespan > 0:
            progress = min(1.0, self.age / self.lifespan)

        # Alpha decreases over time so effect fades naturally.
        alpha = max(0, int(255 * (1.0 - progress)))

        # Draw on a temporary transparent surface first to simplify blending.
        local_size = int((self.radius + 80) * 2)
        local_surface = pygame.Surface((local_size, local_size), pygame.SRCALPHA)
        center = local_size // 2

        if self.kind == "death":
            # Death effect: expanding white ring.
            ring_radius = int(self.radius + progress * 30)
            if ring_radius > 0:
                pygame.draw.circle(
                    local_surface,
                    (255, 255, 255, alpha),
                    (center, center),
                    ring_radius,
                    2,
                )

            # Particle positions are velocity * age from the center.
            for particle in self.particles:
                px = center + int(particle["vx"] * self.age)
                py = center + int(particle["vy"] * self.age)
                pygame.draw.circle(
                    local_surface,
                    (self.color[0], self.color[1], self.color[2], alpha),
                    (px, py),
                    particle["size"],
                )
        else:
            # Rebirth effect: softer colored pulse.
            pulse_radius = int(self.radius + progress * 22)
            if pulse_radius > 0:
                pulse_alpha = max(0, int(alpha * 0.6))
                pygame.draw.circle(
                    local_surface,
                    (self.color[0], self.color[1], self.color[2], pulse_alpha),
                    (center, center),
                    pulse_radius,
                    2,
                )

        screen.blit(local_surface, (int(self.x - center), int(self.y - center)))


class Circle:
    def __init__(self) -> None:
        # Each circle gets one persistent color so it remains identifiable across respawns.
        self.color: Color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255),
        )
        # Radius determines behavior profile (speed cap and chase range).
        self.radius = random.choice(CIRCLE_SIZES)

        # Initial position and velocity are random to distribute circles across the world.
        self.x = random.randint(self.radius, WIDTH - self.radius)
        self.y = random.randint(self.radius, HEIGHT - self.radius)
        self.vx = random.choice([-1, 1]) * random.randint(15, 40)
        self.vy = random.choice([-1, 1]) * random.randint(15, 40)

        # Lifecycle: each circle "lives" for a random duration before respawning.
        self.age = 0.0
        self.lifespan = random.uniform(3.0, 7.0)

    def respawn(self, circles: list["Circle"]) -> bool:
        """Attempt to restart this circle with the same size and safe position.

        Returns:
            True if respawn succeeded.
            False if no safe position exists yet.
        """

        # Keep the same size, then look for a position that does not overlap.
        position = find_safe_position(self.radius, circles, self)

        if position is None:
            return False

        self.x, self.y = position

        # New life starts with a fresh random velocity.
        self.vx = random.choice([-1, 1]) * random.randint(15, 40)
        self.vy = random.choice([-1, 1]) * random.randint(15, 40)

        # Reset lifecycle timer for the next life.
        self.age = 0.0
        self.lifespan = random.uniform(3.0, 7.0)
        return True


def create_initial_circles(count: int) -> list[Circle]:
    """Create the initial list of circles."""

    # Make an empty list first.
    # We will add one Circle object each time the loop runs.
    circles: list[Circle] = []
    for _ in range(count):
        # Create a new circle with random starting properties.
        circles.append(Circle())

    # Return the fully prepared starting population.
    return circles


def initialize_runtime() -> tuple[
    pygame.Surface,
    pygame.time.Clock,
    pygame.font.Font,
    pygame.font.Font,
    list[Circle],
    list[Effect],
]:
    """Initialize pygame resources and runtime data containers."""

    # Step 1: Start pygame.
    # This must happen before creating windows, fonts, or using most pygame APIs.
    pygame.init()

    # Step 2: Create the window (surface) where everything is drawn.
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Magnetic Circles")

    # Step 3: Create a clock to measure time between frames.
    # dt from the clock makes movement frame-rate independent.
    clock = pygame.time.Clock()

    # Step 4: Prepare fonts for on-screen text.
    # `font` is for important status values, `help_font` is for controls/help lines.
    font = pygame.font.SysFont("Arial", 24, bold=True)
    help_font = pygame.font.SysFont("Arial", 18)

    # Step 5: Build runtime state containers.
    # `circles` holds all active entities.
    # `effects` holds temporary visuals (death ring, rebirth pulse, particles).
    circles = create_initial_circles(NUM_CIRCLES)
    effects: list[Effect] = []

    # Return all initialized objects so main() can use them.
    return screen, clock, font, help_font, circles, effects


def handle_events(sim_speed: float, paused: bool) -> tuple[bool, float, bool]:
    """Process input and return updated (running, sim_speed, paused)."""

    # Assume game keeps running unless we receive a quit event.
    running = True

    # Read every queued event for this frame.
    # If we do not consume events regularly, the window can become unresponsive.
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # `+` increases speed, but never above SIM_SPEED_MAX.
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                sim_speed = min(SIM_SPEED_MAX, sim_speed + SIM_SPEED_STEP)
            # `-` decreases speed, but never below SIM_SPEED_MIN.
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                sim_speed = max(SIM_SPEED_MIN, sim_speed - SIM_SPEED_STEP)
            elif event.key == pygame.K_r:
                # Reset speed back to real-time (1.0x).
                sim_speed = SIM_SPEED_DEFAULT
            elif event.key == pygame.K_SPACE:
                # Toggle pause: when paused, simulation time stops advancing.
                paused = not paused

    # Return the updated runtime flags.
    return running, sim_speed, paused


def handle_lifecycle_and_respawn(
    current: Circle,
    circles: list[Circle],
    effects: list[Effect],
    sim_dt: float,
) -> None:
    """Advance age and perform respawn/effects when a circle expires."""

    # Age grows using simulation time (`sim_dt`), not raw wall-clock time.
    # This respects pause and speed controls.
    current.age += sim_dt
    if current.age < current.lifespan:
        # Circle is still alive this frame.
        return

    # Save old values before respawn so the death effect appears where it died.
    old_x = current.x
    old_y = current.y
    old_color = current.color
    old_radius = current.radius

    # Try to respawn this same object in a non-overlapping position.
    # It can fail if there is no free space right now.
    respawned = current.respawn(circles)

    if respawned:
        # Add optional death effect at the old location.
        if ENABLE_SPECIAL_EFFECTS and ENABLE_DEATH_EFFECT:
            effects.append(Effect("death", old_x, old_y, old_color, old_radius))

        # Add optional rebirth effect at the new location.
        if ENABLE_SPECIAL_EFFECTS and ENABLE_REBIRTH_EFFECT:
            effects.append(
                Effect(
                    "rebirth",
                    current.x,
                    current.y,
                    current.color,
                    current.radius,
                )
            )
        return

    # Respawn failed this frame.
    # Move age slightly back so we retry after a small delay instead of every frame.
    current.age = max(0.0, current.lifespan - RESPAWN_RETRY_DELAY_SECONDS)


def apply_jitter(current: Circle, sim_dt: float) -> None:
    """Apply small random velocity rotation so movement looks organic."""

    # Convert 60 FPS tuning into a frame-time-aware chance.
    # This keeps behavior close to the same even if FPS changes.
    jitter_chance = min(1.0, JITTER_CHANCE_BASE_60FPS * (sim_dt * 60))
    if random.random() >= jitter_chance:
        # In most frames nothing changes, which keeps movement smooth.
        return

    # Rotate velocity by a tiny random angle.
    # Think of this as a gentle steering nudge.
    angle = random.uniform(JITTER_MIN_ANGLE, JITTER_MAX_ANGLE)
    new_vx = current.vx * math.cos(angle) - current.vy * math.sin(angle)
    new_vy = current.vx * math.sin(angle) + current.vy * math.cos(angle)
    current.vx = new_vx
    current.vy = new_vy


def apply_interactions(
    current: Circle,
    circles: list[Circle],
    sim_dt: float,
) -> Circle | None:
    """Resolve overlap/flee/chase selection against all other circles."""

    # How far this circle is allowed to search for prey.
    # Small circles have 0 chase radius, so they do not chase at all.
    chase_radius = CHASE_RADIUS_BY_SIZE.get(current.radius, 0.0)

    # Keep track of the best chase target found so far.
    target: Circle | None = None
    target_dist = float("inf")

    # Compare with every other circle for overlap/flee/chase rules.
    for other in circles:
        if current is other:
            continue

        # Vector from `other` to `current`.
        dx = current.x - other.x
        dy = current.y - other.y
        dist = math.sqrt(dx**2 + dy**2)

        # Two circles touch when distance equals sum of radii.
        min_dist = current.radius + other.radius
        if dist == 0:
            # Exact same center point is a rare edge case.
            # Give a random direction so later division by distance is safe.
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            dist = 1.0

        if dist < min_dist:
            overlap_amount = min_dist - dist
            # Push this circle away to separate overlaps gradually.
            # Using a fraction avoids sudden jumps.
            current.x += (dx / dist) * (overlap_amount * OVERLAP_PUSH_FACTOR)
            current.y += (dy / dist) * (overlap_amount * OVERLAP_PUSH_FACTOR)

        # Flee rule:
        # If current is smaller and close enough, accelerate away from larger circle.
        if current.radius < other.radius and dist < FLEE_RANGE and dist > 0:
            current.vx += (dx / dist) * FLEE_FORCE * sim_dt
            current.vy += (dy / dist) * FLEE_FORCE * sim_dt

        # Chase rule:
        # If current is larger, it may choose one smaller nearby target to chase.
        if current.radius > other.radius and dist < chase_radius and dist > 0:
            is_better = False

            if target is None:
                is_better = True
            else:
                # If two targets are almost equally distant, prefer bigger prey first.
                if abs(dist - target_dist) < TARGET_TIE_DISTANCE:
                    if other.radius > target.radius:
                        is_better = True
                    # If still tied, randomize to avoid fixed bias.
                    elif other.radius == target.radius and random.random() < 0.5:
                        is_better = True
                elif dist < target_dist:
                    # Otherwise choose the closer target.
                    is_better = True

            if is_better:
                target = other
                target_dist = dist

    return target


def apply_chase_force(current: Circle, target: Circle | None, sim_dt: float) -> None:
    """Steer current circle toward target when available."""

    if target is None:
        # No target selected, so there is nothing to chase this frame.
        return

    # Build vector from current position toward target position.
    chase_dx = target.x - current.x
    chase_dy = target.y - current.y
    chase_dist = math.sqrt(chase_dx**2 + chase_dy**2)

    if chase_dist <= 0:
        # Safety guard to avoid dividing by zero.
        return

    # Normalize direction and add chase acceleration.
    # Multiplying by sim_dt keeps acceleration stable across frame rates.
    current.vx += (chase_dx / chase_dist) * CHASE_FORCE * sim_dt
    current.vy += (chase_dy / chase_dist) * CHASE_FORCE * sim_dt


def clamp_circle_speed(current: Circle) -> None:
    """Cap velocity by size-specific max speed."""

    # Different sizes use different max speeds.
    # This makes larger circles feel heavier/slower.
    max_speed = MAX_SPEED_BY_SIZE.get(current.radius, 200.0)
    current_speed = math.sqrt(current.vx**2 + current.vy**2)

    if current_speed <= max_speed:
        # Current speed is valid, so no change is needed.
        return

    # Keep direction the same, but shrink magnitude to the allowed limit.
    current.vx = (current.vx / current_speed) * max_speed
    current.vy = (current.vy / current_speed) * max_speed


def apply_screen_wrap(current: Circle) -> None:
    """Wrap circle positions around the screen edges."""

    # If a circle crosses the boundary, move it to the opposite side.
    if current.x < -current.radius:
        current.x = WIDTH + current.radius
    elif current.x > WIDTH + current.radius:
        current.x = -current.radius

    if current.y < -current.radius:
        current.y = HEIGHT + current.radius
    elif current.y > HEIGHT + current.radius:
        current.y = -current.radius


def update_circle(current: Circle, circles: list[Circle], effects: list[Effect], sim_dt: float) -> None:
    """Run one circle's full simulation update for the current frame."""

    # Step 1: Advance lifetime and possibly respawn expired circles.
    handle_lifecycle_and_respawn(current, circles, effects, sim_dt)

    # Step 2: Move by velocity.
    # Position update is done with sim_dt, so speed scales with time.
    current.x += current.vx * sim_dt
    current.y += current.vy * sim_dt

    # Step 3: Apply steering and interactions.
    apply_jitter(current, sim_dt)
    target = apply_interactions(current, circles, sim_dt)
    apply_chase_force(current, target, sim_dt)

    # Step 4: Enforce safety constraints.
    clamp_circle_speed(current)
    apply_screen_wrap(current)


def update_effects(effects: list[Effect], sim_dt: float) -> None:
    """Advance effects and remove finished ones."""

    # Loop over a copy so we can safely remove finished items from the original list.
    for effect in effects[:]:
        effect.update(sim_dt)
        if effect.is_finished():
            effects.remove(effect)


def draw_frame(
    screen: pygame.Surface,
    circles: list[Circle],
    effects: list[Effect],
    font: pygame.font.Font,
    help_font: pygame.font.Font,
    clock: pygame.time.Clock,
    sim_speed: float,
    paused: bool,
) -> None:
    """Render one complete frame."""

    # Step 1: Clear previous frame to black.
    screen.fill((0, 0, 0))

    # Step 2: Draw all circles (world layer).
    for circle in circles:
        pygame.draw.circle(screen, circle.color, (int(circle.x), int(circle.y)), circle.radius)

    # Step 3: Draw optional visual effects above circles.
    if ENABLE_SPECIAL_EFFECTS:
        for effect in effects:
            effect.draw(screen)

    # Step 4: Draw HUD text (FPS and speed).
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
    screen.blit(fps_text, (10, 10))

    speed_text = font.render(f"Speed: {sim_speed:.2f}x", True, (0, 200, 255))
    screen.blit(speed_text, (10, 40))

    # Step 5: Show pause indicator when simulation updates are stopped.
    if paused:
        pause_text = font.render("PAUSED", True, (255, 220, 0))
        screen.blit(pause_text, (10, 70))

    # Step 6: Draw controls help text near the bottom.
    help_lines = [
        "Controls: [+] Faster  [-] Slower  [R] Reset Speed  [SPACE] Pause/Resume"
    ]
    draw_help_text(screen, help_font, help_lines, 10, HEIGHT - 50, (220, 220, 220))

    # Step 7: Present the completed frame on screen.
    pygame.display.flip()


def main():
    """Run the Pygame loop: input, update physics, draw frame, repeat."""

    # Startup: create pygame resources and initial simulation state.
    screen, clock, font, help_font, circles, effects = initialize_runtime()
    sim_speed = SIM_SPEED_DEFAULT
    paused = False

    # Main loop structure is always: input -> update -> render.
    running = True
    while running:
        # Step 1: Process keyboard/window events.
        running, sim_speed, paused = handle_events(sim_speed, paused)

        # Step 2: Compute elapsed frame time.
        # `dt` is real time; `sim_dt` is simulation time (0 when paused, scaled by speed).
        dt = clock.tick(FPS) / 1000.0
        sim_dt = 0.0 if paused else dt * sim_speed

        # Step 3: Update each circle's behavior and movement.
        for current in circles:
            update_circle(current, circles, effects, sim_dt)

        # Step 4: Update temporary effects and render the final frame.
        update_effects(effects, sim_dt)
        draw_frame(screen, circles, effects, font, help_font, clock, sim_speed, paused)

    # Clean shutdown.
    pygame.quit()


# Run only when executed as a script, not when imported as a module.
if __name__ == "__main__":
    main()
