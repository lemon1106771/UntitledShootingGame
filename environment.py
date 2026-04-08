import pygame
import random

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=(115, 150, 140)):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color) 
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # Create a green box
        self.image = pygame.Surface((20, 20))
        self.image.fill((0, 200, 0)) 
        
        # Draw a white cross on it
        pygame.draw.rect(self.image, (255, 255, 255), (8, 4, 4, 12))
        pygame.draw.rect(self.image, (255, 255, 255), (4, 8, 12, 4))
        
        self.rect = self.image.get_rect(center=(x, y))
        
        self.vel_y = 0
        self.gravity = 0.5
        self.lifespan = 600 # Disappears after 10 seconds (60 frames * 10)

    def update(self, platforms):
        # Apply gravity so it falls to the ground
        self.vel_y += self.gravity
        if self.vel_y > 10:
            self.vel_y = 10
            
        self.rect.y += self.vel_y
        
        # Stop falling if it hits a platform
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0:
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
        
        # Count down lifespan
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.kill()