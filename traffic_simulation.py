import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Screen Dimensions & Settings
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2D Multi-Lane Traffic Simulation with Emergency Vehicle")
clock = pygame.time.Clock()

# Colors
GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 220, 50)
BLUE = (50, 100, 220)
YELLOW = (240, 200, 50)
CAR_COLORS = [(70, 130, 180), (220, 100, 50), (150, 100, 200), (200, 200, 70), (50, 180, 120)]

# Simulation Constants
ROAD_Y = HEIGHT // 2 - 60
ROAD_HEIGHT = 120
LANE_HEIGHT = ROAD_HEIGHT // 2
STOP_LINE_X = 700
SAFE_DISTANCE = 20

class ManualTrafficLight:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = "RED"  # Default state

    def toggle(self):
        self.state = "GREEN" if self.state == "RED" else "RED"

    def draw(self, surface):
        pygame.draw.rect(surface, (30, 30, 30), (self.x, self.y, 30, 60), border_radius=5)
        r_color = RED if self.state == "RED" else (80, 0, 0)
        g_color = GREEN if self.state == "GREEN" else (0, 80, 0)

        pygame.draw.circle(surface, r_color, (self.x + 15, self.y + 15), 10)
        pygame.draw.circle(surface, g_color, (self.x + 15, self.y + 45), 10)


class Vehicle:
    def __init__(self, x, lane, is_ambulance=False):
        self.x = x
        self.lane = lane
        self.target_y = ROAD_Y + (lane * LANE_HEIGHT) + (LANE_HEIGHT // 2) - 10
        self.y = self.target_y
        self.width = 40 if is_ambulance else 35
        self.height = 20
        self.is_ambulance = is_ambulance

        self.max_speed = 6.0 if is_ambulance else random.uniform(3.5, 4.5)
        self.speed = self.max_speed
        self.acceleration = 0.15 if is_ambulance else 0.1
        self.deceleration = 0.3
        self.color = WHITE if is_ambulance else random.choice(CAR_COLORS)
        
        # Lane change mechanics
        self.changing_lane = False
        self.lane_change_cooldown = 0
        self.siren_timer = 0

    def check_lane_change(self, all_cars):
        if self.changing_lane or self.lane_change_cooldown > 0:
            return

        target_lane = 1 - self.lane  # Switch to opposite lane
        
        # Check if target lane is clear (no cars in proximity)
        target_clear = True
        for car in all_cars:
            if car != self and car.lane == target_lane:
                # Need distance ahead and behind to safely merge
                if abs(car.x - self.x) < 55:
                    target_clear = False
                    break

        if target_clear:
            self.lane = target_lane
            self.target_y = ROAD_Y + (self.lane * LANE_HEIGHT) + (LANE_HEIGHT // 2) - 10
            self.changing_lane = True
            self.lane_change_cooldown = 120  # Cooldown frame count

    def update(self, all_cars, traffic_light):
        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown -= 1

        # Smooth Y movement for lane changing
        if abs(self.y - self.target_y) > 1:
            self.y += (self.target_y - self.y) * 0.1
        else:
            self.y = self.target_y
            self.changing_lane = False

        target_speed = self.max_speed

        # Find closest lead vehicle in current lane
        lane_cars = [c for c in all_cars if c.lane == self.lane and c.x > self.x]
        lead_car = min(lane_cars, key=lambda c: c.x) if lane_cars else None

        # Check for approaching ambulance behind (Yield rule)
        ambulance_behind = False
        for car in all_cars:
            if car.is_ambulance and car.x < self.x and (self.x - car.x) < 180:
                ambulance_behind = True
                break

        # If ambulance is behind us, attempt to switch lanes to pull over
        if ambulance_behind and not self.is_ambulance:
            self.check_lane_change(all_cars)

        # 1. Traffic Light Logic (Ambulances ignore red lights!)
        if traffic_light.state == "RED" and not self.is_ambulance:
            dist_to_signal = STOP_LINE_X - (self.x + self.width)
            if 0 < dist_to_signal < 150:
                target_speed = min(target_speed, (dist_to_signal / 150) * self.max_speed)
                if dist_to_signal < 5:
                    target_speed = 0

        # 2. Lead Vehicle Distance Logic
        if lead_car is not None:
            dist_to_lead = lead_car.x - (self.x + self.width)
            if dist_to_lead < 120:
                gap_speed = max(0, (dist_to_lead - SAFE_DISTANCE) / 10)
                target_speed = min(target_speed, gap_speed)

                # Consider switching lanes if blocked by slow car (Regular cars only)
                if dist_to_lead < 60 and self.speed < (self.max_speed * 0.6) and not self.is_ambulance:
                    self.check_lane_change(all_cars)

        # Adjust Speed
        if self.speed < target_speed:
            self.speed = min(self.max_speed, self.speed + self.acceleration)
        elif self.speed > target_speed:
            self.speed = max(0, self.speed - self.deceleration)

        self.x += self.speed

    def draw(self, surface):
        # Body
        pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, self.height), border_radius=4)

        if self.is_ambulance:
            # Red Cross
            pygame.draw.rect(surface, RED, (self.x + 15, self.y + 8, 10, 4))
            pygame.draw.rect(surface, RED, (self.x + 18, self.y + 5, 4, 10))
            
            # Flashing Lights
            self.siren_timer += 1
            siren_color = RED if (self.siren_timer // 10) % 2 == 0 else BLUE
            pygame.draw.circle(surface, siren_color, (int(self.x + self.width - 8), int(self.y + self.height // 2)), 4)
        else:
            # Windshield
            pygame.draw.rect(surface, (200, 230, 255), (self.x + self.width - 10, self.y + 3, 6, self.height - 6))


def main():
    traffic_light = ManualTrafficLight(STOP_LINE_X + 10, ROAD_Y - 70)
    cars = []
    spawn_timer = 0
    ambulance_timer = 0

    running = True
    while running:
        clock.tick(60)
        screen.fill((30, 100, 30))

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    traffic_light.toggle()

        # Regular Car Spawning
        spawn_timer += 1
        if spawn_timer > random.randint(35, 70):
            lane = random.choice([0, 1])
            lane_cars = [c for c in cars if c.lane == lane]
            if not lane_cars or lane_cars[-1].x > 60:
                cars.append(Vehicle(-40, lane))
                spawn_timer = 0

        # Ambulance Spawning (Every ~10 seconds)
        ambulance_timer += 1
        if ambulance_timer > 600:
            lane = random.choice([0, 1])
            lane_cars = [c for c in cars if c.lane == lane]
            if not lane_cars or lane_cars[-1].x > 80:
                cars.append(Vehicle(-50, lane, is_ambulance=True))
                ambulance_timer = 0

        # Update all cars
        for car in cars:
            car.update(cars, traffic_light)

        # Remove off-screen cars
        cars = [car for car in cars if car.x < WIDTH + 60]

        # --- DRAWING ---
        # Main Road
        pygame.draw.rect(screen, GRAY, (0, ROAD_Y, WIDTH, ROAD_HEIGHT))
        
        # Lane Line (Dashed)
        divider_y = ROAD_Y + LANE_HEIGHT
        for x in range(0, WIDTH, 40):
            pygame.draw.line(screen, WHITE, (x, divider_y), (x + 20, divider_y), 2)

        # Stop Line
        pygame.draw.line(screen, WHITE, (STOP_LINE_X, ROAD_Y), (STOP_LINE_X, ROAD_Y + ROAD_HEIGHT), 5)

        # Signal Box
        traffic_light.draw(screen)

        # Draw Cars
        for car in cars:
            car.draw(screen)

        # Instructions UI
        font = pygame.font.SysFont(None, 24)
        screen.blit(font.render("Press [ SPACEBAR ] to toggle light RED / GREEN", True, WHITE), (20, 20))
        
        state_color = RED if traffic_light.state == "RED" else GREEN
        screen.blit(font.render(f"Light State: {traffic_light.state}", True, state_color), (20, 45))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
