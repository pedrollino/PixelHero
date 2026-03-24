import pygame
import sys
import random
import math

# ── Inicialização ──────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 500
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PixelHero – Demo")
clock = pygame.time.Clock()

# ── Paleta de cores pixel art ──────────────────────────────────────────────────
SKY_TOP    = (20,  12,  60)
SKY_BOT    = (60,  30, 100)
GROUND_COL = (80,  50,  20)
GRASS_COL  = (34, 139,  34)
PLAT_COL   = (100, 65,  30)
PLAT_TOP   = (60, 179,  60)
PLAYER_COL = (220, 180,  50)   # corpo amarelo
PLAYER_EYE = (10,  10,  10)
PLAYER_SHOE= (40,  40, 140)
ENEMY_COL  = (200,  40,  40)
ENEMY_EYE  = (255, 255,  50)
COIN_COL   = (255, 215,   0)
STAR_COL   = (255, 255, 200)
HUD_COL    = (255, 255, 255)
SHADOW_COL = (0,   0,   0, 120)
RED        = (220,  40,  40)
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
YELLOW     = (255, 215,   0)
DARK_PANEL = (10,   5,  30, 200)

# ── Fontes pixel ───────────────────────────────────────────────────────────────
font_big   = pygame.font.SysFont("Courier", 48, bold=True)
font_med   = pygame.font.SysFont("Courier", 28, bold=True)
font_small = pygame.font.SysFont("Courier", 18, bold=True)

# ── Sons sintéticos (sem arquivos externos) ────────────────────────────────────
def make_sound(freq=440, duration=0.08, volume=0.3, wave="square"):
    sample_rate = 22050
    n = int(sample_rate * duration)
    buf = bytearray(n * 2)
    for i in range(n):
        t = i / sample_rate
        if wave == "square":
            val = 1 if math.sin(2 * math.pi * freq * t) > 0 else -1
        else:
            val = math.sin(2 * math.pi * freq * t)
        s = int(val * 32767 * volume)
        s = max(-32768, min(32767, s))
        buf[i*2]     = s & 0xFF
        buf[i*2 + 1] = (s >> 8) & 0xFF
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound

snd_jump  = make_sound(380, 0.12, 0.25, "square")
snd_coin  = make_sound(880, 0.10, 0.20, "sine")
snd_hit   = make_sound(120, 0.18, 0.30, "square")
snd_dead  = make_sound(100, 0.35, 0.25, "square")

# ══════════════════════════════════════════════════════════════════════════════
# CÂMERA
# ══════════════════════════════════════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.offset_x = 0

    def update(self, player):
        target = player.rect.centerx - WIDTH // 3
        self.offset_x += (target - self.offset_x) * 0.12

    def apply(self, rect):
        return rect.move(-int(self.offset_x), 0)

# ══════════════════════════════════════════════════════════════════════════════
# PARTÍCULAS
# ══════════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -1)
        self.life = random.randint(18, 35)
        self.max_life = self.life
        self.color = color
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.25
        self.life -= 1

    def draw(self, surface, cam_offset):
        alpha = int(255 * self.life / self.max_life)
        c = (*self.color[:3], alpha)
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.rect(s, c, (0, 0, self.size*2, self.size*2))
        surface.blit(s, (self.x - cam_offset - self.size, self.y - self.size))

    @property
    def dead(self):
        return self.life <= 0

# ══════════════════════════════════════════════════════════════════════════════
# JOGADOR
# ══════════════════════════════════════════════════════════════════════════════
class Player:
    W, H = 28, 36

    def __init__(self, x, y):
        self.rect   = pygame.Rect(x, y, self.W, self.H)
        self.vx     = 0.0
        self.vy     = 0.0
        self.on_ground = False
        self.facing = 1        # 1 = direita, -1 = esquerda
        self.anim_t = 0
        self.invincible = 0    # frames de invencibilidade após levar dano
        self.alive  = True

    # ── física ────────────────────────────────────────────────────────────────
    def update(self, platforms, particles):
        keys = pygame.key.get_pressed()
        speed = 4.0

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vx = -speed
            self.facing = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = speed
            self.facing = 1
        else:
            self.vx *= 0.75

        self.vy += 0.55   # gravidade
        if self.vy > 18:
            self.vy = 18

        # movimento horizontal
        self.rect.x += int(self.vx)
        self._collide_h(platforms)

        # movimento vertical
        self.rect.y += int(self.vy)
        self.on_ground = False
        self._collide_v(platforms)

        # animação
        if abs(self.vx) > 0.5 and self.on_ground:
            self.anim_t += 1
        elif not self.on_ground:
            self.anim_t += 0.5

        # invencibilidade
        if self.invincible > 0:
            self.invincible -= 1

        # morte por queda
        if self.rect.top > HEIGHT + 100:
            self.alive = False

    def _collide_h(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vx > 0:
                    self.rect.right = p.rect.left
                elif self.vx < 0:
                    self.rect.left = p.rect.right
                self.vx = 0

    def _collide_v(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                self.vy = 0

    def jump(self):
        if self.on_ground:
            self.vy = -13
            snd_jump.play()

    def hit(self, particles):
        if self.invincible > 0:
            return False
        self.invincible = 90
        snd_hit.play()
        for _ in range(12):
            particles.append(Particle(self.rect.centerx, self.rect.centery, RED))
        return True

    # ── desenho pixel art ─────────────────────────────────────────────────────
    def draw(self, surface, cam):
        if self.invincible > 0 and (self.invincible // 6) % 2 == 0:
            return   # pisca durante invencibilidade

        r = cam.apply(self.rect)
        cx, cy = r.centerx, r.centery
        leg_off = int(math.sin(self.anim_t * 0.4) * 5)

        # sombra
        sh = pygame.Surface((self.W + 4, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 80), sh.get_rect())
        surface.blit(sh, (r.left - 2, r.bottom - 4))

        # pernas (pixel blocks)
        leg_col = PLAYER_SHOE
        pygame.draw.rect(surface, leg_col, (cx - 12, r.bottom - 10, 10, 10))
        pygame.draw.rect(surface, leg_col, (cx + 2,  r.bottom - 10 + leg_off, 10, 10))

        # corpo
        pygame.draw.rect(surface, PLAYER_COL, (r.left, r.top + 10, self.W, self.H - 14))

        # cabeça
        hx = r.left + (4 if self.facing == 1 else 0)
        pygame.draw.rect(surface, PLAYER_COL, (hx, r.top, 24, 18))

        # olho
        ex = hx + (14 if self.facing == 1 else 4)
        pygame.draw.rect(surface, PLAYER_EYE, (ex, r.top + 5, 5, 5))

        # braço
        arm_y = r.top + 18
        arm_x = cx + (10 if self.facing == 1 else -14)
        arm_swing = int(math.sin(self.anim_t * 0.4) * 4)
        pygame.draw.rect(surface, PLAYER_COL, (arm_x, arm_y + arm_swing, 8, 12))

# ══════════════════════════════════════════════════════════════════════════════
# PLATAFORMA
# ══════════════════════════════════════════════════════════════════════════════
class Platform:
    def __init__(self, x, y, w, h=18):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surface, cam):
        r = cam.apply(self.rect)
        if r.right < -10 or r.left > WIDTH + 10:
            return
        # corpo marrom
        pygame.draw.rect(surface, PLAT_COL, r)
        # topo verde (grama pixel)
        top_r = pygame.Rect(r.left, r.top, r.width, 6)
        pygame.draw.rect(surface, PLAT_TOP, top_r)
        # detalhe pixel
        for bx in range(r.left, r.right, 18):
            pygame.draw.rect(surface, (50, 30, 10), (bx, r.top + 6, 9, 4))

# ══════════════════════════════════════════════════════════════════════════════
# INIMIGO
# ══════════════════════════════════════════════════════════════════════════════
class Enemy:
    W, H = 26, 26

    def __init__(self, x, y, plat):
        self.rect  = pygame.Rect(x, y - self.H, self.W, self.H)
        self.plat  = plat
        self.vx    = 1.5
        self.vy    = 0.0
        self.anim_t = 0
        self.alive = True

    def update(self, platforms):
        self.vy += 0.55
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)

        # colisão vertical
        for p in platforms:
            if self.rect.colliderect(p.rect) and self.vy >= 0:
                self.rect.bottom = p.rect.top
                self.vy = 0

        # reverte na borda da plataforma
        if self.rect.right > self.plat.rect.right or self.rect.left < self.plat.rect.left:
            self.vx *= -1

        self.anim_t += 1

    def draw(self, surface, cam):
        r = cam.apply(self.rect)
        if r.right < -10 or r.left > WIDTH + 10:
            return

        bob = int(math.sin(self.anim_t * 0.15) * 2)

        # corpo
        pygame.draw.rect(surface, ENEMY_COL, (r.left, r.top + bob, self.W, self.H))

        # olhos
        pygame.draw.rect(surface, ENEMY_EYE, (r.left + 4,  r.top + 6 + bob, 6, 6))
        pygame.draw.rect(surface, ENEMY_EYE, (r.left + 16, r.top + 6 + bob, 6, 6))

        # sobrancelhas raivosas
        pygame.draw.line(surface, BLACK,
                         (r.left + 3, r.top + 4 + bob),
                         (r.left + 10, r.top + 7 + bob), 2)
        pygame.draw.line(surface, BLACK,
                         (r.left + 15, r.top + 7 + bob),
                         (r.left + 22, r.top + 4 + bob), 2)

        # pernas
        loff = int(math.sin(self.anim_t * 0.3) * 4)
        pygame.draw.rect(surface, (140, 20, 20), (r.left + 4,  r.bottom,     8, 6 + loff))
        pygame.draw.rect(surface, (140, 20, 20), (r.left + 14, r.bottom,     8, 6 - loff))

# ══════════════════════════════════════════════════════════════════════════════
# MOEDA
# ══════════════════════════════════════════════════════════════════════════════
class Coin:
    def __init__(self, x, y):
        self.rect   = pygame.Rect(x, y, 16, 16)
        self.collected = False
        self.t      = random.uniform(0, math.pi * 2)

    def update(self):
        self.t += 0.08

    def draw(self, surface, cam):
        bob = int(math.sin(self.t) * 3)
        r = cam.apply(self.rect)
        if r.right < -10 or r.left > WIDTH + 10:
            return
        cx, cy = r.centerx, r.centery + bob
        # estrela de 4 pontas
        pygame.draw.circle(surface, COIN_COL, (cx, cy), 8)
        pygame.draw.circle(surface, (255, 255, 180), (cx - 2, cy - 2), 3)

# ══════════════════════════════════════════════════════════════════════════════
# GERADOR DE NÍVEL
# ══════════════════════════════════════════════════════════════════════════════
def generate_level():
    platforms = []
    enemies   = []
    coins     = []

    # chão base
    ground = Platform(-200, HEIGHT - 40, 3000, 40)
    platforms.append(ground)

    x = 200
    for i in range(18):
        w = random.randint(100, 220)
        y = random.randint(HEIGHT - 220, HEIGHT - 100)
        p = Platform(x, y, w)
        platforms.append(p)

        # inimigo
        if random.random() < 0.5:
            ex = x + random.randint(10, max(11, w - 30))
            enemies.append(Enemy(ex, y, p))

        # moedas
        num_coins = random.randint(1, 3)
        for _ in range(num_coins):
            cx = x + random.randint(10, max(11, w - 10))
            coins.append(Coin(cx, y - 30))

        x += w + random.randint(60, 160)

    # flag final
    flag_x = x + 40
    return platforms, enemies, coins, flag_x

# ══════════════════════════════════════════════════════════════════════════════
# ESTRELAS (fundo)
# ══════════════════════════════════════════════════════════════════════════════
stars = [(random.randint(0, WIDTH*4), random.randint(0, HEIGHT//2),
          random.randint(1, 3)) for _ in range(120)]

def draw_background(surface, cam_offset):
    # gradiente fake
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
        g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
        b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

    # estrelas com parallax suave
    for sx, sy, sz in stars:
        px = (sx - cam_offset * 0.08) % (WIDTH * 4)
        if 0 <= px < WIDTH:
            bright = 150 + sz * 30
            pygame.draw.rect(surface, (bright, bright, bright), (int(px), sy, sz, sz))

# ══════════════════════════════════════════════════════════════════════════════
# HUD
# ══════════════════════════════════════════════════════════════════════════════
def draw_hud(surface, score, lives, coins_left):
    # painel semi-transparente
    panel = pygame.Surface((260, 38), pygame.SRCALPHA)
    panel.fill((10, 5, 30, 180))
    surface.blit(panel, (6, 6))

    lives_surf  = font_small.render(f"♥ {lives}   ★ {score}   ¢ {coins_left}", True, WHITE)
    surface.blit(lives_surf, (14, 14))

# ══════════════════════════════════════════════════════════════════════════════
# TELA DE MENU
# ══════════════════════════════════════════════════════════════════════════════
def draw_menu(surface, tick):
    draw_background(surface, tick * 0.3)

    # título com sombra
    title = font_big.render("PIXEL  HERO", True, YELLOW)
    shadow = font_big.render("PIXEL  HERO", True, BLACK)
    tx = WIDTH // 2 - title.get_width() // 2
    surface.blit(shadow, (tx + 3, 103))
    surface.blit(title,  (tx,     100))

    sub = font_med.render("– DEMO –", True, WHITE)
    surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 160))

    # caixa de controles
    ctrl_box = pygame.Surface((320, 130), pygame.SRCALPHA)
    ctrl_box.fill((10, 5, 40, 200))
    surface.blit(ctrl_box, (WIDTH // 2 - 160, 210))

    controls = [
        "CONTROLES:",
        "← → / A D   –  Mover",
        "SPACE / W   –  Pular",
        "Pise no inimigo –  Eliminar",
    ]
    for i, line in enumerate(controls):
        col = YELLOW if i == 0 else WHITE
        s = font_small.render(line, True, col)
        surface.blit(s, (WIDTH // 2 - s.get_width() // 2, 218 + i * 26))

    # botão pisca
    if (tick // 30) % 2 == 0:
        btn = font_med.render("[ ENTER ] para jogar", True, YELLOW)
        surface.blit(btn, (WIDTH // 2 - btn.get_width() // 2, 360))

    # personagem animado no menu
    px = WIDTH // 2
    py = 450
    leg = int(math.sin(tick * 0.15) * 6)
    pygame.draw.rect(surface, PLAYER_SHOE, (px - 12, py + 20, 10, 10))
    pygame.draw.rect(surface, PLAYER_SHOE, (px + 2,  py + 20 + leg, 10, 10))
    pygame.draw.rect(surface, PLAYER_COL, (px - 14, py, 28, 22))
    pygame.draw.rect(surface, PLAYER_COL, (px - 10, py - 14, 24, 16))
    pygame.draw.rect(surface, PLAYER_EYE, (px + 6,  py - 9, 5, 5))

# ══════════════════════════════════════════════════════════════════════════════
# TELA DE GAME OVER / WIN
# ══════════════════════════════════════════════════════════════════════════════
def draw_overlay(surface, text, sub, score):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 160))
    surface.blit(ov, (0, 0))

    t  = font_big.render(text, True, YELLOW)
    s  = font_med.render(sub,  True, WHITE)
    sc = font_med.render(f"Pontos: {score}", True, YELLOW)
    r  = font_small.render("[ ENTER ] Jogar novamente   [ ESC ] Menu", True, WHITE)

    surface.blit(t,  (WIDTH//2 - t.get_width()//2,  160))
    surface.blit(s,  (WIDTH//2 - s.get_width()//2,  230))
    surface.blit(sc, (WIDTH//2 - sc.get_width()//2, 275))
    surface.blit(r,  (WIDTH//2 - r.get_width()//2,  340))

# ══════════════════════════════════════════════════════════════════════════════
# LOOP PRINCIPAL DO JOGO
# ══════════════════════════════════════════════════════════════════════════════
def run_game():
    platforms, enemies, coins, flag_x = generate_level()
    player    = Player(80, HEIGHT - 100)
    camera    = Camera()
    particles = []
    score     = 0
    lives     = 3
    state     = "playing"   # playing | dead | win

    while True:
        dt = clock.tick(FPS)

        # ── Eventos ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if state == "playing":
                        player.jump()
                if event.key == pygame.K_RETURN:
                    if state in ("dead", "win"):
                        return "restart"
                if event.key == pygame.K_ESCAPE:
                    return "menu"

        if state == "playing":
            # ── Update ───────────────────────────────────────────────────────
            player.update(platforms, particles)
            camera.update(player)

            for e in enemies:
                e.update(platforms)

            for c in coins:
                if not c.collected:
                    c.update()

            for p in particles[:]:
                p.update()
                if p.dead:
                    particles.remove(p)

            # ── Colisão jogador × inimigos ───────────────────────────────────
            for e in enemies:
                if e.alive and player.rect.colliderect(e.rect):
                    # pisa no inimigo pela cima?
                    if player.vy > 1 and player.rect.bottom < e.rect.centery + 10:
                        e.alive = False
                        player.vy = -9
                        score += 100
                        for _ in range(15):
                            particles.append(Particle(e.rect.centerx, e.rect.centery, ENEMY_COL))
                        snd_coin.play()
                    else:
                        if player.hit(particles):
                            lives -= 1
                            if lives <= 0:
                                snd_dead.play()
                                state = "dead"

            # ── Colisão jogador × moedas ─────────────────────────────────────
            for c in coins:
                if not c.collected and player.rect.colliderect(c.rect):
                    c.collected = True
                    score += 50
                    snd_coin.play()
                    for _ in range(8):
                        particles.append(Particle(c.rect.centerx, c.rect.centery, COIN_COL))

            # ── Morte por queda ──────────────────────────────────────────────
            if not player.alive:
                lives -= 1
                if lives <= 0:
                    snd_dead.play()
                    state = "dead"
                else:
                    player = Player(80, HEIGHT - 100)
                    camera = Camera()

            # ── Vitória ──────────────────────────────────────────────────────
            if player.rect.left > flag_x:
                state = "win"

        # ── Desenho ──────────────────────────────────────────────────────────
        draw_background(screen, camera.offset_x)

        for p in platforms:
            p.draw(screen, camera)

        for c in coins:
            if not c.collected:
                c.draw(screen, camera)

        for e in enemies:
            if e.alive:
                e.draw(screen, camera)

        for part in particles:
            part.draw(screen, camera.offset_x)

        # flag (bandeira do fim)
        fr = camera.apply(pygame.Rect(flag_x, HEIGHT - 160, 8, 120))
        pygame.draw.rect(screen, WHITE, fr)
        pygame.draw.rect(screen, YELLOW, (fr.left, fr.top, 30, 20))
        pygame.draw.rect(screen, RED,    (fr.left, fr.top + 20, 30, 20))

        player.draw(screen, camera)

        draw_hud(screen, score, lives,
                 sum(1 for c in coins if not c.collected))

        if state == "dead":
            draw_overlay(screen, "GAME OVER", "Você foi eliminado!", score)
        elif state == "win":
            draw_overlay(screen, "VOCÊ VENCEU!", "Chegou à bandeira!", score)

        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
# ESTADO DO MENU
# ══════════════════════════════════════════════════════════════════════════════
def run_menu():
    tick = 0
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "game"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

        draw_menu(screen, tick)
        pygame.display.flip()
        tick += 1

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    current = "menu"
    while True:
        if current == "menu":
            current = run_menu()
        elif current == "game":
            result = run_game()
            if result == "restart":
                current = "game"
            else:
                current = "menu"

if __name__ == "__main__":
    main()