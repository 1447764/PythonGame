import pygame
import random
import math
import json
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
# 데이터 저장 파일명
SAVE_FILE = 'save_data.json'


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

# 레벨업에 필요한 경험치 데이터 확장
LEVEL_DATA = [50] * 100


# 인게임 업그레이드 및 스킬 데이터 정의
UPGRADE_DATA = {
    'WEAPON_DAMAGE': {'name': '마법탄 공격력 +5', 'description': '모든 마법탄의 공격력이 5 증가합니다.'},
    'WEAPON_COOLDOWN': {'name': '마법탄 연사 속도 +10%', 'description': '마법탄의 발사 속도가 10% 빨라집니다.'},
    'PLAYER_SPEED': {'name': '이동 속도 +0.5', 'description': '플레이어의 이동 속도가 0.5 증가합니다.'},
    'MAX_HP': {'name': '최대 체력 +20', 'description': '최대 체력이 20 증가합니다. (체력 회복 없음)'},
    'PROJECTILE_SPEED': {'name': '마법탄 속도 +1', 'description': '마법탄의 비행 속도가 1 증가합니다.'},
    'ACQUIRE_BIBLE': {'name': '성스러운 책 획득', 'description': '주위를 맴도는 방어용 책을 소환합니다.'},
    'BIBLE_DAMAGE': {'name': '성스러운 책 공격력 +8', 'description': '책의 공격력이 8 증가합니다.'},
    'BIBLE_COUNT': {'name': '성스러운 책 개수 +1', 'description': '책의 개수가 1개 늘어납니다.'},
    'BIBLE_SPEED': {'name': '성스러운 책 회전 속도 +20%', 'description': '책의 회전 속도가 20% 빨라집니다.'},
}

# 상점 영구 업그레이드 데이터 정의
PERMANENT_UPGRADE_DATA = {
    'MAX_HP': {'name': '최대 체력 증가', 'description': '기본 최대 체력이 10 증가합니다.', 'base_cost': 100, 'cost_increase_factor': 1.5, 'max_level': 20},
    'EXP_GAIN': {'name': '경험치 획득량 증가', 'description': '경험치 획득량이 5% 증가합니다.', 'base_cost': 150, 'cost_increase_factor': 1.8, 'max_level': 10},
    'GOLD_GAIN': {'name': '골드 획득량 증가', 'description': '골드 획득량이 10% 증가합니다.', 'base_cost': 150, 'cost_increase_factor': 2.0, 'max_level': 10},
}


# --- UI 버튼 클래스 ---
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
        x = min(0, x); y = min(0, y)
        x = max(-(self.world_width - SCREEN_WIDTH), x)
        y = max(-(self.world_height - SCREEN_HEIGHT), y)
        self.rect.topleft = (x, y)

# --- 플레이어 클래스 ---
class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((50, 50)); self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
        self.bible_sprites = pygame.sprite.Group()

    def reset(self):
        hp_bonus = self.game.permanent_upgrades.get('MAX_HP', 0) * 10
        self.base_max_hp = 100 + hp_bonus
        self.exp_gain_multiplier = 1 + (self.game.permanent_upgrades.get('EXP_GAIN', 0) * 0.05)
        self.gold_gain_multiplier = 1 + (self.game.permanent_upgrades.get('GOLD_GAIN', 0) * 0.1)
        self.pos.x, self.pos.y = WORLD_WIDTH / 2, WORLD_HEIGHT / 2
        self.speed = 5
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.weapon_cooldown = 500
        self.weapon_damage = 10
        self.projectile_speed = 10
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = LEVEL_DATA[0]
        self.invincible = False
        self.skills = {}
        self.last_shot_time = 0
        self.invincible_duration = 1000
        self.last_hit_time = 0
        for bible in self.bible_sprites: bible.kill()

    def gain_exp(self, amount):
        self.exp += amount * self.exp_gain_multiplier
        if self.exp >= self.exp_to_next_level:
            self.level_up()
    
    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next_level
        if self.level - 1 < len(LEVEL_DATA):
            self.exp_to_next_level = LEVEL_DATA[self.level - 1]
        else:
            self.exp_to_next_level = LEVEL_DATA[-1] + (self.level - len(LEVEL_DATA)) * 500
        self.game.generate_upgrades() 
        self.game.game_state = 'LEVEL_UP'

    def create_bibles(self):
        for sprite in self.bible_sprites: sprite.kill()
        if 'bible' in self.skills:
            stats = self.skills['bible']; count = stats['count']; angle_step = 360 / count
            for i in range(count):
                bible = Bible(self.game); bible.angle = i * angle_step
                self.bible_sprites.add(bible); self.game.all_sprites.add(bible); self.game.skill_sprites.add(bible)
    def fire_weapon(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.weapon_cooldown:
            self.last_shot_time = now
            if target_enemy := self.find_closest_enemy(): Projectile(self.game, self.pos, target_enemy)
    def find_closest_enemy(self):
        closest_dist = float('inf'); closest_enemy = None
        for enemy in self.game.enemies:
            dist = self.pos.distance_to(enemy.pos)
            if dist < closest_dist: closest_dist = dist; closest_enemy = enemy
        return closest_enemy
        
    def take_damage(self, amount):
        if not self.invincible:
            self.hp -= amount
            self.invincible = True
            self.last_hit_time = pygame.time.get_ticks()
            if self.hp <= 0:
                self.hp = 0
                self.game.game_state = 'GAME_OVER'
                self.game.paused_time = pygame.time.get_ticks() # [추가] 게임 오버된 시간을 기록

    def update(self):
        if self.invincible and pygame.time.get_ticks() - self.last_hit_time > self.invincible_duration: self.invincible = False
        vel = pygame.math.Vector2(0, 0)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: vel.x = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: vel.x = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: vel.y = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: vel.y = 1
        if vel.length() > 0: vel.normalize_ip(); self.pos += vel * self.speed
        self.pos.x = max(0, min(self.pos.x, WORLD_WIDTH)); self.pos.y = max(0, min(self.pos.y, WORLD_HEIGHT))
        self.rect.center = self.pos; self.fire_weapon()
    def draw_hp_bar(self, surface, camera):
        if self.hp > 0:
            bar_width = 50; bar_height = 8
            hp_bar_world_rect = pygame.Rect(self.rect.x, self.rect.y - 15, bar_width, bar_height)
            hp_bar_screen_rect = camera.apply(hp_bar_world_rect); hp_ratio = self.hp / self.max_hp
            current_hp_width = bar_width * hp_ratio
            current_hp_rect = pygame.Rect(hp_bar_screen_rect.x, hp_bar_screen_rect.y, current_hp_width, bar_height)
            pygame.draw.rect(surface, RED, hp_bar_screen_rect); pygame.draw.rect(surface, GREEN, current_hp_rect)

# --- 적 클래스 ---
class Enemy(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((40, 40)); self.image.fill(RED)
        self.rect = self.image.get_rect(); self.pos = pygame.math.Vector2(0, 0)
        self.speed = random.randint(1, 2); self.max_hp = 20; self.hp = self.max_hp
        self.exp_drop = 15; self.damage = 5; self.last_skill_hit_time = 0; self.skill_hit_cooldown = 500
        self.gold_drop = random.randint(1, 5)

    def reset(self, pos):
        self.pos = pygame.math.Vector2(pos); self.rect.center = self.pos
        self.hp = self.max_hp; self.speed = random.randint(1, 2); self.last_skill_hit_time = 0
        self.game.all_sprites.add(self); self.game.enemies.add(self)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.game.gain_gold(self.gold_drop)
            self.game.return_enemy_to_pool(self)
            return self.rect.center
        return None
    def update(self):
        player_pos = self.game.player.pos; attraction_vec = player_pos - self.pos
        separation_vec = pygame.math.Vector2(0, 0); close_enemies_count = 0
        for other in self.game.enemies:
            if other is not self:
                dist_to_other = self.pos.distance_to(other.pos)
                if dist_to_other < 40:
                    separation_vec += self.pos - other.pos; close_enemies_count += 1
        final_vec = pygame.math.Vector2(0, 0)
        if attraction_vec.length() > 40:
            final_vec = attraction_vec.normalize()
            if close_enemies_count > 0 and separation_vec.length() > 0: final_vec = final_vec * 0.7 + separation_vec.normalize() * 0.3
        if final_vec.length() > 0: final_vec.normalize_ip(); self.pos += final_vec * self.speed
        self.rect.center = self.pos

# --- 경험치 보석 클래스 ---
class ExpGem(pygame.sprite.Sprite):
    def __init__(self, pos, exp_value):
        super().__init__(); self.image = pygame.Surface((15, 15)); self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=pos); self.exp_value = exp_value

# --- 투사체 클래스 ---
class Projectile(pygame.sprite.Sprite):
    def __init__(self, game, pos, target_enemy):
        super().__init__(); self.game = game; self.image = pygame.Surface((10, 10)); self.image.fill(WHITE)
        self.pos = pygame.math.Vector2(pos); self.rect = self.image.get_rect(center=self.pos)
        self.speed = self.game.player.projectile_speed; self.damage = self.game.player.weapon_damage
        self.lifespan = 2000; self.spawn_time = pygame.time.get_ticks()
        direction = (target_enemy.pos - self.pos).normalize(); self.vel = direction * self.speed
        self.game.all_sprites.add(self); self.game.projectiles.add(self)
    def update(self):
        self.pos += self.vel; self.rect.center = self.pos
        if pygame.time.get_ticks() - self.spawn_time > self.lifespan: self.kill()

# --- 성스러운 책 스킬 클래스 ---
class Bible(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__(); self.game = game; self.image = pygame.Surface((30, 40)); self.image.fill(CYAN)
        self.rect = self.image.get_rect(); self.pos = pygame.math.Vector2(0, 0)
        self.stats = self.game.player.skills['bible']; self.angle = 0
        self.rotation_speed = self.stats.get('speed', 2); self.orbit_radius = self.stats.get('range', 100)
    def update(self):
        self.angle = (self.angle + self.rotation_speed) % 360; player_pos = self.game.player.pos
        self.pos.x = player_pos.x + math.cos(math.radians(self.angle)) * self.orbit_radius
        self.pos.y = player_pos.y + math.sin(math.radians(self.angle)) * self.orbit_radius
        self.rect.center = self.pos

# --- 게임 클래스 ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Vampire Survivors Clone")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True
        font_path = resource_path("GmarketSansTTF/GmarketSansTTFMedium.ttf")
        self.title_font = pygame.font.Font(font_path, 96)
        self.header_font = pygame.font.Font(font_path, 72)
        self.ui_font = pygame.font.Font(font_path, 36)
        self.upgrade_font = pygame.font.Font(font_path, 28)
        self.small_font = pygame.font.Font(font_path, 24)
        
        self.game_state = 'START_MENU' 
        self.current_upgrade_options = []
        self.upgrade_option_rects = []
        
        self.load_game_data()

        btn_w, btn_h, btn_gap = 250, 60, 20
        btn_x = SCREEN_WIDTH / 2 - btn_w / 2
        self.start_button = Button(btn_x, 300, btn_w, btn_h, '게임 시작', self.ui_font)
        self.shop_button = Button(btn_x, 300 + btn_h + btn_gap, btn_w, btn_h, '상점', self.ui_font)
        self.credits_button = Button(btn_x, 300 + (btn_h + btn_gap) * 2, btn_w, btn_h, '제작진', self.ui_font)
        self.quit_button = Button(btn_x, 300 + (btn_h + btn_gap) * 3, btn_w, btn_h, '나가기', self.ui_font)
        self.back_button = Button(btn_x, SCREEN_HEIGHT - 100, btn_w, btn_h, '뒤로 가기', self.ui_font)

        # [추가] 일시정지 메뉴 버튼
        self.resume_button = Button(btn_x, 350, btn_w, btn_h, '계속하기', self.ui_font)
        self.pause_main_menu_button = Button(btn_x, 350 + btn_h + btn_gap, btn_w, btn_h, '메인 화면', self.ui_font)

        # [추가] 게임 오버 메뉴 버튼
        self.restart_button = Button(btn_x, 350, btn_w, btn_h, '새 게임', self.ui_font)
        self.game_over_main_menu_button = Button(btn_x, 350 + btn_h + btn_gap, btn_w, btn_h, '메인 화면', self.ui_font)


    def load_game_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    self.gold = data.get('gold', 0)
                    self.permanent_upgrades = data.get('permanent_upgrades', {})
            except (json.JSONDecodeError, FileNotFoundError):
                self.gold = 0; self.permanent_upgrades = {}
        else:
            self.gold = 0; self.permanent_upgrades = {}
        for key in PERMANENT_UPGRADE_DATA:
            if key not in self.permanent_upgrades: self.permanent_upgrades[key] = 0
        self.save_game_data()

    def save_game_data(self):
        data = {'gold': self.gold, 'permanent_upgrades': self.permanent_upgrades}
        with open(SAVE_FILE, 'w') as f: json.dump(data, f, indent=4)
            
    def gain_gold(self, amount):
        self.gold += int(amount * self.player.gold_gain_multiplier)

    def run(self):
        while self.is_running:
            self.clock.tick(FPS); self.handle_events(); self.update(); self.draw()
        self.save_game_data(); pygame.quit()

    def new_game(self):
        self.all_sprites = pygame.sprite.Group(); self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group(); self.exp_gems = pygame.sprite.Group()
        self.skill_sprites = pygame.sprite.Group(); self.enemy_pool = []
        self.spawn_timer = 0; self.spawn_interval = 500; self.game_state = 'PLAYING'
        self.game_start_time = pygame.time.get_ticks(); self.paused_time = 0
        self.kill_count = 0
        if not hasattr(self, 'player'): self.player = Player(self)
        self.player.reset(); self.all_sprites.add(self.player)
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.background_image = self.create_background(); self.background_rect = self.background_image.get_rect()

    def generate_upgrades(self):
        upgrade_pool = list(UPGRADE_DATA.keys()); available_upgrades = []
        for key in upgrade_pool:
            if key.startswith('BIBLE_'):
                if 'bible' in self.player.skills: available_upgrades.append(key)
            elif key == 'ACQUIRE_BIBLE':
                if 'bible' not in self.player.skills: available_upgrades.append(key)
            else: available_upgrades.append(key)
        sample_size = min(3, len(available_upgrades))
        self.current_upgrade_options = random.sample(available_upgrades, sample_size) if available_upgrades else []
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
        elif upgrade_key == 'BIBLE_COUNT': self.player.skills['bible']['count'] += 1; self.player.create_bibles()
        elif upgrade_key == 'BIBLE_SPEED':
            self.player.skills['bible']['speed'] *= 1.20 
            self.player.create_bibles() 
        pause_duration = pygame.time.get_ticks() - self.paused_time; self.game_start_time += pause_duration
    
    def return_enemy_to_pool(self, enemy): enemy.kill(); self.enemy_pool.append(enemy)
    
    def manage_enemy_spawning(self):
        self.spawn_timer += self.clock.get_time()
        if self.spawn_timer > self.spawn_interval:
            self.spawn_timer = 0
            if len(self.enemies) < MAX_ENEMIES_ON_SCREEN:
                angle = random.uniform(0, 2 * math.pi); distance = random.uniform(700, 800)
                x = self.player.pos.x + math.cos(angle) * distance; y = self.player.pos.y + math.sin(angle) * distance
                x = max(0, min(x, WORLD_WIDTH)); y = max(0, min(y, WORLD_HEIGHT))
                enemy = self.enemy_pool.pop() if self.enemy_pool else Enemy(self)
                enemy.reset((x, y))
    
    def create_background(self):
        background = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT)); background.fill(DARK_GREY)
        tile_size = 100
        for x in range(0, WORLD_WIDTH, tile_size): pygame.draw.line(background, LIGHT_GREY, (x, 0), (x, WORLD_HEIGHT))
        for y in range(0, WORLD_HEIGHT, tile_size): pygame.draw.line(background, LIGHT_GREY, (0, y), (WORLD_WIDTH, y))
        return background

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            
            # [추가] 게임 플레이 중 ESC 누르면 일시정지
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.game_state == 'PLAYING':
                    self.game_state = 'PAUSED'
                    self.paused_time = pygame.time.get_ticks() # 일시정지 시작 시간 기록
            
            if self.game_state == 'START_MENU':
                if self.start_button.handle_event(event): self.new_game()
                if self.shop_button.handle_event(event): self.game_state = 'SHOP'
                if self.credits_button.handle_event(event): self.game_state = 'CREDITS'
                if self.quit_button.handle_event(event): self.is_running = False
            
            elif self.game_state == 'SHOP':
                if self.back_button.handle_event(event): self.game_state = 'START_MENU'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for upgrade_key, (rect, _) in self.shop_buttons.items():
                        if rect.collidepoint(event.pos): self.purchase_permanent_upgrade(upgrade_key)

            elif self.game_state == 'CREDITS':
                if self.back_button.handle_event(event): self.game_state = 'START_MENU'
            
            # [추가] 일시정지 메뉴 이벤트 처리
            elif self.game_state == 'PAUSED':
                if self.resume_button.handle_event(event):
                    # 일시정지된 시간만큼 게임 시작 시간을 보정
                    pause_duration = pygame.time.get_ticks() - self.paused_time
                    self.game_start_time += pause_duration
                    self.game_state = 'PLAYING'
                if self.pause_main_menu_button.handle_event(event):
                    self.game_state = 'START_MENU'

            # [수정] 게임 오버 시 R키 대신 버튼 사용
            elif self.game_state == 'GAME_OVER':
                if self.restart_button.handle_event(event):
                    self.new_game()
                if self.game_over_main_menu_button.handle_event(event):
                    self.game_state = 'START_MENU'

            elif self.game_state == 'LEVEL_UP':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.upgrade_option_rects):
                        if rect.collidepoint(event.pos):
                            self.apply_upgrade(self.current_upgrade_options[i]); self.game_state = 'PLAYING'; break
    
    def purchase_permanent_upgrade(self, upgrade_key):
        data = PERMANENT_UPGRADE_DATA[upgrade_key]
        current_level = self.permanent_upgrades.get(upgrade_key, 0)
        if current_level < data['max_level']:
            cost = int(data['base_cost'] * (data['cost_increase_factor'] ** current_level))
            if self.gold >= cost:
                self.gold -= cost; self.permanent_upgrades[upgrade_key] = current_level + 1; self.save_game_data()
            else: print("골드가 부족합니다.")
        else: print("최대 레벨에 도달했습니다.")

    def update(self):
        if self.game_state == 'PLAYING':
            self.all_sprites.update(); self.camera.update(self.player); self.manage_enemy_spawning()
            # 투사체 vs 적
            hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, True)
            for enemy, projectiles_hit in hits.items():
                for proj in projectiles_hit:
                    if gem_pos := enemy.take_damage(proj.damage):
                        self.kill_count += 1
                        gem = ExpGem(gem_pos, enemy.exp_drop); self.all_sprites.add(gem); self.exp_gems.add(gem)
            # 플레이어 vs 적
            if not self.player.invincible:
                if colliding_enemies := pygame.sprite.spritecollide(self.player, self.enemies, False):
                    self.player.take_damage(colliding_enemies[0].damage)
            # 플레이어 vs 경험치 보석
            gems_collected = pygame.sprite.spritecollide(self.player, self.exp_gems, True)
            for gem in gems_collected: self.player.gain_exp(gem.exp_value)
            # 스킬 vs 적
            skill_hits = pygame.sprite.groupcollide(self.enemies, self.skill_sprites, False, False)
            for enemy, skills_hit in skill_hits.items():
                now = pygame.time.get_ticks()
                if now - enemy.last_skill_hit_time > enemy.skill_hit_cooldown:
                    enemy.last_skill_hit_time = now
                    if isinstance(skills_hit[0], Bible):
                        damage = self.player.skills['bible']['damage']
                        if gem_pos := enemy.take_damage(damage):
                            self.kill_count += 1
                            gem = ExpGem(gem_pos, enemy.exp_drop); self.all_sprites.add(gem); self.exp_gems.add(gem)

    def draw(self):
        if self.game_state == 'START_MENU': self.draw_start_menu()
        elif self.game_state == 'SHOP': self.draw_shop_screen()
        elif self.game_state == 'CREDITS': self.draw_credits_screen()
        # [수정] PAUSED 상태일 때도 draw_game_screen() 호출
        elif self.game_state in ['PLAYING', 'LEVEL_UP', 'GAME_OVER', 'PAUSED']: self.draw_game_screen()
        pygame.display.flip()
        
    def draw_start_menu(self):
        self.screen.fill(DARK_GREY); title_text = self.title_font.render("Vampire Survivals", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH/2, 150)); self.screen.blit(title_text, title_rect)
        self.start_button.draw(self.screen); self.shop_button.draw(self.screen)
        self.credits_button.draw(self.screen); self.quit_button.draw(self.screen)
        gold_text = self.ui_font.render(f"소유 골드: {self.gold} G", True, YELLOW)
        gold_rect = gold_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 50)); self.screen.blit(gold_text, gold_rect)

    def draw_shop_screen(self):
        self.screen.fill(DARK_GREY)
        title_text = self.header_font.render("상점", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH/2, 80)); self.screen.blit(title_text, title_rect)
        gold_text = self.ui_font.render(f"소유 골드: {self.gold} G", True, YELLOW)
        gold_rect = gold_text.get_rect(center=(SCREEN_WIDTH/2, 140)); self.screen.blit(gold_text, gold_rect)
        self.shop_buttons = {}
        item_width, item_height, item_gap = 800, 80, 20
        start_y = 200
        for i, (key, data) in enumerate(PERMANENT_UPGRADE_DATA.items()):
            y = start_y + i * (item_height + item_gap)
            item_rect = pygame.Rect(SCREEN_WIDTH/2 - item_width/2, y, item_width, item_height)
            pygame.draw.rect(self.screen, UI_BG_COLOR, item_rect, border_radius=10)
            level = self.permanent_upgrades.get(key, 0)
            name_text = self.ui_font.render(f"{data['name']} (Lv.{level}/{data['max_level']})", True, WHITE)
            self.screen.blit(name_text, (item_rect.x + 20, item_rect.y + 10))
            desc_text = self.small_font.render(data['description'], True, LIGHT_GREY)
            self.screen.blit(desc_text, (item_rect.x + 20, item_rect.y + 45))
            cost_text = "MAX" if level >= data['max_level'] else f"{int(data['base_cost'] * (data['cost_increase_factor'] ** level))} G"
            purchase_btn_rect = pygame.Rect(item_rect.right - 140, item_rect.y + 15, 120, 50)
            self.shop_buttons[key] = (purchase_btn_rect, cost_text)
            cost = int(data['base_cost'] * (data['cost_increase_factor'] ** level)) if level < data['max_level'] else float('inf')
            btn_color = UI_OPTION_BG_COLOR if self.gold >= cost else DARK_GREY
            pygame.draw.rect(self.screen, btn_color, purchase_btn_rect, border_radius=10)
            cost_surf = self.ui_font.render(cost_text, True, YELLOW if self.gold >= cost else WHITE)
            cost_rect = cost_surf.get_rect(center=purchase_btn_rect.center); self.screen.blit(cost_surf, cost_rect)
        self.back_button.draw(self.screen)

    def draw_credits_screen(self):
        self.screen.fill(DARK_GREY); credits_text = self.header_font.render("제작진", True, WHITE)
        credits_rect = credits_text.get_rect(center=(SCREEN_WIDTH/2, 150)); self.screen.blit(credits_text, credits_rect)
        creator_text = self.ui_font.render("Created by MHA", True, WHITE)
        creator_rect = creator_text.get_rect(center=(SCREEN_WIDTH/2, 350)); self.screen.blit(creator_text, creator_rect)
        self.back_button.draw(self.screen)

    def draw_game_screen(self):
        self.screen.fill(DARK_GREY)
        self.screen.blit(self.background_image, self.camera.apply(self.background_rect))
        for sprite in self.all_sprites: self.screen.blit(sprite.image, self.camera.apply(sprite.rect))
        self.player.draw_hp_bar(self.screen, self.camera)
        self.draw_game_ui()
        
    def draw_game_ui(self):
        # EXP 바
        exp_bar_width = SCREEN_WIDTH - 40; exp_bar_height = 20
        if self.player.exp_to_next_level > 0: exp_ratio = self.player.exp / self.player.exp_to_next_level
        else: exp_ratio = 1
        current_exp_width = exp_bar_width * exp_ratio
        pygame.draw.rect(self.screen, UI_BG_COLOR, (20, 20, exp_bar_width, exp_bar_height))
        pygame.draw.rect(self.screen, YELLOW, (20, 20, current_exp_width, exp_bar_height))
        pygame.draw.rect(self.screen, UI_BORDER_COLOR, (20, 20, exp_bar_width, exp_bar_height), 3)
        level_text = self.ui_font.render(f"LV {self.player.level}", True, WHITE)
        self.screen.blit(level_text, (30, 45))
        # 타이머
        elapsed_ticks = self.paused_time - self.game_start_time if self.game_state != 'PLAYING' else pygame.time.get_ticks() - self.game_start_time
        elapsed_seconds = elapsed_ticks // 1000; minutes, seconds = divmod(elapsed_seconds, 60)
        timer_text = self.ui_font.render(f"{minutes:02}:{seconds:02}", True, WHITE)
        timer_rect = timer_text.get_rect(center=(SCREEN_WIDTH / 2, 60)); self.screen.blit(timer_text, timer_rect)
        
        # 처치 수 표시
        kill_text = self.ui_font.render(f"처치: {self.kill_count}", True, WHITE)
        kill_rect = kill_text.get_rect(topright=(SCREEN_WIDTH - 30, 45))
        self.screen.blit(kill_text, kill_rect)

        # [수정] 레벨업 / 게임 오버 / 일시정지 창 로직 통합
        if self.game_state == 'LEVEL_UP':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); self.screen.blit(overlay, (0, 0))
            title_text = self.header_font.render("LEVEL UP!", True, YELLOW)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 5)); self.screen.blit(title_text, title_rect)
            self.upgrade_option_rects.clear()
            option_width, option_height = 500, 100
            start_y = SCREEN_HEIGHT / 2 - (option_height * 1.5 + 20)
            for i, option_key in enumerate(self.current_upgrade_options):
                option_data = UPGRADE_DATA[option_key]; y = start_y + i * (option_height + 20)
                rect = pygame.Rect(SCREEN_WIDTH / 2 - option_width / 2, y, option_width, option_height)
                self.upgrade_option_rects.append(rect)
                pygame.draw.rect(self.screen, UI_OPTION_BG_COLOR, rect, border_radius=10)
                pygame.draw.rect(self.screen, UI_BORDER_COLOR, rect, 3, border_radius=10)
                name_text = self.ui_font.render(option_data['name'], True, WHITE)
                name_rect = name_text.get_rect(center=(rect.centerx, rect.centery - 15)); self.screen.blit(name_text, name_rect)
                desc_text = self.upgrade_font.render(option_data['description'], True, LIGHT_GREY)
                desc_rect = desc_text.get_rect(center=(rect.centerx, rect.centery + 15)); self.screen.blit(desc_text, desc_rect)

        elif self.game_state == 'GAME_OVER':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 200)); self.screen.blit(overlay, (0, 0))
            game_over_text = self.header_font.render("GAME OVER", True, RED)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3)); self.screen.blit(game_over_text, game_over_rect)
            # 'R'키 안내 문구 대신 버튼을 그림
            self.restart_button.draw(self.screen)
            self.game_over_main_menu_button.draw(self.screen)

        # [추가] 일시정지 메뉴 그리기
        elif self.game_state == 'PAUSED':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); self.screen.blit(overlay, (0, 0))
            pause_text = self.header_font.render("PAUSED", True, WHITE)
            pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3)); self.screen.blit(pause_text, pause_rect)
            self.resume_button.draw(self.screen)
            self.pause_main_menu_button.draw(self.screen)


if __name__ == '__main__':
    game = Game()
    game.run()