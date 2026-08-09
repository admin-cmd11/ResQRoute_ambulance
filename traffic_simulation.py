import pygame
import random
import sys

# Initialize Pygame
pygame.init()
pygame.font.init()

# Screen Dimensions & Settings
WIDTH, HEIGHT = 1100, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Traffic Flow & Priority Yielding Simulation")
clock = pygame.time.Clock()

# Fonts
FONT_TITLE = pygame.font.SysFont("Segoe UI", 20, bold=True)
FONT_BODY = pygame.font.SysFont("Segoe UI", 14)
FONT_LABEL = pygame.font.SysFont("Segoe UI", 12)

# Color Palette (Expo Dark Theme)
BG_COLOR = (24, 28, 36)
PANEL_BG = (34, 40, 49)
PANEL_BORDER = (53, 64, 80)
TEXT_WHITE = (240, 240, 245)
TEXT_MUTED = (160, 170, 185)
WHITE = (255, 255, 255)

ASPHALT = (40, 42, 48)
SHOULDER_RED = (200, 60, 60)
SHOULDER_WHITE = (230, 230, 230)
LANE_YELLOW = (240, 190, 40)
LANE_WHITE = (220, 220, 220)

RED_GLOW = (255, 60, 60)
GREEN_GLOW = (50, 235, 120)
BLUE_SIREN = (40, 140, 255)

# Detailed Vehicle Palette
CAR_PALETTE = [
    (52, 152, 219),  # Electric Blue
    (46, 204, 113),  # Emerald
    (155, 89, 182),  # Amethyst
    (241, 196, 15),  # Sunflower
    (230, 126, 34),  # Carrot
    (149, 165, 166), # Silver
    (54, 69, 79)     # Charcoal
]

# Simulation Constants
ROAD_Y = 240
ROAD_HEIGHT = 160
LANE_HEIGHT = ROAD_HEIGHT // 2
STOP_LINE_X = 750
SAFE_DISTANCE = 25


class ManualTrafficLight:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = "RED"

    def toggle(self):
        self.state = "GREEN" if self.state == "RED" else "RED"

    def draw(self, surface):
        # Pole
        pygame.draw.rect(surface, (80, 85, 95), (self.x + 12, self.y + 70, 6, 40))
        
        # Light Housing
        housing_rect = pygame.Rect(self.x, self.y, 30, 70)
        pygame.draw.rect(surface, (20, 22, 25), housing_rect, border_radius=6)
        pygame.draw.rect(surface, (60, 65, 75), housing_rect, width=2, border_radius=6)

        # Lights with radial glow effect
        r_color = RED_GLOW if self.state == "RED" else (60, 15, 15)
        g_color = GREEN_GLOW if self.state == "GREEN" else (15, 60, 25)

        if self.state == "RED":
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*RED_GLOW, 50), (15, 15), 14)
            surface.blit(glow_surf, (self.x + 15 - 15, self.y + 18 - 15))

        if self.state == "GREEN":
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*GREEN_GLOW, 50), (15, 15), 14)
            surface.blit(glow_surf, (self.x + 15 - 15, self.y + 52 - 15))

        pygame.draw.circle(surface, r_color, (self.x + 15, self.y + 18), 10)
        pygame.draw.circle(surface, g_color, (self.x + 15, self.y + 52), 10)


class Vehicle:
    def __init__(self, x, lane, is_ambulance=False):
        self.x = x
        self.lane = lane
        self.target_y = ROAD_Y + (lane * LANE_HEIGHT) + (LANE_HEIGHT // 2) - 12
        self.y = self.target_y
        self.width = 48 if is_ambulance else 42
        self.height = 24
        self.is_ambulance = is_ambulance

        self.max_speed = 5.5 if is_ambulance else random.uniform(3.2, 4.2)
        self.speed = self.max_speed
        self.acceleration = 0.15 if is_ambulance else 0.08
        self.deceleration = 0.25
        self.color = (245, 245, 250) if is_ambulance else random.choice(CAR_PALETTE)
        
        self.changing_lane = False
        self.lane_change_cooldown = 0
        self.siren_timer = 0

    def check_lane_change(self, all_cars):
        if self.changing_lane or self.lane_change_cooldown > 0:
            return

        target_lane = 1 - self.lane
        target_clear = True
        
        for car in all_cars:
            if car != self and car.lane == target_lane:
                if abs(car.x - self.x) < 65:
                    target_clear = False
                    break

        if target_clear:
            self.lane = target_lane
            self.target_y = ROAD_Y + (self.lane * LANE_HEIGHT) + (LANE_HEIGHT // 2) - 12
            self.changing_lane = True
            self.lane_change_cooldown = 100

    def update(self, all_cars, traffic_light):
        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown -= 1

        if abs(self.y - self.target_y) > 1:
            self.y += (self.target_y - self.y) * 0.1
        else:
            self.y = self.target_y
            self.changing_lane = False

        target_speed = self.max_speed

        lane_cars = [c for c in all_cars if c.lane == self.lane and c.x > self.x]
        lead_car = min(lane_cars, key=lambda c: c.x) if lane_cars else None

        # Emergency yield logic
        ambulance_behind = False
        for car in all_cars:
            if car.is_ambulance and car.x < self.x and (self.x - car.x) < 200:
                ambulance_behind = True
                break

        if ambulance_behind and not self.is_ambulance:
            self.check_lane_change(all_cars)

        # Signal logic
        if traffic_light.state == "RED" and not self.is_ambulance:
            dist_to_signal = STOP_LINE_X - (self.x + self.width)
            if 0 < dist_to_signal < 160:
                target_speed = min(target_speed, (dist_to_signal / 160) * self.max_speed)
                if dist_to_signal < 6:
                    target_speed = 0

        # Proximity control
        if lead_car is not None:
            dist_to_lead = lead_car.x - (self.x + self.width)
            if dist_to_lead < 130:
                gap_speed = max(0, (dist_to_lead - SAFE_DISTANCE) / 10)
                target_speed = min(target_speed, gap_speed)

                if dist_to_lead < 70 and self.speed < (self.max_speed * 0.6) and not self.is_ambulance:
                    self.check_lane_change(all_cars)

        # Acceleration management
        if self.speed < target_speed:
            self.speed = min(self.max_speed, self.speed + self.acceleration)
        elif self.speed > target_speed:
            self.speed = max(0, self.speed - self.deceleration)

        self.x += self.speed

    def draw(self, surface):
        # Shadow Effect
        shadow_rect = pygame.Rect(self.x + 3, self.y + 4, self.width, self.height)
        shadow_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect(), border_radius=5)
        surface.blit(shadow_surf, shadow_rect)

        # Vehicle Body
        body_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, self.color, body_rect, border_radius=5)
        pygame.draw.rect(surface, (20, 20, 20), body_rect, width=1, border_radius=5)

        # Windshields & Roof Details
        glass_color = (40, 50, 65)
        pygame.draw.rect(surface, glass_color, (self.x + self.width - 12, self.y + 3, 5, self.height - 6), border_radius=1)
        pygame.draw.rect(surface, glass_color, (self.x + 8, self.y + 3, 4, self.height - 6), border_radius=1)

        # Lights (Headlights & Taillights)
        pygame.draw.rect(surface, (255, 240, 150), (self.x + self.width - 2, self.y + 2, 2, 4))
        pygame.draw.rect(surface, (255, 240, 150), (self.x + self.width - 2, self.y + self.height - 6, 2, 4))
        pygame.draw.rect(surface, (200, 30, 30), (self.x, self.y + 2, 2, 4))
        pygame.draw.rect(surface, (200, 30, 30), (self.x, self.y + self.height - 6, 2, 4))

        if self.is_ambulance:
            # Cross Graphic
            pygame.draw.rect(surface, RED_GLOW, (self.x + 18, self.y + 10, 8, 4))
            pygame.draw.rect(surface, RED_GLOW, (self.x + 20, self.y + 8, 4, 8))

            # Siren System with Strobe
            self.siren_timer += 1
            is_red = (self.siren_timer // 6) % 2 == 0
            siren_color = RED_GLOW if is_red else BLUE_SIREN

            # Dynamic Aura
            siren_aura = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(siren_aura, (*siren_color, 60), (15, 15), 12)
            surface.blit(siren_aura, (self.x + 22 - 15, self.y + 12 - 15))

            pygame.draw.circle(surface, siren_color, (int(self.x + 22), int(self.y + 12)), 3)


def draw_environment(surface):
    # Road Base
    pygame.draw.rect(surface, ASPHALT, (0, ROAD_Y, WIDTH, ROAD_HEIGHT))

    # Kerbs / Shoulders
    stripe_w = 20
    for x in range(0, WIDTH, stripe_w * 2):
        pygame.draw.rect(surface, SHOULDER_RED, (x, ROAD_Y - 6, stripe_w, 6))
        pygame.draw.rect(surface, SHOULDER_WHITE, (x + stripe_w, ROAD_Y - 6, stripe_w, 6))
        pygame.draw.rect(surface, SHOULDER_RED, (x, ROAD_Y + ROAD_HEIGHT, stripe_w, 6))
        pygame.draw.rect(surface, SHOULDER_WHITE, (x + stripe_w, ROAD_Y + ROAD_HEIGHT, stripe_w, 6))

    # Center Divider (Dashed)
    divider_y = ROAD_Y + LANE_HEIGHT
    for x in range(0, WIDTH, 35):
        pygame.draw.line(surface, LANE_WHITE, (x, divider_y), (x + 18, divider_y), 2)

    # Stop Line & Markings
    pygame.draw.line(surface, WHITE, (STOP_LINE_X, ROAD_Y + 4), (STOP_LINE_X, ROAD_Y + ROAD_HEIGHT - 4), 6)


def draw_hud(surface, cars, traffic_light):
    # Header Panel
    pygame.draw.rect(surface, PANEL_BG, (0, 0, WIDTH, 100))
    pygame.draw.line(surface, PANEL_BORDER, (0, 100), (WIDTH, 100), 2)

    # Project Titles
    title_txt = FONT_TITLE.render("URBAN TRAFFIC & EMERGENCY YIELD SIMULATOR", True, TEXT_WHITE)
    subtitle_txt = FONT_LABEL.render("High School Engineering Expo Demonstration", True, TEXT_MUTED)
    surface.blit(title_txt, (25, 20))
    surface.blit(subtitle_txt, (25, 48))

    # Stats Indicators
    total_cars = len(cars)
    ambulances = len([c for c in cars if c.is_ambulance])

    # Card 1: Active Vehicles
    pygame.draw.rect(surface, BG_COLOR, (480, 18, 140, 64), border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, (480, 18, 140, 64), width=1, border_radius=6)
    surface.blit(FONT_LABEL.render("ACTIVE VEHICLES", True, TEXT_MUTED), (490, 24))
    surface.blit(FONT_TITLE.render(str(total_cars), True, TEXT_WHITE), (490, 42))

    # Card 2: Priority Units
    pygame.draw.rect(surface, BG_COLOR, (635, 18, 140, 64), border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, (635, 18, 140, 64), width=1, border_radius=6)
    surface.blit(FONT_LABEL.render("EMERGENCY UNITS", True, TEXT_MUTED), (645, 24))
    surface.blit(FONT_TITLE.render(str(ambulances), True, BLUE_SIREN), (645, 42))

    # Card 3: Signal Controller State
    pygame.draw.rect(surface, BG_COLOR, (790, 18, 150, 64), border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, (790, 18, 150, 64), width=1, border_radius=6)
    surface.blit(FONT_LABEL.render("SIGNAL STATUS", True, TEXT_MUTED), (800, 24))
    
    state_color = RED_GLOW if traffic_light.state == "RED" else GREEN_GLOW
    surface.blit(FONT_TITLE.render(traffic_light.state, True, state_color), (800, 42))

    # Bottom Control Bar
    pygame.draw.rect(surface, PANEL_BG, (0, HEIGHT - 50, WIDTH, 50))
    pygame.draw.line(surface, PANEL_BORDER, (0, HEIGHT - 50), (WIDTH, HEIGHT - 50), 2)
    
    control_str = "[ SPACEBAR ] Toggle Traffic Signal State    |    Autonomous Emergency Lane Clearance Active"
    surface.blit(FONT_BODY.render(control_str, True, TEXT_WHITE), (25, HEIGHT - 33))


def main():
    traffic_light = ManualTrafficLight(STOP_LINE_X + 15, ROAD_Y - 85)
    cars = []
    spawn_timer = 0
    ambulance_timer = 0

    running = True
    while running:
        clock.tick(60)
        screen.fill(BG_COLOR)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    traffic_light.toggle()

        # Spawning Logic
        spawn_timer += 1
        if spawn_timer > random.randint(40, 75):
            lane = random.choice([0, 1])
            lane_cars = [c for c in cars if c.lane == lane]
            if not lane_cars or lane_cars[-1].x > 70:
                cars.append(Vehicle(-50, lane))
                spawn_timer = 0

        ambulance_timer += 1
        if ambulance_timer > 550:
            lane = random.choice([0, 1])
            lane_cars = [c for c in cars if c.lane == lane]
            if not lane_cars or lane_cars[-1].x > 90:
                cars.append(Vehicle(-60, lane, is_ambulance=True))
                ambulance_timer = 0

        # Updates
        for car in cars:
            car.update(cars, traffic_light)

        cars = [car for car in cars if car.x < WIDTH + 60]

        # Rendering
        draw_environment(screen)
        traffic_light.draw(screen)

        for car in cars:
            car.draw(screen)

        draw_hud(screen, cars, traffic_light)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
