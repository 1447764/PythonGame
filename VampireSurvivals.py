import pygame
import random
import math

# --- 상수 정의 ---
# 화면 크기
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
# 월드(게임 맵) 크기 - 화면의 5배 크기로 확장
WORLD_WIDTH = SCREEN_WIDTH * 5
WORLD_HEIGHT = SCREEN_HEIGHT * 5
# 초당 프레임 수
FPS = 60
# 화면에 등장할 수 있는 최대 적의 수
MAX_ENEMIES_ON_SCREEN = 150

# 색상
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 20)
CYAN = (0, 255, 255)
DARK_GREY = (40, 40, 40)
LIGHT_GREY = (100, 100, 100)
UI_BG_COLOR = (50, 50, 80)
UI_BORDER_COLOR = (200, 200, 255)
UI_OPTION_BG_COLOR = (80, 80, 120)

# 레벨업에 필요한 경험치 데이터 (초반은 쉽고 후반은 어렵게)
LEVEL_DATA = [50, 75, 110, 150, 220, 300, 450, 600, 800, 1000, 1250, 1500]

# 업그레이드 및 스킬 데이터 정의
UPGRADE_DATA = {
    # 기본 스탯 업그레이드
    'WEAPON_DAMAGE': {'name': '마법탄 공격력 +5', 'description': '모든 마법탄의 공격력이 5 증가합니다.'},
    'WEAPON_COOLDOWN': {'name': '마법탄 연사 속도 +10%', 'description': '마법탄의 발사 속도가 10% 빨라집니다.'},
    'PLAYER_SPEED': {'name': '이동 속도 +0.5', 'description': '플레이어의 이동 속도가 0.5 증가합니다.'},
    'MAX_HP': {'name': '최대 체력 +20', 'description': '최대 체력이 20 증가합니다. (체력 회복 없음)'},
    'PROJECTILE_SPEED': {'name': '마법탄 속도 +1', 'description': '마법탄의 비행 속도가 1 증가합니다.'},
    # 스킬 획득
    'ACQUIRE_BIBLE': {'name': '성스러운 책 획득', 'description': '주위를 맴도는 방어용 책을 소환합니다.'},
    # 스킬 업그레이드
    'BIBLE_DAMAGE': {'name': '성스러운 책 공격력 +8', 'description': '책의 공격력이 8 증가합니다.'},
    'BIBLE_COUNT': {'name': '성스러운 책 개수 +1', 'description': '책의 개수가 1개 늘어납니다.'},
    'BIBLE_RANGE': {'name': '성스러운 책 범위 +15%', 'description': '책의 회전 반경이 15% 넓어집니다.'},
}

# --- [추가됨] UI 버튼 클래스 ---
class Button:
    def __init__(self, x, y, width, height, text, font, bg_color=UI_OPTION_BG_COLOR, border_color=UI_BORDER_COLOR):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.border_color = border_color
        self.is_hovered = False

    def draw(self, surface):
        color = tuple(min(c + 30, 255) for c in self.bg_color) if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, self.border_color, self.rect, 3, border_radius=10)
        
        text_surf = self.font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered and event.button == 1:
                return True
        return False

# --- 카메라 클래스 ---
class Camera:
    def __init__(self, world_width, world_height):
        self.rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.world_width = world_width
        self.world_height = world_height

    def apply(self, target_rect):
        return target_rect.move(self.rect.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.world_width - SCREEN_WIDTH), x)
        y = max(-(self.world_height - SCREEN_HEIGHT), y)
        self.rect.topleft = (x, y)


# --- 플레이어 클래스 ---
class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((50, 50))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
        self.rect.center = self.pos
        self.base_speed = 5
        self.base_max_hp = 100
        self.base_weapon_cooldown = 500
        self.base_weapon_damage = 10
        self.base_projectile_speed = 10
        self.bible_sprites = pygame.sprite.Group()

    def reset(self):
        self.pos.x, self.pos.y = WORLD_WIDTH / 2, WORLD_HEIGHT / 2
        self.speed = self.base_speed
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.weapon_cooldown = self.base_weapon_cooldown
        self.weapon_damage = self.base_weapon_damage
        self.projectile_speed = self.base_projectile_speed
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = LEVEL_DATA[0]
        self.invincible = False
        self.skills = {}
        self.last_shot_time = 0
        self.invincible_duration = 1000
        self.last_hit_time = 0
        for bible in self.bible_sprites:
            bible.kill()

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next_level
        if self.level - 1 < len(LEVEL_DATA):
            self.exp_to_next_level = LEVEL_DATA[self.level - 1]
        else:
            self.exp_to_next_level = float('inf')
        self.game.generate_upgrades() 
        self.game.game_state = 'LEVEL_UP'

    def create_bibles(self):
        for sprite in self.bible_sprites:
            sprite.kill()
        if 'bible' in self.skills:
            stats = self.skills['bible']
            count = stats['count']
            angle_step = 360 / count
            for i in range(count):
                bible = Bible(self.game)
                bible.angle = i * angle_step
                self.bible_sprites.add(bible)
                self.game.all_sprites.add(bible)
                self.game.skill_sprites.add(bible)

    def fire_weapon(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.weapon_cooldown:
            self.last_shot_time = now
            target_enemy = self.find_closest_enemy()
            if target_enemy:
                Projectile(self.game, self.pos, target_enemy)

    def find_closest_enemy(self):
        closest_dist = float('inf')
        closest_enemy = None
        for enemy in self.game.enemies:
            dist = self.pos.distance_to(enemy.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_enemy = enemy
        return closest_enemy

    def take_damage(self, amount):
        if not self.invincible:
            self.hp -= amount
            self.invincible = True
            self.last_hit_time = pygame.time.get_ticks()
            if self.hp <= 0:
                self.hp = 0
                self.game.game_state = 'GAME_OVER'

    def update(self):
        if self.invincible:
            if pygame.time.get_ticks() - self.last_hit_time > self.invincible_duration:
                self.invincible = False
        vel = pygame.math.Vector2(0, 0)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: vel.x = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: vel.x = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: vel.y = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: vel.y = 1
        if vel.length() > 0:
            vel.normalize_ip()
            self.pos += vel * self.speed
        self.pos.x = max(0, min(self.pos.x, WORLD_WIDTH))
        self.pos.y = max(0, min(self.pos.y, WORLD_HEIGHT))
        self.rect.center = self.pos
        self.fire_weapon()

    def draw_hp_bar(self, surface, camera):
        if self.hp > 0:
            bar_width = 50
            bar_height = 8
            hp_bar_world_rect = pygame.Rect(self.rect.x, self.rect.y - 15, bar_width, bar_height)
            hp_bar_screen_rect = camera.apply(hp_bar_world_rect)
            hp_ratio = self.hp / self.max_hp
            current_hp_width = bar_width * hp_ratio
            current_hp_rect = pygame.Rect(hp_bar_screen_rect.x, hp_bar_screen_rect.y, current_hp_width, bar_height)
            pygame.draw.rect(surface, RED, hp_bar_screen_rect)
            pygame.draw.rect(surface, GREEN, current_hp_rect)

# --- 적 클래스 ---
class Enemy(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((40, 40))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(0, 0)
        self.speed = random.randint(1, 2)
        self.max_hp = 20
        self.hp = self.max_hp
        self.exp_drop = 15
        self.damage = 5
        self.last_skill_hit_time = 0
        self.skill_hit_cooldown = 500

    def reset(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.rect.center = self.pos
        self.hp = self.max_hp
        self.speed = random.randint(1, 2)
        self.last_skill_hit_time = 0
        self.game.all_sprites.add(self)
        self.game.enemies.add(self)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.game.return_enemy_to_pool(self)
            return self.rect.center
        return None

    def update(self):
        player_pos = self.game.player.pos
        attraction_vec = player_pos - self.pos
        separation_vec = pygame.math.Vector2(0, 0)
        close_enemies_count = 0
        for other in self.game.enemies:
            if other is not self:
                dist_to_other = self.pos.distance_to(other.pos)
                if dist_to_other < 40:
                    separation_vec += self.pos - other.pos
                    close_enemies_count += 1
        final_vec = pygame.math.Vector2(0, 0)
        if attraction_vec.length() > 40:
            final_vec = attraction_vec.normalize()
            if close_enemies_count > 0 and separation_vec.length() > 0:
                final_vec = final_vec * 0.7 + separation_vec.normalize() * 0.3
        if final_vec.length() > 0:
            final_vec.normalize_ip()
            self.pos += final_vec * self.speed
        self.rect.center = self.pos


# --- 경험치 보석 클래스 ---
class ExpGem(pygame.sprite.Sprite):
    def __init__(self, pos, exp_value):
        super().__init__()
        self.image = pygame.Surface((15, 15))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=pos)
        self.exp_value = exp_value

# --- 투사체 클래스 ---
class Projectile(pygame.sprite.Sprite):
    def __init__(self, game, pos, target_enemy):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((10, 10))
        self.image.fill(WHITE)
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        self.speed = self.game.player.projectile_speed
        self.damage = self.game.player.weapon_damage
        self.lifespan = 2000
        self.spawn_time = pygame.time.get_ticks()
        direction = (target_enemy.pos - self.pos).normalize()
        self.vel = direction * self.speed
        self.game.all_sprites.add(self)
        self.game.projectiles.add(self)

    def update(self):
        self.pos += self.vel
        self.rect.center = self.pos
        if pygame.time.get_ticks() - self.spawn_time > self.lifespan:
            self.kill()

# --- 성스러운 책 스킬 클래스 ---
class Bible(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((30, 40))
        self.image.fill(CYAN)
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(0, 0)
        self.stats = self.game.player.skills['bible']
        self.angle = 0
        self.rotation_speed = self.stats.get('speed', 2)
        self.orbit_radius = self.stats.get('range', 100)

    def update(self):
        self.angle = (self.angle + self.rotation_speed) % 360
        player_pos = self.game.player.pos
        self.pos.x = player_pos.x + math.cos(math.radians(self.angle)) * self.orbit_radius
        self.pos.y = player_pos.y + math.sin(math.radians(self.angle)) * self.orbit_radius
        self.rect.center = self.pos


# --- 게임 클래스 ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Vampire Survivors")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True
        font_path = "GmarketSansTTF/GmarketSansTTFMedium.ttf"
        self.title_font = pygame.font.Font(font_path, 96)
        self.header_font = pygame.font.Font(font_path, 72)
        self.ui_font = pygame.font.Font(font_path, 36)
        self.upgrade_font = pygame.font.Font(font_path, 28)
        
        # [수정됨] 게임 상태를 START_MENU에서 시작
        self.game_state = 'START_MENU' 
        
        self.current_upgrade_options = []
        self.upgrade_option_rects = []

        # [추가됨] 골드 (임시)
        self.gold = 1234
        
        # [추가됨] 시작 메뉴 버튼
        button_width, button_height = 250, 60
        button_x = SCREEN_WIDTH / 2 - button_width / 2
        self.start_button = Button(button_x, 300, button_width, button_height, '게임 시작', self.ui_font)
        self.credits_button = Button(button_x, 400, button_width, button_height, '제작진', self.ui_font)
        self.quit_button = Button(button_x, 500, button_width, button_height, '나가기', self.ui_font)
        self.back_button = Button(button_x, 600, button_width, button_height, '뒤로 가기', self.ui_font)


    def run(self):
        while self.is_running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()

    def new_game(self):
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.exp_gems = pygame.sprite.Group()
        self.skill_sprites = pygame.sprite.Group()
        self.enemy_pool = []
        self.spawn_timer = 0
        self.spawn_interval = 500
        self.game_state = 'PLAYING'
        self.game_start_time = pygame.time.get_ticks()
        self.paused_time = 0
        if not hasattr(self, 'player'):
            self.player = Player(self)
        self.player.reset()
        self.all_sprites.add(self.player)
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.background_image = self.create_background()
        self.background_rect = self.background_image.get_rect()

    def generate_upgrades(self):
        upgrade_pool = list(UPGRADE_DATA.keys())
        available_upgrades = []
        for key in upgrade_pool:
            if key.startswith('BIBLE_'):
                if 'bible' in self.player.skills:
                    available_upgrades.append(key)
            elif key == 'ACQUIRE_BIBLE':
                if 'bible' not in self.player.skills:
                    available_upgrades.append(key)
            else:
                available_upgrades.append(key)
        sample_size = min(3, len(available_upgrades))
        self.current_upgrade_options = random.sample(available_upgrades, sample_size)
        self.paused_time = pygame.time.get_ticks()

    def apply_upgrade(self, upgrade_key):
        if upgrade_key == 'WEAPON_DAMAGE': self.player.weapon_damage += 5
        elif upgrade_key == 'WEAPON_COOLDOWN': self.player.weapon_cooldown *= 0.9 
        elif upgrade_key == 'PLAYER_SPEED': self.player.speed += 0.5
        elif upgrade_key == 'MAX_HP': self.player.max_hp += 20
        elif upgrade_key == 'PROJECTILE_SPEED': self.player.projectile_speed += 1
        elif upgrade_key == 'ACQUIRE_BIBLE':
            self.player.skills['bible'] = {'damage': 15, 'count': 1, 'range': 100, 'speed': 2}
            self.player.create_bibles()
        elif upgrade_key == 'BIBLE_DAMAGE': self.player.skills['bible']['damage'] += 8
        elif upgrade_key == 'BIBLE_COUNT':
            self.player.skills['bible']['count'] += 1
            self.player.create_bibles()
        elif upgrade_key == 'BIBLE_RANGE':
            self.player.skills['bible']['range'] *= 1.15
            self.player.create_bibles()
        pause_duration = pygame.time.get_ticks() - self.paused_time
        self.game_start_time += pause_duration

    def return_enemy_to_pool(self, enemy):
        enemy.kill()
        self.enemy_pool.append(enemy)

    def manage_enemy_spawning(self):
        self.spawn_timer += self.clock.get_time()
        if self.spawn_timer > self.spawn_interval:
            self.spawn_timer = 0
            if len(self.enemies) < MAX_ENEMIES_ON_SCREEN:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(700, 800)
                x = self.player.pos.x + math.cos(angle) * distance
                y = self.player.pos.y + math.sin(angle) * distance
                x = max(0, min(x, WORLD_WIDTH))
                y = max(0, min(y, WORLD_HEIGHT))
                enemy = self.enemy_pool.pop() if self.enemy_pool else Enemy(self)
                enemy.reset((x, y))

    def create_background(self):
        background = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
        background.fill(DARK_GREY)
        tile_size = 100
        for x in range(0, WORLD_WIDTH, tile_size): pygame.draw.line(background, LIGHT_GREY, (x, 0), (x, WORLD_HEIGHT))
        for y in range(0, WORLD_HEIGHT, tile_size): pygame.draw.line(background, LIGHT_GREY, (0, y), (WORLD_WIDTH, y))
        return background

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            
            if self.game_state == 'START_MENU':
                if self.start_button.handle_event(event): self.new_game()
                if self.credits_button.handle_event(event): self.game_state = 'CREDITS'
                if self.quit_button.handle_event(event): self.is_running = False
            
            elif self.game_state == 'CREDITS':
                if self.back_button.handle_event(event): self.game_state = 'START_MENU'

            elif self.game_state == 'GAME_OVER':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.new_game()

            elif self.game_state == 'LEVEL_UP':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.upgrade_option_rects):
                        if rect.collidepoint(event.pos):
                            self.apply_upgrade(self.current_upgrade_options[i])
                            self.game_state = 'PLAYING'
                            break
    
    def update(self):
        if self.game_state == 'PLAYING':
            self.all_sprites.update()
            self.camera.update(self.player)
            self.manage_enemy_spawning()
            # ... (충돌 감지 로직은 기존과 동일) ...
            hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, True)
            for enemy, projectiles_hit in hits.items():
                for proj in projectiles_hit:
                    if gem_pos := enemy.take_damage(proj.damage):
                        gem = ExpGem(gem_pos, enemy.exp_drop)
                        self.all_sprites.add(gem)
                        self.exp_gems.add(gem)
            if not self.player.invincible:
                if colliding_enemies := pygame.sprite.spritecollide(self.player, self.enemies, False):
                    self.player.take_damage(colliding_enemies[0].damage)
            gems_collected = pygame.sprite.spritecollide(self.player, self.exp_gems, True)
            for gem in gems_collected:
                self.player.gain_exp(gem.exp_value)
            skill_hits = pygame.sprite.groupcollide(self.enemies, self.skill_sprites, False, False)
            for enemy, skills_hit in skill_hits.items():
                now = pygame.time.get_ticks()
                if now - enemy.last_skill_hit_time > enemy.skill_hit_cooldown:
                    enemy.last_skill_hit_time = now
                    if isinstance(skills_hit[0], Bible):
                        damage = self.player.skills['bible']['damage']
                        if gem_pos := enemy.take_damage(damage):
                            gem = ExpGem(gem_pos, enemy.exp_drop)
                            self.all_sprites.add(gem)
                            self.exp_gems.add(gem)

    def draw(self):
        # [수정됨] 게임 상태에 따라 다른 화면을 그림
        if self.game_state == 'START_MENU':
            self.draw_start_menu()
        elif self.game_state == 'CREDITS':
            self.draw_credits_screen()
        elif self.game_state in ['PLAYING', 'LEVEL_UP', 'GAME_OVER']:
            self.draw_game_screen()
        
        pygame.display.flip()
        
    def draw_start_menu(self):
        self.screen.fill(DARK_GREY)
        title_text = self.title_font.render("Vampire Survivals", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH/2, 150))
        self.screen.blit(title_text, title_rect)
        
        self.start_button.draw(self.screen)
        self.credits_button.draw(self.screen)
        self.quit_button.draw(self.screen)
        
        gold_text = self.ui_font.render(f"소유 골드: {self.gold} G", True, YELLOW)
        gold_rect = gold_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 50))
        self.screen.blit(gold_text, gold_rect)

    def draw_credits_screen(self):
        self.screen.fill(DARK_GREY)
        credits_text = self.header_font.render("제작진", True, WHITE)
        credits_rect = credits_text.get_rect(center=(SCREEN_WIDTH/2, 150))
        self.screen.blit(credits_text, credits_rect)
        
        creator_text = self.ui_font.render("Created by 문현아", True, WHITE)
        creator_rect = creator_text.get_rect(center=(SCREEN_WIDTH/2, 350))
        self.screen.blit(creator_text, creator_rect)
        
        self.back_button.draw(self.screen)

    def draw_game_screen(self):
        self.screen.fill(DARK_GREY)
        self.screen.blit(self.background_image, self.camera.apply(self.background_rect))
        for sprite in self.all_sprites:
            self.screen.blit(sprite.image, self.camera.apply(sprite.rect))
        self.player.draw_hp_bar(self.screen, self.camera)
        self.draw_game_ui()
        
    def draw_game_ui(self):
        # EXP 바
        exp_bar_width = SCREEN_WIDTH - 40
        exp_bar_height = 20
        exp_ratio = self.player.exp / self.player.exp_to_next_level
        current_exp_width = exp_bar_width * exp_ratio
        pygame.draw.rect(self.screen, UI_BG_COLOR, (20, 20, exp_bar_width, exp_bar_height))
        pygame.draw.rect(self.screen, YELLOW, (20, 20, current_exp_width, exp_bar_height))
        pygame.draw.rect(self.screen, UI_BORDER_COLOR, (20, 20, exp_bar_width, exp_bar_height), 3)
        level_text = self.ui_font.render(f"LV {self.player.level}", True, WHITE)
        self.screen.blit(level_text, (30, 45))
        
        # 타이머
        elapsed_ticks = self.paused_time - self.game_start_time if self.game_state != 'PLAYING' else pygame.time.get_ticks() - self.game_start_time
        elapsed_seconds = elapsed_ticks // 1000
        minutes, seconds = divmod(elapsed_seconds, 60)
        timer_text = self.ui_font.render(f"{minutes:02}:{seconds:02}", True, WHITE)
        timer_rect = timer_text.get_rect(center=(SCREEN_WIDTH / 2, 60))
        self.screen.blit(timer_text, timer_rect)

        # 레벨업 / 게임 오버 창
        if self.game_state == 'LEVEL_UP':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            title_text = self.header_font.render("LEVEL UP!", True, YELLOW)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 5))
            self.screen.blit(title_text, title_rect)
            self.upgrade_option_rects.clear()
            option_width, option_height = 500, 100
            start_y = SCREEN_HEIGHT / 2 - (option_height * 1.5 + 20)
            for i, option_key in enumerate(self.current_upgrade_options):
                option_data = UPGRADE_DATA[option_key]
                y = start_y + i * (option_height + 20)
                rect = pygame.Rect(SCREEN_WIDTH / 2 - option_width / 2, y, option_width, option_height)
                self.upgrade_option_rects.append(rect)
                pygame.draw.rect(self.screen, UI_OPTION_BG_COLOR, rect, border_radius=10)
                pygame.draw.rect(self.screen, UI_BORDER_COLOR, rect, 3, border_radius=10)
                name_text = self.ui_font.render(option_data['name'], True, WHITE)
                name_rect = name_text.get_rect(center=(rect.centerx, rect.centery - 15))
                self.screen.blit(name_text, name_rect)
                desc_text = self.upgrade_font.render(option_data['description'], True, LIGHT_GREY)
                desc_rect = desc_text.get_rect(center=(rect.centerx, rect.centery + 15))
                self.screen.blit(desc_text, desc_rect)

        elif self.game_state == 'GAME_OVER':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))
            game_over_text = self.header_font.render("GAME OVER", True, RED)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3))
            self.screen.blit(game_over_text, game_over_rect)
            restart_text = self.ui_font.render("Press 'R' to Restart", True, WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(restart_text, restart_rect)

if __name__ == '__main__':
    game = Game()
    game.run()

