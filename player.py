import pygame
import math
import random
from weapons import Bullet
from settings import SCREEN_WIDTH, SCREEN_HEIGHT 


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 7
        self.gravity = 0.5
        self.jump_strength = -12
        self.is_grounded = False

        # Health and Invincibility setup
        self.max_health = 3
        self.health = self.max_health
        self.invincible = False
        self.invincibility_timer = 0
        
    def take_damage(self):
        # Only take damage if not currently invincible
        if not self.invincible:
            self.health -= 1
            self.invincible = True
            self.invincibility_timer = 60 # 1 full second of i-frames
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel_x = 0 
        
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vel_x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vel_x = self.speed
            
        if keys[pygame.K_SPACE] and self.is_grounded:
            self.vel_y = self.jump_strength
            self.is_grounded = False

    def apply_gravity(self):
        self.vel_y += self.gravity

    def update(self, platforms):
        # Handle i-frames timer
        if self.invincible:
            self.invincibility_timer -= 1
            if self.invincibility_timer <= 0:
                self.invincible = False

        self.handle_input()
        self.rect.x += self.vel_x
        
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0: 
                    self.rect.right = plat.rect.left
                elif self.vel_x < 0: 
                    self.rect.left = plat.rect.right

        self.apply_gravity()
        if self.vel_y > 15: 
            self.vel_y = 15
            
        self.rect.y += self.vel_y
        self.is_grounded = False
        
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0: 
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.is_grounded = True
                elif self.vel_y < 0: 
                    self.rect.top = plat.rect.bottom
                    self.vel_y = 0

    def draw(self, surface):
        # If invincible, create a flashing effect
        if self.invincible:
            # Only draw the player half the time (flashes every 10 frames)
            if self.invincibility_timer % 10 < 5:
                surface.blit(self.image, self.rect)
        else:
                # Draw normally when not invincible
            surface.blit(self.image, self.rect)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0)) 
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.shoot_timer = 0
        self.shoot_delay = 90 
        
        self.vel_x = 2 
        self.vel_y = 0
        self.gravity = 0.5
        
        # New jumping variables
        self.jump_strength = -10
        self.is_grounded = False

    def update(self, platforms, player, enemy_bullets):
        # 1. Apply gravity
        self.vel_y += self.gravity
        if self.vel_y > 15:
            self.vel_y = 15
            
        # 2. Move vertically and check floor collisions
        self.rect.y += self.vel_y
        self.is_grounded = False # Reset grounded state every frame
        
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0: 
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.is_grounded = True # Enemy is touching the floor
                elif self.vel_y < 0: 
                    self.rect.top = plat.rect.bottom
                    self.vel_y = 0

        # 3. Move horizontally and check wall collisions
        self.rect.x += self.vel_x
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0: 
                    self.rect.right = plat.rect.left
                    self.vel_x *= -1 
                elif self.vel_x < 0: 
                    self.rect.left = plat.rect.right
                    self.vel_x *= -1 

        # 4. Random Jumping Logic
        if self.is_grounded:
            # 2% chance to jump every frame while on the ground
            if random.randint(1, 100) <= 2: 
                self.vel_y = self.jump_strength
                self.is_grounded = False

        # 5. Shooting logic
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_delay:
            self.shoot_timer = 0
            
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            angle_rad = math.atan2(dy, dx)
            
            new_bullet = Bullet(self.rect.centerx, self.rect.centery, angle_rad, (255, 50, 50), 7)
            enemy_bullets.add(new_bullet)

class FlyingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # Create a yellow square for the flying enemy
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 255, 0)) # Yellow color
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.shoot_timer = 0
        self.shoot_delay = 90 
        
        # Flying physics: no gravity, constant diagonal movement
        self.vel_x = random.choice([-2, 2])
        self.vel_y = random.choice([-2, 2])

    def update(self, platforms, player, enemy_bullets):
        # 1. Move horizontally and check platform collisions
        self.rect.x += self.vel_x
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0: 
                    self.rect.right = plat.rect.left
                    self.vel_x *= -1 # Bounce off wall
                elif self.vel_x < 0: 
                    self.rect.left = plat.rect.right
                    self.vel_x *= -1 # Bounce off wall

        # 2. Bounce off screen edges (horizontal)
        if self.rect.left < 0:
            self.rect.left = 0
            self.vel_x *= -1
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.vel_x *= -1

        # 3. Move vertically and check platform collisions
        self.rect.y += self.vel_y
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0: 
                    self.rect.bottom = plat.rect.top
                    self.vel_y *= -1 # Bounce off floor
                elif self.vel_y < 0: 
                    self.rect.top = plat.rect.bottom
                    self.vel_y *= -1 # Bounce off ceiling

        # 4. Bounce off screen edges (vertical)
        if self.rect.top < 0:
            self.rect.top = 0
            self.vel_y *= -1
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.vel_y *= -1

        # 5. Shooting logic
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_delay:
            self.shoot_timer = 0
            
            # Calculate angle to the player
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            angle_rad = math.atan2(dy, dx)
            
            # Spawn a yellow bullet to match the enemy
            new_bullet = Bullet(self.rect.centerx, self.rect.centery, angle_rad, (255, 255, 0), 7)
            enemy_bullets.add(new_bullet)