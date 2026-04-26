import pygame


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=(115, 150, 140)):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect  = self.image.get_rect(topleft=(x, y))

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill((0, 200, 0))
        pygame.draw.rect(self.image, (255, 255, 255), (8,  4, 4, 12))
        pygame.draw.rect(self.image, (255, 255, 255), (4,  8, 12, 4))
        self.rect    = self.image.get_rect(center=(x, y))
        self.vel_y   = 0
        self.gravity = 0.5
        self.lifespan = 600

    def update(self, platforms):
        self.vel_y = min(self.vel_y + self.gravity, 10)
        self.rect.y += self.vel_y

        for plat in platforms:
            if self.rect.colliderect(plat.rect) and self.vel_y > 0:
                self.rect.bottom = plat.rect.top
                self.vel_y = 0

        self.lifespan -= 1
        if self.lifespan <= 0:
            self.kill()