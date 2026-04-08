import pygame
import math
import random
class Gun(pygame.sprite.Sprite):
    def __init__(self, player,image):
        super().__init__()
        self.player = player # the gun needs to know who is holding it
        self.orbit_radius = 25 # how far away from the player the gun floats
        
        # create a simple dark grey rectangle for the gun graphic
        self.original_image = image
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        self.current_angle = 0

    def swap_image(self, new_image):
        """Swaps the base image of the gun when changing weapons."""
        self.original_image = new_image

    def update(self):
        # get the current mouse position
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # calculate the distance and angle from the player's center
        dx = mouse_x - self.player.rect.centerx
        dy = mouse_y - self.player.rect.centery
        angle_rad = math.atan2(dy, dx)

        # calculate the new orbit position using sine and cosine
        gun_x = self.player.rect.centerx + (math.cos(angle_rad) * self.orbit_radius)
        gun_y = self.player.rect.centery + (math.sin(angle_rad) * self.orbit_radius)

        # convert radians to degrees for pygame rotation
        angle_deg = math.degrees(angle_rad)
        self.current_angle = angle_rad
        
        # flip the gun vertically if the mouse is on the left side of the screen
        if mouse_x < self.player.rect.centerx:
            flipped_gun = pygame.transform.flip(self.original_image, False, True)
            self.image = pygame.transform.rotate(flipped_gun, -angle_deg)
        else:
            self.image = pygame.transform.rotate(self.original_image, -angle_deg)
            
        # re-center the bounding box so the gun doesn't wobble when spinning
        self.rect = self.image.get_rect(center=(gun_x, gun_y))
        
    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, color=(255, 200, 0), speed=15):
        super().__init__()
        self.original_image = pygame.Surface((10, 5), pygame.SRCALPHA)
        self.original_image.fill(color) 
        
        # Rotate the bullet so it faces the direction it is flying
        self.image = pygame.transform.rotate(self.original_image, -math.degrees(angle))
        self.rect = self.image.get_rect(center=(x, y))

        # Bullet physics using the speed parameter
        self.speed = speed
        self.vel_x = math.cos(angle) * self.speed
        self.vel_y = math.sin(angle) * self.speed

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        
        if self.rect.x < -100 or self.rect.x > 1380 or self.rect.y < -100 or self.rect.y > 820:
            self.kill()

class Spark(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # give each spark a random small size
        size = random.randint(2, 5)
        self.image = pygame.Surface((size, size))
        self.image.fill((255, 200, 0)) # yellow spark to match the bullet
        self.rect = self.image.get_rect(center=(x, y))

        # blast them outward in completely random directions
        self.vel_x = random.uniform(-4, 4)
        self.vel_y = random.uniform(-4, 4)

        # give them a short, random lifespan (10 to 20 frames)
        self.lifespan = random.randint(10, 20)

    def update(self):
        # move the spark
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        
        # add a tiny bit of gravity so the sparks arc downwards naturally
        self.vel_y += 0.2 
        
        # countdown the timer and destroy the spark when it hits zero
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.kill()