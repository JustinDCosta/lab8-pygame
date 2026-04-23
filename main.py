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
NUM_CIRCLES = 30

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
CIRCLE_SIZES: tuple[int, int, int] = (8, 16, 32)
CHASE_RADIUS_BY_SIZE: dict[int, float] = {
    8: 0.0,
    16: 250.0,
    32: 350.0,
}
MAX_SPEED_BY_SIZE: dict[int, float] = {
    8: 250.0,
    16: 200.0,
    32: 150.0,
}

# Physics tuning constants.
# These values control overlap handling, flee/chase strength, and wall behavior.
SPAWN_PADDING = 3
FLEE_RANGE = 180.0
FLEE_FORCE = 800.0
CHASE_FORCE = 600.0
WALL_MARGIN = 60.0
WALL_REPEL_FORCE = 2500.0
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
        """Attempt to restart this circle with a new size and safe position.

        Returns:
            True if respawn succeeded.
            False if no safe position exists yet.
        """

        # Choose candidate size first, then look for a position that does not overlap.
        new_radius = random.choice(CIRCLE_SIZES)
        position = find_safe_position(new_radius, circles, self)

        if position is None:
            return False

        self.radius = new_radius
        self.x, self.y = position

        # New life starts with a fresh random velocity.
        self.vx = random.choice([-1, 1]) * random.randint(15, 40)
        self.vy = random.choice([-1, 1]) * random.randint(15, 40)

        # Reset lifecycle timer for the next life.
        self.age = 0.0
        self.lifespan = random.uniform(3.0, 7.0)
        return True


def main():
    """Run the Pygame loop: input, update physics, draw frame, repeat."""

    # Initialize Pygame systems and create the main drawing window.
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Magnetic Circles")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24, bold=True)
    help_font = pygame.font.SysFont("Arial", 18)

    # Build the initial population of circles.
    circles: list[Circle] = []
    for _ in range(NUM_CIRCLES):
        circles.append(Circle())

    # Active temporary effects (death rings, rebirth pulses, particles).
    effects: list[Effect] = []

    # Runtime state variables.
    sim_speed = SIM_SPEED_DEFAULT
    paused = False

    running = True
    while running:
        # 1) Handle user input events.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # + increases simulation speed, - decreases it.
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    sim_speed = min(SIM_SPEED_MAX, sim_speed + SIM_SPEED_STEP)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    sim_speed = max(SIM_SPEED_MIN, sim_speed - SIM_SPEED_STEP)
                elif event.key == pygame.K_r:
                    # Reset speed to real-time.
                    sim_speed = SIM_SPEED_DEFAULT
                elif event.key == pygame.K_SPACE:
                    # Toggle pause/resume.
                    paused = not paused

        # 2) Compute elapsed time in seconds.
        # dt is real elapsed time; sim_dt includes pause and speed multiplier.
        dt = clock.tick(FPS) / 1000.0
        sim_dt = 0.0 if paused else dt * sim_speed

        # 3) Update simulation state.
        for current in circles:
            # 3a) Update lifetime and respawn expired circles.
            current.age += sim_dt
            if current.age >= current.lifespan:
                # Keep previous state so we can place death effect at the old position.
                old_x = current.x
                old_y = current.y
                old_color = current.color
                old_radius = current.radius

                respawned = current.respawn(circles)

                if respawned:
                    if ENABLE_SPECIAL_EFFECTS and ENABLE_DEATH_EFFECT:
                        effects.append(
                            Effect("death", old_x, old_y, old_color, old_radius)
                        )

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
                else:
                    # If no space is available, delay retry to avoid rapid repeated attempts.
                    current.age = max(
                        0.0, current.lifespan - RESPAWN_RETRY_DELAY_SECONDS
                    )

            # 3b) Integrate velocity into position.
            current.x += current.vx * sim_dt
            current.y += current.vy * sim_dt

            # 3c) Add tiny random direction changes (jitter) for more natural motion.
            jitter_chance = min(1.0, JITTER_CHANCE_BASE_60FPS * (sim_dt * 60))
            if random.random() < jitter_chance:
                angle = random.uniform(JITTER_MIN_ANGLE, JITTER_MAX_ANGLE)
                # Rotate velocity by a small angle using 2D rotation formulas.
                new_vx = current.vx * math.cos(angle) - current.vy * math.sin(angle)
                new_vy = current.vx * math.sin(angle) + current.vy * math.cos(angle)
                current.vx = new_vx
                current.vy = new_vy

            # Bigger circles can chase from farther away.
            chase_radius = CHASE_RADIUS_BY_SIZE.get(current.radius, 0.0)

            target: Circle | None = None
            target_dist = float("inf")

            # 3d) Compare against every other circle for overlap, flee, and chase behavior.
            for other in circles:
                if current is other:
                    continue

                # Vector from other -> current (useful for pushing/fleeing).
                dx = current.x - other.x
                dy = current.y - other.y
                dist = math.sqrt(dx**2 + dy**2)

                # Resolve overlap so circles do not visually merge.
                min_dist = current.radius + other.radius
                if dist == 0:
                    # Degenerate case: same center. Use random direction to avoid divide-by-zero.
                    angle = random.uniform(0, 2 * math.pi)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                    dist = 1.0

                if dist < min_dist:
                    overlap_amount = min_dist - dist
                    # Move current partially away from other to separate them smoothly.
                    current.x += (dx / dist) * (overlap_amount * OVERLAP_PUSH_FACTOR)
                    current.y += (dy / dist) * (overlap_amount * OVERLAP_PUSH_FACTOR)

                # Flee rule: smaller circles accelerate away from larger nearby circles.
                if current.radius < other.radius and dist < FLEE_RANGE and dist > 0:
                    # Scale by sim_dt so behavior is stable across frame rates.
                    current.vx += (dx / dist) * FLEE_FORCE * sim_dt
                    current.vy += (dy / dist) * FLEE_FORCE * sim_dt

                # Chase rule: larger circles pick one smaller nearby target.
                if current.radius > other.radius and dist < chase_radius and dist > 0:
                    is_better = False

                    if target is None:
                        is_better = True
                    else:
                        # If distances are close, apply deterministic tie-break preferences.
                        if abs(dist - target_dist) < TARGET_TIE_DISTANCE:
                            # Prefer the larger prey to reduce rapid target switching.
                            if other.radius > target.radius:
                                is_better = True
                            # Final tie-breaker for equal size: random choice.
                            elif (
                                other.radius == target.radius and random.random() < 0.5
                            ):
                                is_better = True
                        elif dist < target_dist:
                            is_better = True

                    if is_better:
                        target = other
                        target_dist = dist

            # Apply chase steering toward chosen target.
            if target is not None:
                # This vector points from current -> target.
                chase_dx = target.x - current.x
                chase_dy = target.y - current.y
                chase_dist = math.sqrt(chase_dx**2 + chase_dy**2)

                if chase_dist > 0:
                    # Normalize direction and apply acceleration.
                    current.vx += (chase_dx / chase_dist) * CHASE_FORCE * sim_dt
                    current.vy += (chase_dy / chase_dist) * CHASE_FORCE * sim_dt

            # 3e) Clamp speed by circle size so acceleration stays bounded.
            max_speed = MAX_SPEED_BY_SIZE.get(current.radius, 200.0)

            # Without clamping, repeated forces can make velocities unrealistically large.
            current_speed = math.sqrt(current.vx**2 + current.vy**2)
            if current_speed > max_speed:
                current.vx = (current.vx / current_speed) * max_speed
                current.vy = (current.vy / current_speed) * max_speed

            # 3f) Apply soft wall repulsion before hard boundary collision.
            wall_margin = WALL_MARGIN
            if current.x < current.radius + wall_margin:
                current.vx += WALL_REPEL_FORCE * sim_dt
            elif current.x > WIDTH - current.radius - wall_margin:
                current.vx -= WALL_REPEL_FORCE * sim_dt

            if current.y < current.radius + wall_margin:
                current.vy += WALL_REPEL_FORCE * sim_dt
            elif current.y > HEIGHT - current.radius - wall_margin:
                current.vy -= WALL_REPEL_FORCE * sim_dt

            # 3g) Hard boundary handling: clamp position and reflect velocity direction.
            if current.x - current.radius < 0:
                current.x = current.radius
                current.vx = abs(current.vx)
            elif current.x + current.radius > WIDTH:
                current.x = WIDTH - current.radius
                current.vx = -abs(current.vx)

            if current.y - current.radius < 0:
                current.y = current.radius
                current.vy = abs(current.vy)
            elif current.y + current.radius > HEIGHT:
                current.y = HEIGHT - current.radius
                current.vy = -abs(current.vy)

        # Update and clean up expired visual effects.
        for effect in effects[:]:
            effect.update(sim_dt)
            if effect.is_finished():
                effects.remove(effect)

        # 4) Draw frame.
        screen.fill((0, 0, 0))

        for circle in circles:
            # Pygame draw calls expect integer pixel coordinates.
            pygame.draw.circle(
                screen, circle.color, (int(circle.x), int(circle.y)), circle.radius
            )

        # Draw effects after circles so they appear on top.
        if ENABLE_SPECIAL_EFFECTS:
            for effect in effects:
                effect.draw(screen)

        # Show the frame rate.
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        screen.blit(fps_text, (10, 10))

        # Show the current speed multiplier.
        speed_text = font.render(f"Speed: {sim_speed:.2f}x", True, (0, 200, 255))
        screen.blit(speed_text, (10, 40))

        # Show a pause label when the simulation is stopped.
        if paused:
            pause_text = font.render("PAUSED", True, (255, 220, 0))
            screen.blit(pause_text, (10, 70))

        # On-screen control reminder for the player.
        help_lines = [
            "Controls: [+] Faster  [-] Slower  [R] Reset Speed  [SPACE] Pause/Resume"
        ]
        draw_help_text(screen, help_font, help_lines, 10, HEIGHT - 50, (220, 220, 220))

        # Swap buffers: show the completed frame.
        pygame.display.flip()

    # Clean shutdown.
    pygame.quit()


# Run only when executed as a script, not when imported as a module.
if __name__ == "__main__":
    main()
