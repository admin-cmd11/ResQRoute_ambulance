import pygame
import random
import sys
import math

# Initialize Pygame
pygame.init()
pygame.font.init()

# Screen Setup (Width expanded for Right-Side Interactive Panel)
WIDTH, HEIGHT = 1180, 720
SIM_WIDTH = 920  # Width allocated to the road grid simulation
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ResQRoute - Interactive V2I Preemption Simulation")
clock = pygame.time.Clock()

# Fonts
FONT_TITLE = pygame.font.SysFont("Segoe UI", 17, bold=True)
FONT_BODY = pygame.font.SysFont("Segoe UI", 12)
FONT_LABEL = pygame.font.SysFont("Segoe UI", 10, bold=True)
FONT_STATUS = pygame.font.SysFont("Segoe UI", 14, bold=True)
FONT_BTN = pygame.font.SysFont("Segoe UI", 12, bold=True)

# Colors
BG_COLOR = (24, 28, 36)
PANEL_BG = (34, 40, 49)
PANEL_BORDER = (53, 64, 80)
TEXT_WHITE = (240, 240, 245)
TEXT_MUTED = (160, 170, 185)
WHITE = (255, 255, 255)

ASPHALT = (40, 42, 48)
SHOULDER_RED = (200, 60, 60)
SHOULDER_WHITE = (230, 230, 230)
LANE_WHITE = (220, 220, 220)

RED_GLOW = (255, 60, 60)
GREEN_GLOW = (50, 235, 120)
BLUE_SIREN = (40, 140, 255)
CYAN_SIGNAL = (0, 230, 255)

CAR_PALETTE = [
    (52, 152, 219), (46, 204, 113), (155, 89, 182),
    (241, 196, 15), (230, 126, 34), (149, 165, 166), (54, 69, 79)
]

# Layout Geometry
CENTER_X, CENTER_Y = SIM_WIDTH // 2, HEIGHT // 2 + 20
ROAD_WIDTH = 130
HALF_ROAD = ROAD_WIDTH // 2
PREEMPTION_RANGE = 320

STOP_LINES = {
    "EAST": CENTER_X - HALF_ROAD,
    "WEST": CENTER_X + HALF_ROAD,
    "SOUTH": CENTER_Y - HALF_ROAD,
    "NORTH": CENTER_Y + HALF_ROAD
}


class Button:
    """Clickable UI Button for Guest Interaction"""
    def __init__(self, x, y, w, h, text, color, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.callback = callback
        self.hovered = False

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()

    def draw(self, surface):
        bg_col = (min(255, self.color[0] + 30), min(255, self.color[1] + 30), min(255, self.color[2] + 30)) if self.hovered else self.color
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=1, border_radius=6)
        
        txt_surf = FONT_BTN.render(self.text, True, TEXT_WHITE)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)


class SmartTrafficLight:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction

    def draw(self, surface, state, is_preempted):
        # Antenna
        pygame.draw.rect(surface, (100, 110, 125), (self.x + 12, self.y - 14, 6, 16))
        antenna_glow = CYAN_SIGNAL if is_preempted else (100, 100, 100)
        pygame.draw.circle(surface, antenna_glow, (self.x + 15, self.y - 16), 5)

        # Pole
        pygame.draw.rect(surface, (80, 85, 95), (self.x + 12, self.y + 65, 6, 20))

        # Housing
        housing_rect = pygame.Rect(self.x, self.y, 30, 65)
        pygame.draw.rect(surface, (20, 22, 25), housing_rect, border_radius=6)
        border_col = CYAN_SIGNAL if is_preempted else (60, 65, 75)
        pygame.draw.rect(surface, border_col, housing_rect, width=2, border_radius=6)

        # Bulbs
        r_color = RED_GLOW if state == "RED" else (60, 15, 15)
        g_color = GREEN_GLOW if state == "GREEN" else (15, 60, 25)

        if state == "RED":
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*RED_GLOW, 60), (15, 15), 14)
            surface.blit(glow_surf, (self.x, self.y + 2))

        if state == "GREEN":
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*GREEN_GLOW, 60), (15, 15), 14)
            surface.blit(glow_surf, (self.x, self.y + 34))

        pygame.draw.circle(surface, r_color, (self.x + 15, self.y + 16), 9)
        pygame.draw.circle(surface, g_color, (self.x + 15, self.y + 48), 9)


class IntersectionController:
    def __init__(self):
        self.current_phase = "EW"
        self.timer = 0
        self.phase_duration = 320
        self.preempted = False
        self.preempt_direction = None

    def update(self):
        if self.preempted:
            return

        self.timer += 1
        if self.timer >= self.phase_duration:
            self.timer = 0
            self.current_phase = "NS" if self.current_phase == "EW" else "EW"

    def trigger_preemption(self, direction):
        self.preempted = True
        self.preempt_direction = direction
        if direction in ["EAST", "WEST"]:
            self.current_phase = "EW"
        else:
            self.current_phase = "NS"

    def toggle_phase_manual(self):
        if not self.preempted:
            self.current_phase = "NS" if self.current_phase == "EW" else "EW"

    def release_preemption(self):
        self.preempted = False
        self.preempt_direction = None

    def get_signal_state(self, direction):
        if direction in ["EAST", "WEST"]:
            return "GREEN" if self.current_phase == "EW" else "RED"
        else:
            return "GREEN" if self.current_phase == "NS" else "RED"


class Vehicle:
    def __init__(self, direction, is_ambulance=False):
        self.direction = direction
        self.is_ambulance = is_ambulance
        self.length = 50 if is_ambulance else 40
        self.width = 22
        self.max_speed = 5.2 if is_ambulance else random.uniform(2.8, 3.4)
        self.speed = self.max_speed
        self.color = (245, 245, 250) if is_ambulance else random.choice(CAR_PALETTE)
        self.siren_timer = 0
        self.ping_radius = 0

        lane_offset = HALF_ROAD // 2
        if direction == "EAST":
            self.x, self.y = -60, CENTER_Y + lane_offset - (self.width // 2)
        elif direction == "WEST":
            self.x, self.y = SIM_WIDTH + 60, CENTER_Y - lane_offset - (self.width // 2)
        elif direction == "SOUTH":
            self.x, self.y = CENTER_X - lane_offset - (self.width // 2), -60
        elif direction == "NORTH":
            self.x, self.y = CENTER_X + lane_offset - (self.width // 2), HEIGHT + 60

    def update(self, all_cars, controller):
        stop_pos = STOP_LINES[self.direction]

        if self.direction == "EAST":
            dist_to_stop = stop_pos - (self.x + self.length)
        elif self.direction == "WEST":
            dist_to_stop = self.x - stop_pos
        elif self.direction == "SOUTH":
            dist_to_stop = stop_pos - (self.y + self.length)
        elif self.direction == "NORTH":
            dist_to_stop = self.y - stop_pos

        if self.is_ambulance:
            if 0 < dist_to_stop < PREEMPTION_RANGE:
                controller.trigger_preemption(self.direction)
            elif dist_to_stop < -100:
                controller.release_preemption()

        target_speed = self.max_speed
        signal_state = controller.get_signal_state(self.direction)

        # Braking at Signals (Civilians Stop Safely Outside Core Intersection)
        if signal_state == "RED" and not self.is_ambulance:
            if 0 < dist_to_stop < 170:
                target_speed = min(target_speed, (dist_to_stop / 170) * self.max_speed)
                if dist_to_stop < 14:  # Stopped 14px clear of stop line to prevent bumper clipping
                    target_speed = 0

        # Anti-Collision System (Handles Car-Car, Car-Ambulance, and Ambulance-Ambulance)
        same_dir = [c for c in all_cars if c != self and c.direction == self.direction]
        lead_car = self.get_lead_car(same_dir)
        if lead_car:
            dist_to_lead = self.get_distance_to(lead_car)
            
            # Safe buffer distance: enlarged for fast emergency units
            safe_buffer = 32 if (self.is_ambulance or lead_car.is_ambulance) else 22
            
            if dist_to_lead < 120:
                gap_speed = max(0, (dist_to_lead - safe_buffer) / 8)
                target_speed = min(target_speed, gap_speed)
                if dist_to_lead < (safe_buffer - 5):
                    target_speed = 0  # Hard stop if trailing too close

        if self.speed < target_speed:
            self.speed = min(self.max_speed, self.speed + 0.15)
        elif self.speed > target_speed:
            self.speed = max(0, self.speed - 0.4)

        if self.direction == "EAST":
            self.x += self.speed
        elif self.direction == "WEST":
            self.x -= self.speed
        elif self.direction == "SOUTH":
            self.y += self.speed
        elif self.direction == "NORTH":
            self.y -= self.speed

    def get_lead_car(self, cars):
        ahead = []
        for c in cars:
            if self.direction == "EAST" and c.x > self.x: ahead.append(c)
            elif self.direction == "WEST" and c.x < self.x: ahead.append(c)
            elif self.direction == "SOUTH" and c.y > self.y: ahead.append(c)
            elif self.direction == "NORTH" and c.y < self.y: ahead.append(c)
        if not ahead: return None
        return min(ahead, key=lambda c: self.get_distance_to(c))

    def get_distance_to(self, other):
        if self.direction in ["EAST", "WEST"]:
            return abs(other.x - self.x) - self.length
        return abs(other.y - self.y) - self.length

    def draw(self, surface, controller, signals):
        is_vert = self.direction in ["NORTH", "SOUTH"]
        w = self.width if is_vert else self.length
        h = self.length if is_vert else self.width

        shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 75), shadow_surf.get_rect(), border_radius=5)
        surface.blit(shadow_surf, (self.x + 3, self.y + 4))

        body_rect = pygame.Rect(self.x, self.y, w, h)
        pygame.draw.rect(surface, self.color, body_rect, border_radius=5)
        pygame.draw.rect(surface, (20, 20, 20), body_rect, width=1, border_radius=5)

        glass_color = (40, 50, 65)

        if self.direction == "EAST":
            pygame.draw.rect(surface, glass_color, (self.x + self.length - 12, self.y + 3, 5, self.width - 6), border_radius=1)
            pygame.draw.rect(surface, glass_color, (self.x + 8, self.y + 3, 4, self.width - 6), border_radius=1)
            pygame.draw.rect(surface, (255, 240, 150), (self.x + self.length - 2, self.y + 2, 2, 4))
            pygame.draw.rect(surface, (255, 240, 150), (self.x + self.length - 2, self.y + self.width - 6, 2, 4))
            pygame.draw.rect(surface, (200, 30, 30), (self.x, self.y + 2, 2, 4))
            pygame.draw.rect(surface, (200, 30, 30), (self.x, self.y + self.width - 6, 2, 4))

        elif self.direction == "WEST":
            pygame.draw.rect(surface, glass_color, (self.x + 7, self.y + 3, 5, self.width - 6), border_radius=1)
            pygame.draw.rect(surface, glass_color, (self.x + self.length - 12, self.y + 3, 4, self.width - 6), border_radius=1)
            pygame.draw.rect(surface, (255, 240, 150), (self.x, self.y + 2, 2, 4))
            pygame.draw.rect(surface, (255, 240, 150), (self.x, self.y + self.width - 6, 2, 4))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + self.length - 2, self.y + 2, 2, 4))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + self.length - 2, self.y + self.width - 6, 2, 4))

        elif self.direction == "SOUTH":
            pygame.draw.rect(surface, glass_color, (self.x + 3, self.y + self.length - 12, self.width - 6, 5), border_radius=1)
            pygame.draw.rect(surface, glass_color, (self.x + 3, self.y + 8, self.width - 6, 4), border_radius=1)
            pygame.draw.rect(surface, (255, 240, 150), (self.x + 2, self.y + self.length - 2, 4, 2))
            pygame.draw.rect(surface, (255, 240, 150), (self.x + self.width - 6, self.y + self.length - 2, 4, 2))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + 2, self.y, 4, 2))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + self.width - 6, self.y, 4, 2))

        elif self.direction == "NORTH":
            pygame.draw.rect(surface, glass_color, (self.x + 3, self.y + 7, self.width - 6, 5), border_radius=1)
            pygame.draw.rect(surface, glass_color, (self.x + 3, self.y + self.length - 12, self.width - 6, 4), border_radius=1)
            pygame.draw.rect(surface, (255, 240, 150), (self.x + 2, self.y, 4, 2))
            pygame.draw.rect(surface, (255, 240, 150), (self.x + self.width - 6, self.y, 4, 2))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + 2, self.y + self.length - 2, 4, 2))
            pygame.draw.rect(surface, (200, 30, 30), (self.x + self.width - 6, self.y + self.length - 2, 4, 2))

        if self.is_ambulance:
            cx, cy = self.x + w // 2, self.y + h // 2
            pygame.draw.rect(surface, RED_GLOW, (cx - 4, cy - 2, 8, 4))
            pygame.draw.rect(surface, RED_GLOW, (cx - 2, cy - 4, 4, 8))

            self.siren_timer += 1
            is_red = (self.siren_timer // 5) % 2 == 0
            siren_color = RED_GLOW if is_red else BLUE_SIREN

            siren_aura = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(siren_aura, (*siren_color, 80), (15, 15), 13)
            surface.blit(siren_aura, (cx - 15, cy - 15))
            pygame.draw.circle(surface, siren_color, (cx, cy), 3)

            if controller.preempted and controller.preempt_direction == self.direction:
                self.ping_radius = (self.ping_radius + 2) % 35
                ping_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                target_sig = signals[self.direction]
                pygame.draw.line(ping_surf, (*CYAN_SIGNAL, 90), (cx, cy), (target_sig.x + 15, target_sig.y + 30), 1)
                alpha = int(255 * (1 - self.ping_radius / 35))
                pygame.draw.circle(ping_surf, (*CYAN_SIGNAL, alpha), (cx, cy), self.ping_radius, width=2)
                surface.blit(ping_surf, (0, 0))


def draw_environment(surface):
    surface.fill(BG_COLOR)

    # Asphalt Grid
    pygame.draw.rect(surface, ASPHALT, (0, CENTER_Y - HALF_ROAD, SIM_WIDTH, ROAD_WIDTH))
    pygame.draw.rect(surface, ASPHALT, (CENTER_X - HALF_ROAD, 0, ROAD_WIDTH, HEIGHT))

    # Shoulders
    stripe = 18
    for i in range(0, SIM_WIDTH, stripe * 2):
        if not (CENTER_X - HALF_ROAD - 10 <= i <= CENTER_X + HALF_ROAD + 10):
            pygame.draw.rect(surface, SHOULDER_RED, (i, CENTER_Y - HALF_ROAD - 5, stripe, 5))
            pygame.draw.rect(surface, SHOULDER_WHITE, (i + stripe, CENTER_Y - HALF_ROAD - 5, stripe, 5))
            pygame.draw.rect(surface, SHOULDER_RED, (i, CENTER_Y + HALF_ROAD, stripe, 5))
            pygame.draw.rect(surface, SHOULDER_WHITE, (i + stripe, CENTER_Y + HALF_ROAD, stripe, 5))

    for i in range(0, HEIGHT, stripe * 2):
        if not (CENTER_Y - HALF_ROAD - 10 <= i <= CENTER_Y + HALF_ROAD + 10):
            pygame.draw.rect(surface, SHOULDER_RED, (CENTER_X - HALF_ROAD - 5, i, 5, stripe))
            pygame.draw.rect(surface, SHOULDER_WHITE, (CENTER_X - HALF_ROAD - 5, i + stripe, 5, stripe))
            pygame.draw.rect(surface, SHOULDER_RED, (CENTER_X + HALF_ROAD, i, 5, stripe))
            pygame.draw.rect(surface, SHOULDER_WHITE, (CENTER_X + HALF_ROAD, i + stripe, 5, stripe))

    # Center Lines
    for x in range(0, SIM_WIDTH, 35):
        if not (CENTER_X - HALF_ROAD <= x <= CENTER_X + HALF_ROAD):
            pygame.draw.line(surface, LANE_WHITE, (x, CENTER_Y), (x + 18, CENTER_Y), 2)

    for y in range(0, HEIGHT, 35):
        if not (CENTER_Y - HALF_ROAD <= y <= CENTER_Y + HALF_ROAD):
            pygame.draw.line(surface, LANE_WHITE, (CENTER_X, y), (CENTER_X, y + 18), 2)

    # Stop Lines
    pygame.draw.line(surface, WHITE, (STOP_LINES["EAST"], CENTER_Y), (STOP_LINES["EAST"], CENTER_Y + HALF_ROAD), 5)
    pygame.draw.line(surface, WHITE, (STOP_LINES["WEST"], CENTER_Y - HALF_ROAD), (STOP_LINES["WEST"], CENTER_Y), 5)
    pygame.draw.line(surface, WHITE, (CENTER_X - HALF_ROAD, STOP_LINES["SOUTH"]), (CENTER_X, STOP_LINES["SOUTH"]), 5)
    pygame.draw.line(surface, WHITE, (CENTER_X, STOP_LINES["NORTH"]), (CENTER_X + HALF_ROAD, STOP_LINES["NORTH"]), 5)


def draw_hud(surface, cars, controller):
    pygame.draw.rect(surface, PANEL_BG, (0, 0, SIM_WIDTH, 80))
    pygame.draw.line(surface, PANEL_BORDER, (0, 80), (SIM_WIDTH, 80), 2)

    title_txt = FONT_TITLE.render("ResQRoute : V2I 4-WAY INTERSECTION SYSTEM", True, CYAN_SIGNAL)
    subtitle_txt = FONT_BODY.render("Dynamic Cross-Traffic Green Corridor Preemption", True, TEXT_MUTED)
    surface.blit(title_txt, (20, 14))
    surface.blit(subtitle_txt, (20, 38))

    total_cars = len(cars)
    ambulances = len([c for c in cars if c.is_ambulance])

    pygame.draw.rect(surface, BG_COLOR, (440, 12, 110, 56), border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, (440, 12, 110, 56), width=1, border_radius=6)
    surface.blit(FONT_LABEL.render("TRAFFIC", True, TEXT_MUTED), (450, 16))
    surface.blit(FONT_TITLE.render(str(total_cars), True, TEXT_WHITE), (450, 32))

    pygame.draw.rect(surface, BG_COLOR, (560, 12, 110, 56), border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, (560, 12, 110, 56), width=1, border_radius=6)
    surface.blit(FONT_LABEL.render("EMERGENCY", True, TEXT_MUTED), (570, 16))
    surface.blit(FONT_TITLE.render(str(ambulances), True, BLUE_SIREN), (570, 32))

    card_bg = (20, 45, 55) if controller.preempted else BG_COLOR
    card_border = CYAN_SIGNAL if controller.preempted else PANEL_BORDER
    pygame.draw.rect(surface, card_bg, (680, 12, 220, 56), border_radius=6)
    pygame.draw.rect(surface, card_border, (680, 12, 220, 56), width=2 if controller.preempted else 1, border_radius=6)
    
    surface.blit(FONT_LABEL.render("V2I COMM LINK", True, TEXT_MUTED), (690, 16))
    
    if controller.preempted:
        status_str = f"LOCKED [{controller.preempt_direction}]"
        status_col = GREEN_GLOW
    else:
        status_str = "IDLE (CYCLING)"
        status_col = TEXT_MUTED

    surface.blit(FONT_STATUS.render(status_str, True, status_col), (690, 32))


def draw_side_panel(surface, buttons):
    panel_x = SIM_WIDTH
    panel_w = WIDTH - SIM_WIDTH

    pygame.draw.rect(surface, PANEL_BG, (panel_x, 0, panel_w, HEIGHT))
    pygame.draw.line(surface, PANEL_BORDER, (panel_x, 0), (panel_x, HEIGHT), 2)

    hdr = FONT_TITLE.render("EXPO CONTROL DECK", True, CYAN_SIGNAL)
    surface.blit(hdr, (panel_x + 15, 15))

    sub = FONT_LABEL.render("INTERACTIVE SIMULATOR", True, TEXT_MUTED)
    surface.blit(sub, (panel_x + 15, 38))

    pygame.draw.line(surface, PANEL_BORDER, (panel_x + 15, 55), (panel_x + panel_w - 15, 55), 1)

    lbl1 = FONT_BTN.render("QUICK CONTROLS:", True, TEXT_WHITE)
    surface.blit(lbl1, (panel_x + 15, 68))

    for btn in buttons:
        btn.draw(surface)

    guide_y = 380
    pygame.draw.line(surface, PANEL_BORDER, (panel_x + 15, guide_y), (panel_x + panel_w - 15, guide_y), 1)
    
    lbl2 = FONT_BTN.render("KEYBOARD SHORTCUTS:", True, TEXT_WHITE)
    surface.blit(lbl2, (panel_x + 15, guide_y + 12))

    shortcuts = [
        ("[ A ]", "Spawn Random Ambulance"),
        ("[ C ]", "Spawn Civilian Car"),
        ("[ E / W ]", "Dispatch East / West Unit"),
        ("[ N / S ]", "Dispatch North / South Unit"),
        ("[ J ]", "Stress Test (Traffic Jam)"),
        ("[ SPACE ]", "Manual Signal Switch"),
        ("[ R ]", "Reset Simulation Scene")
    ]

    curr_y = guide_y + 36
    for key, desc in shortcuts:
        k_surf = FONT_BTN.render(key, True, CYAN_SIGNAL)
        d_surf = FONT_BODY.render(desc, True, TEXT_WHITE)
        surface.blit(k_surf, (panel_x + 15, curr_y))
        surface.blit(d_surf, (panel_x + 85, curr_y))
        curr_y += 24


def main():
    controller = IntersectionController()
    
    signals = {
        "EAST": SmartTrafficLight(STOP_LINES["EAST"] - 35, CENTER_Y + HALF_ROAD + 8, "EAST"),
        "WEST": SmartTrafficLight(STOP_LINES["WEST"] + 10, CENTER_Y - HALF_ROAD - 85, "WEST"),
        "SOUTH": SmartTrafficLight(CENTER_X - HALF_ROAD - 40, STOP_LINES["SOUTH"] - 70, "SOUTH"),
        "NORTH": SmartTrafficLight(CENTER_X + HALF_ROAD + 10, STOP_LINES["NORTH"] + 10, "NORTH")
    }

    cars = []
    spawn_timer = 0

    # Helper function to check if spawn entry is clear before adding
    def is_spawn_clear(direction):
        dir_cars = [c for c in cars if c.direction == direction]
        if not dir_cars:
            return True
        if direction == "EAST":
            return min([c.x for c in dir_cars]) > 80
        elif direction == "WEST":
            return max([c.x for c in dir_cars]) < SIM_WIDTH - 80
        elif direction == "SOUTH":
            return min([c.y for c in dir_cars]) > 80
        elif direction == "NORTH":
            return max([c.y for c in dir_cars]) < HEIGHT - 80
        return True

    def spawn_direction_vehicle(direction, is_ambulance=False):
        if is_spawn_clear(direction):
            cars.append(Vehicle(direction, is_ambulance=is_ambulance))

    def spawn_random_amb():
        d = random.choice(["EAST", "WEST", "NORTH", "SOUTH"])
        spawn_direction_vehicle(d, is_ambulance=True)

    def spawn_car():
        d = random.choice(["EAST", "WEST", "NORTH", "SOUTH"])
        spawn_direction_vehicle(d, is_ambulance=False)

    def trigger_jam():
        for d in ["EAST", "WEST", "NORTH", "SOUTH"]:
            spawn_direction_vehicle(d, is_ambulance=False)

    def reset_sim():
        cars.clear()
        controller.release_preemption()

    def toggle_signal():
        controller.toggle_phase_manual()

    btn_x = SIM_WIDTH + 15
    btn_w = WIDTH - SIM_WIDTH - 30
    
    buttons = [
        Button(btn_x, 95, btn_w, 36, "+ SPAWN AMBULANCE", (180, 40, 40), spawn_random_amb),
        Button(btn_x, 140, btn_w, 36, "+ SPAWN CIVILIAN CAR", (40, 110, 180), spawn_car),
        Button(btn_x, 185, btn_w, 36, "⚡ TRAFFIC JAM TEST", (180, 120, 30), trigger_jam),
        Button(btn_x, 230, btn_w, 36, "🔄 SWITCH SIGNAL LIGHT", (40, 140, 90), toggle_signal),
        Button(btn_x, 275, btn_w, 36, "🧹 RESET SIMULATION", (70, 80, 95), reset_sim)
    ]

    running = True
    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for btn in buttons:
            btn.check_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in buttons:
                    btn.handle_click(mouse_pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    spawn_random_amb()
                elif event.key == pygame.K_c:
                    spawn_car()
                elif event.key == pygame.K_e:
                    spawn_direction_vehicle("EAST", is_ambulance=True)
                elif event.key == pygame.K_w:
                    spawn_direction_vehicle("WEST", is_ambulance=True)
                elif event.key == pygame.K_n:
                    spawn_direction_vehicle("NORTH", is_ambulance=True)
                elif event.key == pygame.K_s:
                    spawn_direction_vehicle("SOUTH", is_ambulance=True)
                elif event.key == pygame.K_j:
                    trigger_jam()
                elif event.key == pygame.K_SPACE:
                    toggle_signal()
                elif event.key == pygame.K_r:
                    reset_sim()

        # Ambient Civilian Traffic Spawning
        spawn_timer += 1
        if spawn_timer > 55:
            d = random.choice(["EAST", "WEST", "NORTH", "SOUTH"])
            spawn_direction_vehicle(d, is_ambulance=False)
            spawn_timer = 0

        # Updates
        controller.update()
        for car in cars:
            car.update(cars, controller)

        cars = [c for c in cars if -120 < c.x < SIM_WIDTH + 120 and -120 < c.y < HEIGHT + 120]

        # Rendering
        draw_environment(screen)

        for car in cars:
            car.draw(screen, controller, signals)

        for dir_key, sig in signals.items():
            state = controller.get_signal_state(dir_key)
            is_p = controller.preempted and controller.preempt_direction == dir_key
            sig.draw(screen, state, is_p)

        draw_hud(screen, cars, controller)
        draw_side_panel(screen, buttons)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
