import pygame
import math
import random


class Gun(pygame.sprite.Sprite):
    def __init__(self, player, image):
        super().__init__()
        self.player       = player
        self.orbit_radius = 25
        self.original_image = image
        self.image        = self.original_image.copy()
        self.rect         = self.image.get_rect()
        self.current_angle = 0

    def swap_image(self, new_image):
        self.original_image = new_image

    def update(self):
        mx, my = pygame.mouse.get_pos()
        dx = mx - self.player.rect.centerx
        dy = my - self.player.rect.centery
        angle_rad   = math.atan2(dy, dx)
        self.current_angle = angle_rad

        gun_x = self.player.rect.centerx + math.cos(angle_rad) * self.orbit_radius
        gun_y = self.player.rect.centery + math.sin(angle_rad) * self.orbit_radius
        angle_deg = math.degrees(angle_rad)

        if mx < self.player.rect.centerx:
            rotated = pygame.transform.rotate(
                pygame.transform.flip(self.original_image, False, True), -angle_deg)
        else:
            rotated = pygame.transform.rotate(self.original_image, -angle_deg)

        self.image = rotated
        self.rect  = self.image.get_rect(center=(gun_x, gun_y))

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, color=(255, 200, 0), speed=15):
        super().__init__()
        self.original_image = pygame.Surface((10, 5), pygame.SRCALPHA)
        self.original_image.fill(color)
        self.image = pygame.transform.rotate(self.original_image, -math.degrees(angle))
        self.rect  = self.image.get_rect(center=(x, y))
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed

    def update(self, timescale=1.0):
        self.rect.x += self.vel_x * timescale
        self.rect.y += self.vel_y * timescale
        if not (-100 < self.rect.x < 1380 and -100 < self.rect.y < 820):
            self.kill()


class Spark(pygame.sprite.Sprite):
    def __init__(self, x, y, color=(255, 200, 0), size_range=(2, 5), speed=4):
        super().__init__()
        size = random.randint(*size_range)
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.rect     = self.image.get_rect(center=(x, y))
        self.vel_x    = random.uniform(-speed, speed)
        self.vel_y    = random.uniform(-speed, speed)
        self.lifespan = random.randint(10, 20)

    def update(self, timescale=1.0):
        self.rect.x += self.vel_x * timescale
        self.rect.y += self.vel_y * timescale
        self.vel_y  += 0.2 * timescale
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.kill()