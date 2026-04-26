import pygame
import sys
import random
from settings import *
from MovableObjects import Player, Enemy, FlyingEnemy
from environment import Platform, HealthPack
from weapons import Gun, Bullet, Spark
from leaderboard import Leaderboard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_sound(path, volume=0.5):
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(volume)
        return s
    except Exception:
        return None

def _load_image(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size) if size else img
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Untitled Shooting Game")
        self.clock  = pygame.time.Clock()

        # ---- state -------------------------------------------------------
        self.state   = "main_menu"
        self.running = True
        self.score   = 0

        # ---- slow-mo / hitStop ------------------------------------------
        self.slowmo_timer = 0   # frames remaining; 0 = normal speed

        # ---- combo -------------------------------------------------------
        self.combo        = 0
        self.combo_timer  = 0   # countdown; resets on each kill

        # ---- screen shake ------------------------------------------------
        self.shake_timer  = 0
        self.shake_mag    = 0

        # ---- weapon ------------------------------------------------------
        self.weapon       = "pistol"
        self.weapons_data = {
            "pistol":  {"ammo": 6,  "max_ammo": 6,  "cooldown": 0, "fire_rate": 15},
            "shotgun": {"ammo": 2,  "max_ammo": 2,  "cooldown": 0, "fire_rate": 30},
            "rifle":   {"ammo": 30, "max_ammo": 30, "cooldown": 0, "fire_rate": 8},
        }
        self.is_reloading     = False
        self.reloading_weapon = None
        self.reload_timer     = 0
        self.reload_duration  = 120
        self.spawn_timer      = 0

        # ---- fonts -------------------------------------------------------
        self.font       = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 32)
        self.title_font = pygame.font.SysFont(None, 100)

        # ---- leaderboard -------------------------------------------------
        self.leaderboard_manager = Leaderboard()

        # ---- assets ------------------------------------------------------
        self._load_assets()

        # ---- world -------------------------------------------------------
        self._build_world()

    # ------------------------------------------------------------------
    def _load_assets(self):
        # Background music
        try:
            pygame.mixer.music.load("assets/theme.mp3")
            pygame.mixer.music.set_volume(0.2)
            pygame.mixer.music.play(-1)
        except Exception:
            print("Warning: Could not load background music.")

        self.bg_image = _load_image("assets/background.png")
        if self.bg_image:
            self.bg_image = pygame.transform.scale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        self.player_hit_sound = _load_sound("assets/player_hit.wav", 0.5)
        self.enemy_hit_sound  = _load_sound("assets/enemy_hit.wav",  0.4)

        self.weapon_sounds = {}
        for w in ("pistol", "shotgun", "rifle"):
            self.weapon_sounds[w] = {
                "shoot":  _load_sound(f"assets/{w}_shoot.wav",  0.3),
                "reload": _load_sound(f"assets/{w}_reload.wav", 0.5),
            }

        # Weapon images
        self.weapon_images = {}
        for w in ("pistol", "shotgun", "rifle"):
            img = _load_image(f"assets/{w}.png", (90, 45))
            if img is None:
                img = pygame.Surface((90, 45))
                img.fill((100, 100, 100))
            self.weapon_images[w] = img

    def _build_world(self):
        player_img = pygame.Surface((50, 50))
        player_img.fill(GREEN)
        self.player = Player(PLAYER_START_X, PLAYER_START_Y, player_img)
        self.gun    = Gun(self.player, self.weapon_images["pistol"])

        self.platforms = [
            Platform(0,    680, 1280,  40),  # floor
            Platform(0,      0,   40, 720),  # left wall
            Platform(1240,   0,   40, 720),  # right wall
            Platform(0,      0, 1280,  40),  # ceiling
            Platform(200,  560,  200,  20),
            Platform(880,  560,  200,  20),
            Platform(540,  450,  200,  20),
            Platform(200,  340,  200,  20),
            Platform(880,  340,  200,  20),
            Platform(540,  230,  200,  20),
        ]

        self.bullets      = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.sparks       = pygame.sprite.Group()
        self.enemies      = pygame.sprite.Group()
        self.health_packs = pygame.sprite.Group()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _play(self, sound):
        if sound:
            sound.play()

    def _shake(self, magnitude=6, duration=8):
        self.shake_timer = duration
        self.shake_mag   = magnitude

    def _start_slowmo(self):
        self.slowmo_timer = SLOWMO_DURATION

    @property
    def timescale(self):
        return SLOWMO_TIMESCALE if self.slowmo_timer > 0 else 1.0

    def _register_kill(self):
        """Call once per enemy killed. Updates combo + score."""
        self.combo       += 1
        self.combo_timer  = COMBO_DECAY_FRAMES
        points = 10 * self.combo   # multiplied score!
        self.score += points
        return points

    def _tick_combo(self):
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0:
                self.combo = 0

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset_game_state(self):
        self.score        = 0
        self.combo        = 0
        self.combo_timer  = 0
        self.spawn_timer  = 0
        self.slowmo_timer = 0
        self.shake_timer  = 0
        self.is_reloading = False
        self.reloading_weapon = None
        self.reload_timer = 0

        for w in self.weapons_data.values():
            w["ammo"]     = w["max_ammo"]
            w["cooldown"] = 0

        self.player.rect.topleft = (PLAYER_START_X, PLAYER_START_Y)
        self.player.health       = self.player.max_health
        self.player.vel_x = self.player.vel_y = 0
        self.player.invincible   = False

        for grp in (self.enemies, self.bullets, self.enemy_bullets,
                    self.health_packs, self.sparks):
            grp.empty()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.running = False

                if event.key == pygame.K_r and self.state == "playing":
                    stats = self.weapons_data[self.weapon]
                    if not self.is_reloading and stats["ammo"] < stats["max_ammo"]:
                        self._start_reload()

                if self.state == "main_menu":
                    if event.key == pygame.K_p:
                        self.state = "playing"
                    elif event.key == pygame.K_s:
                        self.state = "gun_store"

                elif self.state == "playing":
                    if event.key == pygame.K_m:
                        self.reset_game_state()
                        self.state = "main_menu"

                elif self.state == "gun_store":
                    weapon_keys = {pygame.K_1: "pistol",
                                   pygame.K_2: "shotgun",
                                   pygame.K_3: "rifle"}
                    if event.key in weapon_keys:
                        self.weapon = weapon_keys[event.key]
                        self.gun.swap_image(self.weapon_images[self.weapon])
                    elif event.key == pygame.K_m:
                        self.state = "main_menu"

                elif self.state == "game_over":
                    if event.key == pygame.K_m:
                        self.reset_game_state()
                        self.state = "main_menu"

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "playing" and event.button == 1:
                    self._fire_weapon()

    # ------------------------------------------------------------------
    # Weapon helpers
    # ------------------------------------------------------------------
    def _start_reload(self):
        self.is_reloading     = True
        self.reloading_weapon = self.weapon
        self.reload_timer     = self.reload_duration
        self._play(self.weapon_sounds[self.weapon]["reload"])

    def _fire_weapon(self):
        if self.is_reloading:
            return
        stats = self.weapons_data[self.weapon]
        if stats["cooldown"] > 0 or stats["ammo"] <= 0:
            if stats["ammo"] <= 0:
                self._start_reload()
            return

        stats["ammo"]    -= 1
        stats["cooldown"] = stats["fire_rate"]
        self._play(self.weapon_sounds[self.weapon]["shoot"])

        cx, cy = self.gun.rect.centerx, self.gun.rect.centery
        angle  = self.gun.current_angle

        if self.weapon == "shotgun":
            for spread in (-0.2, 0.0, 0.2):
                self.bullets.add(Bullet(cx, cy, angle + spread))
        else:
            self.bullets.add(Bullet(cx, cy, angle))

        if stats["ammo"] <= 0:
            self._start_reload()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self):
        if self.state != "playing":
            return

        ts = self.timescale

        # --- slow-mo countdown (real-time, not scaled) ------------------
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1

        # --- shake countdown --------------------------------------------
        if self.shake_timer > 0:
            self.shake_timer -= 1

        # --- combo decay ------------------------------------------------
        self._tick_combo()

        # --- weapon cooldowns / reload (real-time) ----------------------
        stats = self.weapons_data[self.weapon]
        if stats["cooldown"] > 0:
            stats["cooldown"] -= 1

        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.is_reloading = False
                if self.reloading_weapon:
                    self.weapons_data[self.reloading_weapon]["ammo"] = \
                        self.weapons_data[self.reloading_weapon]["max_ammo"]

        # rifle auto-fire
        if (pygame.mouse.get_pressed()[0] and self.weapon == "rifle"
                and stats["cooldown"] <= 0 and not self.is_reloading):
            self._fire_weapon()

        # --- player & gun -----------------------------------------------
        self.player.update(self.platforms, ts)
        self.gun.update()

        # --- bullets & sparks (scaled) ----------------------------------
        for b in self.bullets:
            b.update(ts)
        for b in self.enemy_bullets:
            b.update(ts)
        for sp in self.sparks:
            sp.update(ts)

        # --- bullet-vs-platform sparks ----------------------------------
        hits = pygame.sprite.groupcollide(self.bullets, self.platforms, True, False)
        for bullet_pos in hits:
            for _ in range(5):
                self.sparks.add(Spark(bullet_pos.rect.centerx,
                                      bullet_pos.rect.centery))

        # --- enemy spawning ---------------------------------------------
        self.spawn_timer += 1
        if self.spawn_timer >= SPAWN_RATE:
            self.spawn_timer = 0
            rx = random.randint(100, 1100)
            if random.choice((True, False)):
                self.enemies.add(FlyingEnemy(rx, random.randint(50, 300)))
            else:
                self.enemies.add(Enemy(rx, 50))

        self.enemies.update(self.platforms, self.player, self.enemy_bullets, ts)
        pygame.sprite.groupcollide(self.enemy_bullets, self.platforms, True, False)

        # --- kill enemies -----------------------------------------------
        killed = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True)
        if killed:
            self._play(self.enemy_hit_sound)
            self._shake(6, 8)
            for enemy in killed:
                self._register_kill()
                # big death sparks
                for _ in range(8):
                    self.sparks.add(Spark(enemy.rect.centerx, enemy.rect.centery,
                                          color=(255, 80, 0),
                                          size_range=(4, 9), speed=5))
                if random.random() < 0.10:
                    self.health_packs.add(HealthPack(enemy.rect.centerx,
                                                     enemy.rect.centery))

        # --- health packs -----------------------------------------------
        self.health_packs.update(self.platforms)
        for pack in pygame.sprite.spritecollide(self.player, self.health_packs, True):
            if self.player.health < self.player.max_health:
                self.player.health += 1

        # --- PARRY ------------------------------------------------------
        if self.player.is_parrying:
            parried = pygame.sprite.spritecollide(
                self.player, self.enemy_bullets, True,
                collided=lambda p, b: p.parry_rect.colliderect(b.rect))
            if parried:
                self._start_slowmo()
                self._shake(4, 6)
                for _ in parried:
                    if self.player.health < self.player.max_health:
                        self.player.health += 1
                    self.weapons_data[self.weapon]["ammo"] = \
                        self.weapons_data[self.weapon]["max_ammo"]
                    # reflect bullet toward cursor
                    reflect = Bullet(self.player.rect.centerx,
                                     self.player.rect.centery,
                                     self.gun.current_angle,
                                     color=(0, 220, 255), speed=25)
                    self.bullets.add(reflect)

        # --- player damage ----------------------------------------------
        bullet_hits = pygame.sprite.spritecollide(self.player, self.enemy_bullets, True)
        enemy_hits  = pygame.sprite.spritecollide(self.player, self.enemies, False)

        if (bullet_hits or enemy_hits) and not self.player.invincible:
            self._play(self.player_hit_sound)
            self._shake(10, 12)
            self.player.take_damage()

        # --- game over --------------------------------------------------
        if self.player.health <= 0:
            self.leaderboard_manager.add_score(self.score)
            self.state = "game_over"

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self):
        # shake offset
        ox = oy = 0
        if self.shake_timer > 0:
            ox = random.randint(-self.shake_mag, self.shake_mag)
            oy = random.randint(-self.shake_mag, self.shake_mag)

        self.screen.fill(WHITE)

        if self.state == "main_menu":
            self._draw_main_menu()

        elif self.state == "playing":
            self._draw_playing(ox, oy)

        elif self.state == "gun_store":
            self._draw_gun_store()

        elif self.state == "game_over":
            self._draw_game_over()

        pygame.display.flip()

    # ---- sub-draw methods ------------------------------------------------
    def _draw_main_menu(self):
        self.screen.fill(DARK_GRAY)
        title = self.title_font.render("UNTITLED SHOOTING GAME", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

        prompt = self.font.render(
            "Press 'P' to Play  |  Press 'S' for Store  |  'Q' to Quit",
            True, (200, 200, 200))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 200)))

        lb_title = self.font.render("LEADERBOARD", True, GOLD)
        self.screen.blit(lb_title, (SCREEN_WIDTH // 2 - 130, 300))
        for i, s in enumerate(self.leaderboard_manager.get_scores()):
            surf = self.font.render(f"{i+1}. {s}", True, WHITE)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - 50, 360 + i * 45))

    def _draw_playing(self, ox, oy):
        # background
        if self.bg_image:
            self.screen.blit(self.bg_image, (ox, oy))
        else:
            self.screen.fill(DARK_GRAY)

        for plat in self.platforms:
            plat.draw(self.screen)

        self.player.draw(self.screen)

        # parry aura
        if self.player.is_parrying:
            pygame.draw.rect(self.screen, CYAN,
                             self.player.parry_rect.move(ox, oy), 3, border_radius=10)

        self.gun.draw(self.screen)
        self.bullets.draw(self.screen)
        self.enemy_bullets.draw(self.screen)
        self.sparks.draw(self.screen)
        self.health_packs.draw(self.screen)
        self.enemies.draw(self.screen)

        # slow-mo vignette (subtle blue tint)
        if self.slowmo_timer > 0:
            vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha    = int(60 * (self.slowmo_timer / SLOWMO_DURATION))
            vignette.fill((0, 100, 200, alpha))
            self.screen.blit(vignette, (0, 0))

        self._draw_hud()

    def _draw_hud(self):
        # semi-transparent panel
        panel = pygame.Surface((240, 145))
        panel.fill(UI_BG_COLOR)
        panel.set_alpha(200)
        self.screen.blit(panel, (10, 10))

        self.screen.blit(self.font.render(f"Score: {self.score}", True, GOLD), (20, 20))
        self.screen.blit(self.font.render(f"Health: {self.player.health}", True, RED),  (20, 68))

        stats = self.weapons_data[self.weapon]
        if self.is_reloading and self.reloading_weapon == self.weapon:
            ammo_surf = self.small_font.render("RELOADING...", True, CYAN)
        else:
            ammo_surf = self.font.render(
                f"Ammo: {stats['ammo']}/{stats['max_ammo']}", True, CYAN)
        self.screen.blit(ammo_surf, (20, 116))

        # combo
        if self.combo >= 2:
            combo_color = GOLD if self.combo < 5 else ORANGE
            combo_surf  = self.font.render(f"x{self.combo} COMBO!", True, combo_color)
            self.screen.blit(combo_surf, combo_surf.get_rect(
                center=(SCREEN_WIDTH // 2, 40)))

        # dash indicator
        if self.player.dash_cooldown > 0:
            pct  = 1.0 - self.player.dash_cooldown / DASH_COOLDOWN
            bar_w = int(100 * pct)
            pygame.draw.rect(self.screen, (60, 60, 80),   (20, 160, 100, 10))
            pygame.draw.rect(self.screen, (80, 180, 255), (20, 160, bar_w, 10))
            label = self.small_font.render("DASH", True, (150, 150, 200))
            self.screen.blit(label, (125, 157))

        # hints
        self.screen.blit(
            self.small_font.render("M: Menu  R: Reload  Shift: Dash  F: Parry",
                                   True, (150, 150, 150)),
            (SCREEN_WIDTH - 420, 20))

    def _draw_gun_store(self):
        self.screen.fill((50, 50, 60))
        title = self.title_font.render("GUN STORE", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))
        cur   = self.font.render(f"Current: {self.weapon.upper()}", True, GREEN)
        self.screen.blit(cur, cur.get_rect(center=(SCREEN_WIDTH // 2, 200)))

        for i, line in enumerate(("1: Pistol  (6 shots, reliable)",
                                   "2: Shotgun (2 shots, spread)",
                                   "3: Rifle   (30 shots, auto)",
                                   "M: Back to Menu")):
            color = WHITE if i < 3 else (180, 180, 180)
            surf  = self.font.render(f"Press {line}", True, color)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2,
                                                          300 + i * 60)))

    def _draw_game_over(self):
        self.screen.fill((80, 20, 20))
        go   = self.title_font.render("GAME OVER", True, WHITE)
        scr  = self.title_font.render(f"Final Score: {self.score}", True, GOLD)
        hint = self.font.render("Press 'M' to Return to Menu", True, (200, 200, 200))
        self.screen.blit(go,   go.get_rect(center=(SCREEN_WIDTH // 2, 200)))
        self.screen.blit(scr,  scr.get_rect(center=(SCREEN_WIDTH // 2, 350)))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 500)))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()