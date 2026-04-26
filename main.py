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

        # HUD fonts — monospace for that ULTRAKILL terminal feel
        mono = "Courier New"
        self.hud_rank   = pygame.font.SysFont(mono, 46, bold=True)
        self.hud_score  = pygame.font.SysFont(mono, 30, bold=True)
        self.hud_combo  = pygame.font.SysFont(mono, 40, bold=True)
        self.hud_medium = pygame.font.SysFont(mono, 28, bold=True)
        self.hud_small  = pygame.font.SysFont(mono, 18, bold=True)
        self.hud_tiny   = pygame.font.SysFont(mono, 13)

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

    # ------------------------------------------------------------------
    # HUD helpers
    # ------------------------------------------------------------------
    def _hud_panel(self, x, y, w, h, alpha=210):
        """Draw a semi-transparent dark panel with a 1px border."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((*HUD_BG, alpha))
        self.screen.blit(surf, (x, y))
        pygame.draw.rect(self.screen, HUD_BORDER, (x, y, w, h), 1)

    def _hud_label(self, text, x, y, font=None):
        """Tiny spaced-out category label."""
        f = font or self.hud_tiny
        surf = f.render(text.upper(), True, HUD_TEXT_DIM)
        self.screen.blit(surf, (x, y))

    def _hud_bar(self, x, y, w, h, pct, fill_color, bg_color=None):
        """Horizontal bar. pct = 0.0–1.0."""
        bg = bg_color or HUD_DIM
        pygame.draw.rect(self.screen, bg,         (x, y, w, h))
        pygame.draw.rect(self.screen, fill_color, (x, y, max(0, int(w * pct)), h))

    def _get_style_rank(self):
        rank = STYLE_RANKS[0]
        for r in STYLE_RANKS:
            if self.combo >= r[0]:
                rank = r
        return rank  # (min, letter, label, color)

    # ------------------------------------------------------------------
    # _draw_hud  — main entry point
    # ------------------------------------------------------------------
    def _draw_hud(self):
        s = self.screen

        # ── STYLE RANK  (top-left) ─────────────────────────────────────
        rank = self._get_style_rank()
        self._hud_panel(16, 16, 90, 88)
        self._hud_label("style", 26, 22)
        rank_surf = self.hud_rank.render(rank[1], True, rank[3])
        s.blit(rank_surf, (24, 34))
        sub_surf = self.hud_tiny.render(rank[2], True, rank[3])
        s.blit(sub_surf, (26, 88))

        # ── SCORE  (top-center) ────────────────────────────────────────
        score_str = str(self.score).zfill(5)
        score_surf = self.hud_score.render(score_str, True, HUD_AMBER)
        score_rect = score_surf.get_rect(centerx=SCREEN_WIDTH // 2, top=18)
        self._hud_panel(score_rect.x - 12, 14,
                        score_rect.width + 24, score_rect.height + 16)
        self._hud_label("score",
                         score_rect.centerx - 18, 18)
        s.blit(score_surf, (score_rect.x, 30))

        # ── PARRY COOLDOWN  (top-right) ────────────────────────────────
        px = SCREEN_WIDTH - 114
        self._hud_panel(px, 16, 98, 58)
        self._hud_label("parry", px + 10, 22)
        parry_pct = 1.0 - (self.player.parry_cooldown / 60)
        parry_pct = max(0.0, min(1.0, parry_pct))
        if self.player.is_parrying:
            p_color = (0, 220, 255)
            p_text  = "ACTIVE"
        elif parry_pct >= 1.0:
            p_color = HUD_GREEN
            p_text  = "READY"
        else:
            p_color = HUD_GRAY
            p_text  = "CD"
        self._hud_bar(px + 10, 52, 78, 3, parry_pct, p_color)
        p_surf = self.hud_small.render(p_text, True, p_color)
        s.blit(p_surf, (px + 10, 36))

        # ── COMBO  (center-screen, fades in at 2+) ─────────────────────
        if self.combo >= 2:
            combo_alpha = min(255, self.combo * 40 + 120)
            cx = SCREEN_WIDTH // 2
            c_surf = self.hud_combo.render(f"x{self.combo}", True, HUD_RED)
            c_rect = c_surf.get_rect(centerx=cx, top=90)
            # decay bar
            decay_pct = self.combo_timer / COMBO_DECAY_FRAMES
            bar_w = 100
            self._hud_bar(cx - bar_w // 2, c_rect.bottom + 4,
                          bar_w, 3, decay_pct, HUD_RED)
            s.blit(c_surf, c_rect)

        # ── HEALTH  (bottom-left) ──────────────────────────────────────
        hp_max   = self.player.max_health
        hp_cur   = max(0, self.player.health)
        hp_pct   = hp_cur / hp_max if hp_max else 0
        bx, by   = 16, SCREEN_HEIGHT - 88
        bar_w    = 200
        self._hud_panel(bx, by, bar_w + 28, 72)
        self._hud_label("health", bx + 10, by + 8)

        # segmented bar
        seg_w  = (bar_w - (hp_max - 1) * 2) // hp_max
        for i in range(hp_max):
            sx = bx + 10 + i * (seg_w + 2)
            filled = i < hp_cur
            color  = HUD_RED if filled else HUD_DIM
            pygame.draw.rect(s, color, (sx, by + 26, seg_w, 14))
            if filled:   # bright trailing edge
                pygame.draw.rect(s, HUD_WHITE, (sx + seg_w - 2, by + 26, 2, 14))

        hp_num  = self.hud_medium.render(str(hp_cur), True, HUD_RED)
        hp_denom= self.hud_tiny.render(f"/{hp_max}", True, HUD_TEXT_DIM)
        s.blit(hp_num,   (bx + 10, by + 44))
        s.blit(hp_denom, (bx + 10 + hp_num.get_width() + 2, by + 52))

        # ── DASH PIP  (bottom-center) ──────────────────────────────────
        dp_ready = self.player.dash_cooldown == 0
        dp_color = HUD_BLUE if dp_ready else HUD_DIM
        dpx      = SCREEN_WIDTH // 2 - 22
        dpy      = SCREEN_HEIGHT - 52
        self._hud_panel(dpx - 6, dpy - 6, 56, 38)
        pygame.draw.rect(s, dp_color, (dpx, dpy, 44, 10))
        if not dp_ready:
            fill_w = int(44 * (1.0 - self.player.dash_cooldown / DASH_COOLDOWN))
            pygame.draw.rect(s, HUD_BLUE, (dpx, dpy, fill_w, 10))
        self._hud_label("dash", dpx + 4, dpy + 14)

        # ── AMMO  (bottom-right) ───────────────────────────────────────
        stats      = self.weapons_data[self.weapon]
        ammo_cur   = stats["ammo"]
        ammo_max   = stats["max_ammo"]
        w_color, w_border = WEAPON_COLORS[self.weapon]
        pip_w, pip_h, pip_gap = 10, 22, 3
        # clamp pips to 2 rows of 15 max
        display_max = min(ammo_max, 30)
        cols        = min(display_max, 15)
        rows        = (display_max + cols - 1) // cols
        panel_w     = cols * (pip_w + pip_gap) + 20
        panel_h     = rows * (pip_h + pip_gap) + 52
        ax          = SCREEN_WIDTH - panel_w - 16
        ay          = SCREEN_HEIGHT - panel_h - 16
        self._hud_panel(ax, ay, panel_w, panel_h)
        self._hud_label("ammo", ax + 10, ay + 8)

        for i in range(display_max):
            col = i % cols
            row = i // cols
            px2 = ax + 10 + col * (pip_w + pip_gap)
            py2 = ay + 24 + row * (pip_h + pip_gap)
            filled = i < ammo_cur
            fc = w_color  if filled else HUD_DIM
            bc = w_border if filled else HUD_GRAY
            pygame.draw.rect(s, fc,  (px2, py2, pip_w, pip_h))
            pygame.draw.rect(s, bc,  (px2, py2, pip_w, pip_h), 1)

        # ammo number + weapon name
        if self.is_reloading and self.reloading_weapon == self.weapon:
            # blinking RELOAD text
            if pygame.time.get_ticks() % 600 < 300:
                rl = self.hud_small.render("RELOAD", True, w_color)
                s.blit(rl, (ax + 10, ay + panel_h - 36))
        else:
            a_num  = self.hud_medium.render(str(ammo_cur), True, w_color)
            a_den  = self.hud_tiny.render(f"/{ammo_max}", True, HUD_TEXT_DIM)
            s.blit(a_num,  (ax + 10, ay + panel_h - 42))
            s.blit(a_den,  (ax + 10 + a_num.get_width() + 2, ay + panel_h - 34))
        wpn_surf = self.hud_tiny.render(self.weapon.upper(), True, HUD_TEXT_DIM)
        s.blit(wpn_surf, (ax + 10, ay + panel_h - 16))

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