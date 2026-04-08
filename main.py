import pygame
import sys
import random
from settings import *
from player import Player, Enemy, FlyingEnemy
from environment import Platform, HealthPack
from weapons import Gun, Bullet, Spark
from leaderboard import Leaderboard

class Game:
    def __init__(self):
        pygame.init()
        
        # Screen and Clock setup
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Untitled Shooting Game")
        self.clock = pygame.time.Clock()
        
        #Game State
        self.state = "main_menu" 
        self.running = True
        self.score = 0
        self.spawn_timer = 0
        self.weapon = "pistol"
        
        # New Weapon Stats System
        self.weapons_data = {
            "pistol": {"ammo": 6, "max_ammo": 6, "cooldown": 0, "fire_rate": 15}, 
            "shotgun": {"ammo": 2, "max_ammo": 2, "cooldown": 0, "fire_rate": 60}, # 1 second cooldown
            "rifle": {"ammo": 30, "max_ammo": 30, "cooldown": 0, "fire_rate": 8}
        }
        self.is_reloading = False
        self.reloading_weapon = None
        self.reload_timer = 0
        self.reload_duration = 120 # 2 seconds at 60 FPS

        # Load Leaderboard from our new file
        self.leaderboard_manager = Leaderboard()

        # Fonts
        self.font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 32)
        self.title_font = pygame.font.SysFont(None, 100) 

        # Pre-rendering static text for speed
        self.title_surf = self.title_font.render("UNTITLED SHOOTING GAME", True, WHITE)
        self.title_rect = self.title_surf.get_rect(center=(SCREEN_WIDTH // 2, 100))

        # --- SOUND SETUP ---
        pygame.mixer.init()
        self.player_hit_sound = None
        self.enemy_hit_sound = None
        
        # Dictionary to hold distinct sounds for each weapon
        self.weapon_sounds = {
            "pistol": {"shoot": None, "reload": None},
            "shotgun": {"shoot": None, "reload": None},
            "rifle": {"shoot": None, "reload": None}
        }

        # --- BACKGROUND MUSIC SETUP ---
        try:
            # Load the streaming music file
            pygame.mixer.music.load("assets/theme.mp3") 
            
            # Set the volume a bit lower so it doesn't overpower your gun sound effects
            pygame.mixer.music.set_volume(0.2) 
            
            # The -1 argument tells Pygame to loop the music infinitely
            pygame.mixer.music.play(-1) 
            
        except Exception as e:
            print("Warning: Could not load background music. Check if 'theme.mp3' is in your assets folder!")

        # --- BACKGROUND IMAGE SETUP ---
        self.bg_image = None
        try:
            # Load the image and convert it for better performance
            raw_bg = pygame.image.load("assets/background.png").convert()
            # Scale it to match the screen size exactly
            self.bg_image = pygame.transform.scale(raw_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception as e:
            print("Warning: Could not load background.png. Make sure it is in your assets folder!")
        
        try:
            self.player_hit_sound = pygame.mixer.Sound("assets/player_hit.wav")
            self.enemy_hit_sound = pygame.mixer.Sound("assets/enemy_hit.wav")
            self.player_hit_sound.set_volume(0.5)
            self.enemy_hit_sound.set_volume(0.4)
            
            # Dynamically load the shoot and reload sounds for each gun
            for w in ["pistol", "shotgun", "rifle"]:
                shoot_sfx = pygame.mixer.Sound(f"assets/{w}_shoot.wav")
                reload_sfx = pygame.mixer.Sound(f"assets/{w}_reload.wav")
                shoot_sfx.set_volume(0.3)
                reload_sfx.set_volume(0.5)
                
                self.weapon_sounds[w]["shoot"] = shoot_sfx
                self.weapon_sounds[w]["reload"] = reload_sfx
                
        except FileNotFoundError:
            print("Warning: Asset files missing. Please ensure you have pistol_shoot.wav, pistol_reload.wav, etc. inside your 'asset' folder.")

        # Player Setup
        self.player_image = pygame.Surface((50, 50))
        self.player_image.fill(GREEN) 
        self.player = Player(PLAYER_START_X, PLAYER_START_Y, self.player_image)

        # Environment Setup
        self.platforms = [
            Platform(0, 680, 1280, 40),  
            Platform(0, 0, 40, 720),     
            Platform(1240, 0, 40, 720),  
            Platform(0, 0, 1280, 40),    
            Platform(200, 560, 200, 20), 
            Platform(880, 560, 200, 20), 
            Platform(540, 450, 200, 20), 
            Platform(200, 340, 200, 20), 
            Platform(880, 340, 200, 20), 
            Platform(540, 230, 200, 20)  
        ]
        
        # Weapon Setup
        self.weapon_images = {}
        for w in ["pistol", "shotgun", "rifle"]:
            try:
                raw_gun_image = pygame.image.load(f"assets/{w}.png").convert_alpha()
                self.weapon_images[w] = pygame.transform.scale(raw_gun_image, (90, 45))
            except Exception as e:
                # Fallback to a grey box if an image is missing so the game doesn't crash
                fallback = pygame.Surface((90, 45))
                fallback.fill((100, 100, 100))
                self.weapon_images[w] = fallback
                print(f"Warning: Could not load {w}.png in assets folder.")

        # Default to pistol on startup
        self.gun = Gun(self.player, self.weapon_images["pistol"])
        
        # Sprite Groups
        self.bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.sparks = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.health_packs = pygame.sprite.Group()

    def reset_game_state(self):
        #"""Clears everything to start a fresh round."""
        self.spawn_timer = 0
        self.player.health = self.player.max_health
        self.score = 0
        self.enemies.empty() 
        self.bullets.empty() 
        self.enemy_bullets.empty() 
        self.health_packs.empty() 
        self.player.rect.x = PLAYER_START_X
        self.player.rect.y = PLAYER_START_Y

        self.is_reloading = False
        self.reloading_weapon = None
        self.reload_timer = 0
        for w in self.weapons_data.values():
            w["ammo"] = w["max_ammo"]
            w["cooldown"] = 0
    
    def play_sound(self, sound):
        if sound:
            sound.play()

    def start_reload(self):
        """Triggers the reload timer and sound."""
        self.is_reloading = True
        self.reloading_weapon = self.weapon 
        self.reload_timer = self.reload_duration
        
        # Play the specific reload sound for the current weapon
        self.play_sound(self.weapon_sounds[self.weapon]["reload"])

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
    
            if event.type == pygame.KEYDOWN:
                # Global Quit Key
                if event.key == pygame.K_q:
                    self.running = False
                # Manual Reload
                if event.key == pygame.K_r and self.state == "playing":
                    stats = self.weapons_data[self.weapon]
                    if not self.is_reloading and stats["ammo"] < stats["max_ammo"]:
                        self.start_reload()

                # State-specific Key Presses
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
                    if event.key == pygame.K_1: 
                        self.weapon = "pistol"
                        self.gun.swap_image(self.weapon_images["pistol"])
                    elif event.key == pygame.K_2: 
                        self.weapon = "shotgun"
                        self.gun.swap_image(self.weapon_images["shotgun"])
                    elif event.key == pygame.K_3: 
                        self.weapon = "rifle"
                        self.gun.swap_image(self.weapon_images["rifle"])
                    elif event.key == pygame.K_m: 
                        self.state = "main_menu"

                elif self.state == "game_over":
                    if event.key == pygame.K_m:
                        self.reset_game_state()
                        self.state = "main_menu"
                
                

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "playing" and event.button == 1:
                    self.fire_weapon()

    def fire_weapon(self):
        """Handles the different firing logic for each gun."""
        if self.is_reloading: 
            return
            
        stats = self.weapons_data[self.weapon]
        if stats["cooldown"] > 0: 
            return

        if stats["ammo"] > 0:
            stats["ammo"] -= 1
            stats["cooldown"] = stats["fire_rate"]
            
            # Play the specific shoot sound for the current weapon
            self.play_sound(self.weapon_sounds[self.weapon]["shoot"])
            
            if self.weapon == "pistol":
                new_bullet = Bullet(self.gun.rect.centerx, self.gun.rect.centery, self.gun.current_angle)
                self.bullets.add(new_bullet)
            elif self.weapon == "shotgun":
                for spread in [-0.2, 0, 0.2]:
                    new_bullet = Bullet(self.gun.rect.centerx, self.gun.rect.centery, self.gun.current_angle + spread)
                    self.bullets.add(new_bullet)
            elif self.weapon == "rifle":
                # Now single clicks will actually spawn a rifle bullet!
                new_bullet = Bullet(self.gun.rect.centerx, self.gun.rect.centery, self.gun.current_angle)
                self.bullets.add(new_bullet)
                    
            # Auto-reload if empty
            if stats["ammo"] <= 0:
                self.start_reload()

    def update(self):
        if self.state == "playing":
            stats = self.weapons_data[self.weapon]

            # Weapon cooldown logic
            if stats["cooldown"] > 0:
                stats["cooldown"] -= 1

            # Reloading logic
            if self.is_reloading:
                self.reload_timer -= 1
                if self.reload_timer <= 0:
                    self.is_reloading = False
                    if self.reloading_weapon:
                        self.weapons_data[self.reloading_weapon]["ammo"] = self.weapons_data[self.reloading_weapon]["max_ammo"]

            # Rifle Automatic Fire (fires while holding mouse)
            elif pygame.mouse.get_pressed()[0] and self.weapon == "rifle" and stats["cooldown"] <= 0:
                if stats["ammo"] > 0:
                    stats["ammo"] -= 1
                    stats["cooldown"] = stats["fire_rate"]
                    
                    # Play the specific rifle shoot sound
                    self.play_sound(self.weapon_sounds["rifle"]["shoot"]) 
                    
                    new_bullet = Bullet(self.gun.rect.centerx, self.gun.rect.centery, self.gun.current_angle)
                    self.bullets.add(new_bullet)
                    
                    if stats["ammo"] <= 0:
                        self.start_reload()
            # Update all sprites
            self.player.update(self.platforms) 
            self.gun.update()
            self.bullets.update()
            self.sparks.update()
            self.enemy_bullets.update()
            
            hits = pygame.sprite.groupcollide(self.bullets, self.platforms, True, False)
            for bullet in hits:
                for _ in range(5): 
                    self.sparks.add(Spark(bullet.rect.centerx, bullet.rect.centery))

            # Enemy Spawning (Randomly choose ground or flying)
            self.spawn_timer += 1
            if self.spawn_timer >= SPAWN_RATE: 
                random_x = random.randint(100, 1100)
                
                # 50% chance to spawn a flying enemy
                if random.choice([True, False]):
                    # Spawn flying enemy higher up in the air
                    random_y = random.randint(50, 300)
                    self.enemies.add(FlyingEnemy(random_x, random_y))
                else:
                    # Spawn normal red enemy near the top to fall down
                    self.enemies.add(Enemy(random_x, 50))
                    
                self.spawn_timer = 0
                
            self.enemies.update(self.platforms, self.player, self.enemy_bullets)
            pygame.sprite.groupcollide(self.enemy_bullets, self.platforms, True, False)

            # Damage and Score logic with Sounds added
            killed = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True)
            if killed:
                self.play_sound(self.enemy_hit_sound) 
                
                # Iterate directly over the keys (the enemies) to eliminate the nested loop
                for enemy in killed:
                    # 10% drop chance (random.random() is faster than randint)
                    if random.random() < 0.10: 
                        self.health_packs.add(HealthPack(enemy.rect.centerx, enemy.rect.centery))

            self.score += len(killed) * 10

            self.health_packs.update(self.platforms)
            collected = pygame.sprite.spritecollide(self.player, self.health_packs, True)
            for pack in collected:
                if self.player.health < self.player.max_health:
                    self.player.health += 1

            if pygame.sprite.spritecollide(self.player, self.enemies, False) or \
               pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
                if not self.player.invincible:
                    self.play_sound(self.player_hit_sound) # Play player hit sound
                self.player.take_damage()
                
            # Game Over Trigger
            if self.player.health <= 0:
                self.leaderboard_manager.add_score(self.score)
                self.state = "game_over"

    def draw(self):
        self.screen.fill(WHITE) 

        if self.state == "main_menu":
            self.screen.fill(DARK_GRAY) 
            self.screen.blit(self.title_surf, self.title_rect)
            
            prompt_text = self.font.render("Press 'P' to Play  |  Press 'S' for Store  |  'Q' to Quit", True, (200, 200, 200))
            self.screen.blit(prompt_text, prompt_text.get_rect(center=(SCREEN_WIDTH // 2, 200))) 

            # Leaderboard Display
            lb_title = self.font.render("LEADERBOARD", True, GOLD)
            self.screen.blit(lb_title, (SCREEN_WIDTH // 2 - 130, 300))
            for i, score in enumerate(self.leaderboard_manager.get_scores()):
                score_text = self.font.render(f"{i+1}. {score}", True, WHITE)
                self.screen.blit(score_text, (SCREEN_WIDTH // 2 - 50, 360 + (i * 45)))
                
        elif self.state == "playing":
            if self.bg_image:
                self.screen.blit(self.bg_image, (0, 0))
            for plat in self.platforms: plat.draw(self.screen)
            self.player.draw(self.screen)
            self.gun.draw(self.screen)
            self.bullets.draw(self.screen)
            self.enemy_bullets.draw(self.screen)
            self.sparks.draw(self.screen)
            self.health_packs.draw(self.screen)
            self.enemies.draw(self.screen) 
            
            # Distinguished Score Section
            ui_bg = pygame.Surface((220, 110))
            ui_bg.fill(UI_BG_COLOR); ui_bg.set_alpha(200)
            self.screen.blit(ui_bg, (10, 10))
            
            self.screen.blit(self.font.render(f"Score: {self.score}", True, GOLD), (20, 20)) 
            self.screen.blit(self.font.render(f"Health: {self.player.health}", True, RED), (20, 70))
            self.screen.blit(self.small_font.render("Press 'M' for Menu", True, (150, 150, 150)), (SCREEN_WIDTH - 220, 20))

            # Ammo Display
            stats = self.weapons_data[self.weapon]
            if self.is_reloading and self.reloading_weapon == self.weapon:
                ammo_text = self.small_font.render("RELOADING...", True, (0, 200, 255))
            else:
                ammo_text = self.font.render(f"Ammo: {stats['ammo']}/{stats['max_ammo']}", True, (0, 200, 255))
            self.screen.blit(ammo_text, (20, 120))

            self.screen.blit(self.small_font.render("Press 'M' for Menu", True, (150, 150, 150)), (SCREEN_WIDTH - 220, 20))
            self.screen.blit(self.small_font.render("Press 'R' to Reload", True, (150, 150, 150)), (SCREEN_WIDTH - 220, 50))

        elif self.state == "gun_store":
            self.screen.fill((50, 50, 60))
            self.screen.blit(self.title_font.render("GUN STORE", True, WHITE), (SCREEN_WIDTH // 2 - 200, 100))
            self.screen.blit(self.font.render(f"Current: {self.weapon.upper()}", True, GREEN), (SCREEN_WIDTH // 2 - 180, 200))
            
            options = ["1: Pistol (Standard)", "2: Shotgun (Spread)", "3: Rifle (Auto)", "M: Back to Menu"]
            for i, opt in enumerate(options):
                color = WHITE if i < 3 else (200, 200, 200)
                self.screen.blit(self.font.render(f"Press {opt}", True, color), (SCREEN_WIDTH // 2 - 180, 300 + (i * 60)))
            
        elif self.state == "game_over":
            self.screen.fill((80, 20, 20)) 
            self.screen.blit(self.title_font.render("GAME OVER", True, WHITE), (SCREEN_WIDTH // 2 - 210, 200))
            self.screen.blit(self.title_font.render(f"Final Score: {self.score}", True, GOLD), (SCREEN_WIDTH // 2 - 240, 350))
            self.screen.blit(self.font.render("Press 'M' to Return to Menu", True, (200, 200, 200)), (SCREEN_WIDTH // 2 - 230, 500))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    my_game = Game()
    my_game.run()