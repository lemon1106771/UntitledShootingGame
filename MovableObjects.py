import pygame
import math
import random
from weapons import Bullet
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT,
                      DASH_SPEED, DASH_DURATION, DASH_COOLDOWN)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect  = self.image.get_rect(topleft=(x, y))

        # Movement
        self.vel_x        = 0
        self.vel_y        = 0
        self.speed        = 7
        self.gravity      = 0.5
        self.jump_strength = -12
        self.is_grounded  = False

        # Dash
        self.dash_timer    = 0   # frames remaining in active dash
        self.dash_cooldown = 0   # frames until next dash allowed
        self.dash_dir      = 0   # -1 left, +1 right

        # Parry
        self.is_parrying   = False
        self.parry_window  = 0
        self.parry_cooldown = 0

        # Health / i-frames
        self.max_health         = 3
        self.health             = self.max_health
        self.invincible         = False
        self.invincibility_timer = 0

    # --- helpers -----------------------------------------------------------
    @property
    def parry_rect(self):
        return self.rect.inflate(60, 60)

    @property
    def is_dashing(self):
        return self.dash_timer > 0

    def take_damage(self):
        if not self.invincible and not self.is_dashing:
            self.health -= 1
            self.invincible = True
            self.invincibility_timer = 60

    # --- per-frame ---------------------------------------------------------
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

    def _try_dash(self, keys):
        """Initiate a dash on Shift if off cooldown."""
        if self.dash_cooldown > 0:
            return
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            # dash in the direction currently held, fallback to facing right
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.dash_dir = -1
            else:
                self.dash_dir = 1
            self.dash_timer    = DASH_DURATION
            self.dash_cooldown = DASH_COOLDOWN
            # grant brief i-frames during dash
            self.invincible = True
            self.invincibility_timer = max(self.invincibility_timer, DASH_DURATION + 2)

    def _try_parry(self, keys):
        if self.parry_cooldown == 0 and (keys[pygame.K_f]):
            self.parry_window  = 12
            self.parry_cooldown = 60

    def update(self, platforms, timescale=1.0):
        keys = pygame.key.get_pressed()

        # --- timers (always tick at real speed so they don't get stuck) ---
        if self.invincible:
            self.invincibility_timer -= 1
            if self.invincibility_timer <= 0:
                self.invincible = False

        if self.dash_timer > 0:
            self.dash_timer -= 1
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        if self.parry_window > 0:
            self.parry_window -= 1
            self.is_parrying = True
        else:
            self.is_parrying = False
        if self.parry_cooldown > 0:
            self.parry_cooldown -= 1

        # --- input --------------------------------------------------------
        self._try_dash(keys)
        self._try_parry(keys)
        self.handle_input()

        # --- horizontal movement (scale by timescale) ---------------------
        if self.is_dashing:
            move_x = self.dash_dir * DASH_SPEED * timescale
        else:
            move_x = self.vel_x * timescale

        self.rect.x += move_x
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if move_x > 0:
                    self.rect.right = plat.rect.left
                elif move_x < 0:
                    self.rect.left  = plat.rect.right

        # --- vertical movement --------------------------------------------
        self.vel_y += self.gravity * timescale
        self.vel_y  = min(self.vel_y, 15)
        self.rect.y += self.vel_y * timescale
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
        if self.invincible and self.invincibility_timer % 10 < 5:
            return
        surface.blit(self.image, self.rect)


# ---------------------------------------------------------------------------
# Enemy (ground)
# ---------------------------------------------------------------------------
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))
        self.rect  = self.image.get_rect(topleft=(x, y))

        self.shoot_timer = 0
        self.shoot_delay = 90

        self.vel_x       = 2
        self.vel_y       = 0
        self.gravity     = 0.5
        self.jump_strength = -10
        self.is_grounded = False

        # Telegraph: turns orange before shooting
        self._base_color    = (255, 0, 0)
        self._warn_color    = (255, 140, 0)
        self._warn_frames   = 20   # frames of orange warning before shot

    def update(self, platforms, player, enemy_bullets, timescale=1.0):
        ts = timescale

        # gravity
        self.vel_y = min(self.vel_y + self.gravity * ts, 15)
        self.rect.y += self.vel_y * ts
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

        # horizontal
        self.rect.x += self.vel_x * ts
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0:
                    self.rect.right = plat.rect.left
                elif self.vel_x < 0:
                    self.rect.left  = plat.rect.right
                self.vel_x *= -1

        # random jump
        if self.is_grounded and random.randint(1, 100) <= 2:
            self.vel_y = self.jump_strength
            self.is_grounded = False

        # shoot with telegraph
        self.shoot_timer += ts
        if self.shoot_timer >= self.shoot_delay:
            self.shoot_timer = 0
            self._fire(player, enemy_bullets)

        # telegraph color
        warn_start = self.shoot_delay - self._warn_frames
        if self.shoot_timer >= warn_start:
            self.image.fill(self._warn_color)
        else:
            self.image.fill(self._base_color)

    def _fire(self, player, enemy_bullets):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        enemy_bullets.add(Bullet(self.rect.centerx, self.rect.centery,
                                 angle, (255, 50, 50), 7))


# ---------------------------------------------------------------------------
# FlyingEnemy
# ---------------------------------------------------------------------------
class FlyingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 255, 0))
        self.rect  = self.image.get_rect(topleft=(x, y))

        self.shoot_timer = 0
        self.shoot_delay = 90

        self.vel_x = random.choice([-2, 2])
        self.vel_y = random.choice([-2, 2])

        self._base_color  = (255, 255, 0)
        self._warn_color  = (255, 180, 0)
        self._warn_frames = 20

    def update(self, platforms, player, enemy_bullets, timescale=1.0):
        ts = timescale

        # horizontal
        self.rect.x += self.vel_x * ts
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                self.rect.right = plat.rect.left if self.vel_x > 0 else self.rect.left
                if self.vel_x > 0:
                    self.rect.right = plat.rect.left
                else:
                    self.rect.left  = plat.rect.right
                self.vel_x *= -1

        if self.rect.left < 0:
            self.rect.left = 0;  self.vel_x *= -1
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH; self.vel_x *= -1

        # vertical
        self.rect.y += self.vel_y * ts
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0:
                    self.rect.bottom = plat.rect.top
                else:
                    self.rect.top = plat.rect.bottom
                self.vel_y *= -1

        if self.rect.top < 0:
            self.rect.top = 0;    self.vel_y *= -1
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT; self.vel_y *= -1

        # shoot with telegraph
        self.shoot_timer += ts
        if self.shoot_timer >= self.shoot_delay:
            self.shoot_timer = 0
            self._fire(player, enemy_bullets)

        warn_start = self.shoot_delay - self._warn_frames
        if self.shoot_timer >= warn_start:
            self.image.fill(self._warn_color)
        else:
            self.image.fill(self._base_color)

    def _fire(self, player, enemy_bullets):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        enemy_bullets.add(Bullet(self.rect.centerx, self.rect.centery,
                                 angle, (255, 255, 0), 7))