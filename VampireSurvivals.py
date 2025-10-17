import pygame
import random
import math
import json
import os
import sys

# --- 리소스 경로 함수 ---
def resource_path(relative_path):
    """ 실행 파일(exe)로 만들 때 리소스 경로를 올바르게 찾기 위한 함수 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 상수 정의 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 768
WORLD_WIDTH, WORLD_HEIGHT = SCREEN_WIDTH * 5, SCREEN_HEIGHT * 5
FPS, MAX_ENEMIES_ON_SCREEN = 60, 150
SAVE_FILE = 'save_data.json'

# --- 색상 정의 ---
BLACK, WHITE, BLUE, RED, GREEN = (0,0,0), (255,255,255), (0,0,255), (255,0,0), (0,255,0)
YELLOW, CYAN, DARK_GREY, LIGHT_GREY = (255,255,20), (0,255,255), (40,40,40), (100,100,100)
UI_BG_COLOR, UI_BORDER_COLOR, UI_OPTION_BG_COLOR = (50,50,80), (200,200,255), (80,80,120)

# --- 데이터 정의 ---
LEVEL_DATA = [50, 75, 110, 150, 220, 300, 450, 600, 800, 1000, 1250, 1500, 1800, 2200, 2600, 3000]
UPGRADE_DATA = {
    'PLAYER_SPEED':    {'name': '이동 속도 +0.5',         'type': 'passive', 'target': 'speed',            'operation': 'add', 'value': 0.5},
    'MAX_HP':          {'name': '최대 체력 +20',          'type': 'passive', 'target': 'max_hp',           'operation': 'add', 'value': 20},
    'ACQUIRE_BIBLE': {'name': '성스러운 책 획득', 'type': 'acquire', 'skill_key': 'bible'},
    'MAGIC_BULLET_DAMAGE': {'name': '마법탄 공격력 +5', 'type': 'upgrade', 'skill_key': 'magic_bullet', 'target': 'damage', 'operation': 'add', 'value': 5},
    'MAGIC_BULLET_COOLDOWN': {'name': '마법탄 연사 속도 +10%', 'type': 'upgrade', 'skill_key': 'magic_bullet', 'target': 'cooldown', 'operation': 'multiply', 'value': 0.9},
    'MAGIC_BULLET_SPEED': {'name': '마법탄 속도 +1', 'type': 'upgrade', 'skill_key': 'magic_bullet', 'target': 'projectile_speed', 'operation': 'add', 'value': 1},
    'BIBLE_DAMAGE': {'name': '성스러운 책 공격력 +8', 'type': 'upgrade', 'skill_key': 'bible', 'target': 'damage', 'operation': 'add', 'value': 8},
    'BIBLE_COUNT':  {'name': '성스러운 책 개수 +1', 'type': 'upgrade', 'skill_key': 'bible', 'target': 'count', 'operation': 'add', 'value': 1, 'side_effect': 'recreate_sprites'},
    'BIBLE_SPEED':  {'name': '성스러운 책 회전 속도 +20%', 'type': 'upgrade', 'skill_key': 'bible', 'target': 'rotation_speed', 'operation': 'multiply', 'value': 1.2},
}
PERMANENT_UPGRADE_DATA = {
    'MAX_HP':   {'name': '최대 체력 증가', 'base_cost': 100, 'cost_increase_factor': 1.5, 'max_level': 20},
    'EXP_GAIN': {'name': '경험치 획득량 증가', 'base_cost': 150, 'cost_increase_factor': 1.8, 'max_level': 10},
    'GOLD_GAIN':{'name': '골드 획득량 증가', 'base_cost': 150, 'cost_increase_factor': 2.0, 'max_level': 10},
}


# --- 쿼드트리 클래스 ---
class Quadtree:
    def __init__(self, level, bounds):
        self.level, self.bounds = level, pygame.Rect(bounds)
        self.objects, self.nodes = [], [None] * 4
        self.max_objects, self.max_level = 10, 5
    def clear(self):
        self.objects = []
        for i in range(len(self.nodes)):
            if self.nodes[i]: self.nodes[i].clear(); self.nodes[i] = None
    def split(self):
        sub_w, sub_h = self.bounds.width / 2, self.bounds.height / 2
        x, y = self.bounds.x, self.bounds.y
        self.nodes[0] = Quadtree(self.level + 1, (x + sub_w, y, sub_w, sub_h))
        self.nodes[1] = Quadtree(self.level + 1, (x, y, sub_w, sub_h))
        self.nodes[2] = Quadtree(self.level + 1, (x, y + sub_h, sub_w, sub_h))
        self.nodes[3] = Quadtree(self.level + 1, (x + sub_w, y + sub_h, sub_w, sub_h))
    def get_index(self, rect):
        index, cx, cy = -1, self.bounds.centerx, self.bounds.centery
        top_quad, bottom_quad = (rect.bottom < cy), (rect.top > cy)
        if rect.right < cx:
            if top_quad: index = 1
            elif bottom_quad: index = 2
        elif rect.left > cx:
            if top_quad: index = 0
            elif bottom_quad: index = 3
        return index
    def insert(self, obj):
        if self.nodes[0]:
            index = self.get_index(obj.rect)
            if index != -1: self.nodes[index].insert(obj); return
        self.objects.append(obj)
        if len(self.objects) > self.max_objects and self.level < self.max_level:
            if not self.nodes[0]: self.split()
            i = 0
            while i < len(self.objects):
                index = self.get_index(self.objects[i].rect)
                if index != -1: self.nodes[index].insert(self.objects.pop(i))
                else: i += 1
    def retrieve(self, return_objects, rect):
        index = self.get_index(rect)
        if index != -1 and self.nodes[0]: self.nodes[index].retrieve(return_objects, rect)
        return_objects.extend(self.objects)
        return return_objects

# --- 스킬 관련 클래스들 ---
class Skill:
    def __init__(self, player, skill_key):
        self.player, self.game, self.skill_key, self.level = player, player.game, skill_key, 1
    def update(self): raise NotImplementedError
    def level_up(self, upgrade_key):
        self.level += 1
        data = UPGRADE_DATA.get(upgrade_key)
        if not data: return
        if all(k in data for k in ('target', 'operation', 'value')):
            target_attr, op, val = data['target'], data['operation'], data['value']
            current_val = getattr(self, target_attr, 0)
            if op == 'add': setattr(self, target_attr, current_val + val)
            elif op == 'multiply': setattr(self, target_attr, current_val * val)
        if 'side_effect' in data:
            method_name = data['side_effect']
            if hasattr(self, method_name): getattr(self, method_name)()
        self.exp = 0
    def get_upgrade_options(self): raise NotImplementedError
    def on_remove(self): pass

class MagicBulletSkill(Skill):
    def __init__(self, player, skill_key='magic_bullet'):
        super().__init__(player, skill_key)
        self.damage, self.cooldown, self.projectile_speed = 10, 500, 10
        self.last_shot_time = 0
    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.cooldown:
            self.last_shot_time = now
            if target_enemy := self.player.find_closest_enemy():
                Projectile(self.game, self.player.pos, target_enemy, self)
    def get_upgrade_options(self):
        return ['MAGIC_BULLET_DAMAGE', 'MAGIC_BULLET_COOLDOWN', 'MAGIC_BULLET_SPEED']

class BibleSprite(pygame.sprite.Sprite):
    def __init__(self, game, skill_instance):
        super().__init__(); self.game, self.skill = game, skill_instance
        self.image = pygame.Surface((30, 40)); self.image.fill(CYAN); self.rect = self.image.get_rect()
        self.pos, self.angle = pygame.math.Vector2(0, 0), 0
    def update(self):
        self.angle = (self.angle + self.skill.rotation_speed) % 360
        self.pos.x = self.game.player.pos.x + math.cos(math.radians(self.angle)) * self.skill.orbit_radius
        self.pos.y = self.game.player.pos.y + math.sin(math.radians(self.angle)) * self.skill.orbit_radius
        self.rect.center = self.pos

class BibleSkill(Skill):
    def __init__(self, player, skill_key='bible'):
        super().__init__(player, skill_key)
        self.damage, self.count, self.orbit_radius, self.rotation_speed = 15, 1, 100, 2
        self.sprites = pygame.sprite.Group(); self.recreate_sprites()
    def update(self): pass
    def get_upgrade_options(self): return ['BIBLE_DAMAGE', 'BIBLE_COUNT', 'BIBLE_SPEED']
    def recreate_sprites(self):
        for sprite in self.sprites: sprite.kill()
        angle_step = 360 / self.count
        for i in range(self.count):
            sprite = BibleSprite(self.game, self); sprite.angle = i * angle_step
            self.sprites.add(sprite); self.game.all_sprites.add(sprite); self.game.skill_sprites.add(sprite)
    def on_remove(self):
        for sprite in self.sprites: sprite.kill()

SKILL_CLASSES = {'magic_bullet': MagicBulletSkill, 'bible': BibleSkill}

# --- UI 및 기타 클래스들 ---
class Button:
    def __init__(self, x, y, w, h, text, font, bg=UI_OPTION_BG_COLOR, border=UI_BORDER_COLOR):
        self.rect, self.text, self.font = pygame.Rect(x, y, w, h), text, font
        self.bg_color, self.border_color, self.is_hovered = bg, border, False
    def draw(self, surface):
        self.is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = tuple(min(c + 30, 255) for c in self.bg_color) if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, self.border_color, self.rect, 3, border_radius=10)
        text_surf = self.font.render(self.text, True, WHITE)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class Camera:
    def __init__(self, world_w, world_h):
        self.rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.world_width, self.world_height = world_w, world_h
    def apply(self, target_rect): return target_rect.move(self.rect.topleft)
    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        x = min(0, max(-(self.world_width - SCREEN_WIDTH), x))
        y = min(0, max(-(self.world_height - SCREEN_HEIGHT), y))
        self.rect.topleft = (x, y)

class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__(); self.game = game
        self.image = pygame.Surface((50, 50)); self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
    def reset(self):
        hp_bonus = self.game.permanent_upgrades.get('MAX_HP', 0) * 10
        self.base_max_hp = 100 + hp_bonus
        self.exp_gain_multiplier = 1 + (self.game.permanent_upgrades.get('EXP_GAIN', 0) * 0.05)
        self.gold_gain_multiplier = 1 + (self.game.permanent_upgrades.get('GOLD_GAIN', 0) * 0.1)
        self.pos.xy = WORLD_WIDTH / 2, WORLD_HEIGHT / 2
        self.speed, self.max_hp = 5, self.base_max_hp
        self.hp = self.max_hp
        self.level, self.exp, self.exp_to_next_level = 1, 0, LEVEL_DATA[0]
        self.invincible, self.invincible_duration, self.last_hit_time = False, 1000, 0
        
        # [추가] 접촉 피해 관련 속성
        self.contact_damage_cooldown = 1000 # 1초
        self.last_contact_damage_time = 0
        self.is_in_contact_with_enemy = False

        if hasattr(self, 'skills'):
            for skill in self.skills.values(): skill.on_remove()
        self.skills = {}
        self.skills['magic_bullet'] = MagicBulletSkill(self)
    def gain_exp(self, amount):
        self.exp += amount * self.exp_gain_multiplier
        while self.exp >= self.exp_to_next_level: self.level_up()
    def level_up(self):
        self.level += 1; self.exp -= self.exp_to_next_level
        self.exp_to_next_level = LEVEL_DATA[min(self.level - 1, len(LEVEL_DATA) - 1)]
        self.game.generate_upgrades(); self.game.game_state = 'LEVEL_UP'
    def find_closest_enemy(self):
        closest_dist_sq, closest_enemy = float('inf'), None
        if not self.game.enemies: return None
        for enemy in self.game.enemies:
            dist_sq = self.pos.distance_squared_to(enemy.pos)
            if dist_sq < closest_dist_sq: closest_dist_sq, closest_enemy = dist_sq, enemy
        return closest_enemy
    
    # [추가] 모든 체력 감소 및 사망 처리를 담당하는 내부 메소드
    def _apply_damage(self, amount):
        if self.hp > 0:
            self.hp -= amount
            if self.hp <= 0:
                self.hp = 0
                self.game.game_state = 'GAME_OVER'
                self.game.gold += self.game.session_gold
                self.game.save_game_data()

    # [수정] 투사체 등 일회성 피해용 메소드 (무적 부여)
    def take_projectile_damage(self, amount):
        if not self.invincible:
            self._apply_damage(amount)
            if self.hp > 0:
                 self.invincible, self.last_hit_time = True, pygame.time.get_ticks()

    # [추가] 접촉 피해용 메소드 (무적 부여 안함)
    def take_contact_damage(self, amount):
        self._apply_damage(amount)

    def update(self):
        if self.invincible and pygame.time.get_ticks() - self.last_hit_time > self.invincible_duration:
            self.invincible = False
        vel = pygame.math.Vector2(0, 0); keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: vel.x = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: vel.x = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: vel.y = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: vel.y = 1
        if vel.length() > 0: self.pos += vel.normalize() * self.speed
        self.pos.x = max(0, min(self.pos.x, WORLD_WIDTH))
        self.pos.y = max(0, min(self.pos.y, WORLD_HEIGHT))
        self.rect.center = self.pos
        for skill in self.skills.values(): skill.update()
    def draw_hp_bar(self, surface, camera):
        if self.hp > 0:
            bar_w, bar_h = 50, 8
            hp_bar_world = pygame.Rect(self.rect.x, self.rect.y - 15, bar_w, bar_h)
            hp_bar_screen = camera.apply(hp_bar_world)
            pygame.draw.rect(surface, RED, hp_bar_screen)
            pygame.draw.rect(surface, GREEN, (hp_bar_screen.x, hp_bar_screen.y, bar_w * (self.hp / self.max_hp), bar_h))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__(); self.game = game
        self.image = pygame.Surface((40, 40)); self.image.fill(RED); self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(0, 0)
        self.speed, self.max_hp, self.hp = random.randint(1, 2), 20, 20
        self.exp_drop, self.contact_damage, self.skill_hit_cooldown, self.last_skill_hit_time = 15, 5, 500, 0
        self.gold_drop = random.randint(1, 5)
    def reset(self, pos):
        self.pos.xy = pos; self.rect.center = self.pos
        self.hp, self.last_skill_hit_time = self.max_hp, 0
        self.game.all_sprites.add(self); self.game.enemies.add(self)
    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.game.gain_gold(self.gold_drop)
            self.game.return_enemy_to_pool(self)
            return self.rect.center
        return None
    def update(self):
        attraction_vec = self.game.player.pos - self.pos
        separation_vec, close_enemies_count, search_radius = pygame.math.Vector2(0, 0), 0, 40
        search_rect = pygame.Rect(self.pos.x-search_radius, self.pos.y-search_radius, search_radius*2, search_radius*2)
        for other in self.game.quadtree.retrieve([], search_rect):
            if other is not self and self.pos.distance_squared_to(other.pos) < search_radius**2:
                separation_vec += self.pos - other.pos; close_enemies_count += 1
        final_vec = pygame.math.Vector2(0, 0)
        if attraction_vec.length() > search_radius:
            final_vec = attraction_vec.normalize()
            if close_enemies_count > 0 and separation_vec.length() > 0:
                final_vec = final_vec * 0.7 + separation_vec.normalize() * 0.3
        if final_vec.length() > 0: self.pos += final_vec.normalize() * self.speed
        self.rect.center = self.pos

class ExpGem(pygame.sprite.Sprite):
    def __init__(self, pos, exp_value):
        super().__init__()
        self.image = pygame.Surface((15, 15)); self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=pos); self.exp_value = exp_value

class Projectile(pygame.sprite.Sprite):
    def __init__(self, game, pos, target_enemy, source_skill):
        super().__init__(); self.game = game
        self.image = pygame.Surface((10, 10)); self.image.fill(WHITE)
        self.pos = pygame.math.Vector2(pos); self.rect = self.image.get_rect(center=self.pos)
        self.damage = source_skill.damage
        self.lifespan, self.spawn_time = 2000, pygame.time.get_ticks()
        self.vel = (target_enemy.pos - self.pos).normalize() * source_skill.projectile_speed
        self.game.all_sprites.add(self); self.game.projectiles.add(self)
    def update(self):
        self.pos += self.vel; self.rect.center = self.pos
        if pygame.time.get_ticks() - self.spawn_time > self.lifespan: self.kill()

# --- 게임 메인 클래스 ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Vampire Survivors Clone"); self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock(); self.is_running = True
        font_path = resource_path("GmarketSansTTF/GmarketSansTTFMedium.ttf")
        self.title_font = pygame.font.Font(font_path, 96); self.header_font = pygame.font.Font(font_path, 72)
        self.ui_font = pygame.font.Font(font_path, 36); self.upgrade_font = pygame.font.Font(font_path, 28)
        self.game_state, self.current_upgrade_options, self.upgrade_option_rects = 'START_MENU', [], []
        self.load_game_data()
        btn_w, btn_h, btn_gap, btn_x = 250, 60, 20, SCREEN_WIDTH/2 - 125
        self.start_button = Button(btn_x, 300, btn_w, btn_h, '게임 시작', self.ui_font)
        self.shop_button = Button(btn_x, 300 + btn_h + btn_gap, btn_w, btn_h, '상점', self.ui_font)
        self.credits_button = Button(btn_x, 300 + (btn_h + btn_gap)*2, btn_w, btn_h, '제작진', self.ui_font)
        self.quit_button = Button(btn_x, 300 + (btn_h + btn_gap)*3, btn_w, btn_h, '나가기', self.ui_font)
        self.back_button = Button(btn_x, SCREEN_HEIGHT - 100, btn_w, btn_h, '뒤로 가기', self.ui_font)
        self.resume_button = Button(btn_x, 250, btn_w, btn_h, '계속하기', self.ui_font)
        self.main_menu_button = Button(btn_x, 250 + btn_h + btn_gap, btn_w, btn_h, '메인 메뉴', self.ui_font)
        self.quit_from_pause_button = Button(btn_x, 250 + (btn_h + btn_gap)*2, btn_w, btn_h, '게임 종료', self.ui_font)
        
        # [추가] 게임 오버 화면 버튼
        self.restart_button = Button(btn_x, SCREEN_HEIGHT/2 - btn_h, btn_w, btn_h, '다시 시작', self.ui_font)
        self.game_over_main_menu_button = Button(btn_x, SCREEN_HEIGHT/2 + btn_gap, btn_w, btn_h, '메인 메뉴', self.ui_font)
        
        self.shop_buttons = {}

    def load_game_data(self):
        try:
            with open(SAVE_FILE, 'r') as f: data = json.load(f)
            self.gold = data.get('gold', 0); self.permanent_upgrades = data.get('permanent_upgrades', {})
        except (FileNotFoundError, json.JSONDecodeError): self.gold, self.permanent_upgrades = 0, {}
        for key in PERMANENT_UPGRADE_DATA: self.permanent_upgrades.setdefault(key, 0)
    def save_game_data(self):
        with open(SAVE_FILE, 'w') as f: json.dump({'gold': self.gold, 'permanent_upgrades': self.permanent_upgrades}, f, indent=4)
    def gain_gold(self, amount): self.session_gold += int(amount * self.player.gold_gain_multiplier)
    def run(self):
        while self.is_running: self.clock.tick(FPS); self.handle_events(); self.update(); self.draw()
        pygame.quit()
    def new_game(self):
        self.all_sprites = pygame.sprite.Group(); self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group(); self.exp_gems = pygame.sprite.Group()
        self.skill_sprites = pygame.sprite.Group()
        self.enemy_pool = []; self.quadtree = Quadtree(0, (0, 0, WORLD_WIDTH, WORLD_HEIGHT))
        self.spawn_timer, self.spawn_interval = 0, 500
        self.game_state, self.kill_count = 'PLAYING', 0; self.session_gold = 0
        self.game_start_time, self.paused_time = pygame.time.get_ticks(), 0
        if not hasattr(self, 'player'): self.player = Player(self)
        self.player.reset(); self.all_sprites.add(self.player)
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.background_image = self.create_background(); self.background_rect = self.background_image.get_rect()
    def generate_upgrades(self):
        available = []
        acquired_skills = self.player.skills.keys()
        for key, data in UPGRADE_DATA.items():
            if data['type'] == 'passive': available.append(key)
            elif data['type'] == 'acquire' and data['skill_key'] not in acquired_skills: available.append(key)
            elif data['type'] == 'upgrade' and data['skill_key'] in acquired_skills: available.append(key)
        self.current_upgrade_options = random.sample(available, min(3, len(available)))
        self.paused_time = pygame.time.get_ticks()
    def apply_upgrade(self, upgrade_key):
        data = UPGRADE_DATA.get(upgrade_key, {})
        if data['type'] == 'passive':
            target, op, val = data['target'], data['operation'], data['value']
            current_val = getattr(self.player, target)
            if op == 'add': setattr(self.player, target, current_val + val)
            elif op == 'multiply': setattr(self.player, target, current_val * val)
        elif data['type'] == 'acquire':
            key = data['skill_key']
            if key in SKILL_CLASSES: self.player.skills[key] = SKILL_CLASSES[key](self.player)
        elif data['type'] == 'upgrade':
            key = data['skill_key']
            if key in self.player.skills: self.player.skills[key].level_up(upgrade_key)
        self.unpause_game()
    def return_enemy_to_pool(self, enemy): enemy.kill(); self.enemy_pool.append(enemy)
    def manage_enemy_spawning(self):
        self.spawn_timer += self.clock.get_time()
        if self.spawn_timer > self.spawn_interval:
            self.spawn_timer = 0
            if len(self.enemies) < MAX_ENEMIES_ON_SCREEN:
                angle, dist = random.uniform(0, 2*math.pi), random.uniform(700, 800)
                pos = (max(0,min(self.player.pos.x+math.cos(angle)*dist, WORLD_WIDTH)),
                       max(0,min(self.player.pos.y+math.sin(angle)*dist, WORLD_HEIGHT)))
                enemy = self.enemy_pool.pop() if self.enemy_pool else Enemy(self); enemy.reset(pos)
    def create_background(self):
        bg = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT)); bg.fill(DARK_GREY); ts = 100
        for x in range(0, WORLD_WIDTH, ts): pygame.draw.line(bg, LIGHT_GREY, (x, 0), (x, WORLD_HEIGHT))
        for y in range(0, WORLD_HEIGHT, ts): pygame.draw.line(bg, LIGHT_GREY, (0, y), (WORLD_WIDTH, y))
        return bg
    def unpause_game(self):
        pause_duration = pygame.time.get_ticks() - self.paused_time
        self.game_start_time += pause_duration
        self.game_state = 'PLAYING'
    def return_to_main_menu(self):
        self.all_sprites, self.enemies, self.projectiles, self.exp_gems, self.skill_sprites, self.enemy_pool, self.quadtree = (None,)*7
        self.game_state = 'START_MENU'
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            if self.game_state == 'PLAYING':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.game_state = 'PAUSED'; self.paused_time = pygame.time.get_ticks()
            elif self.game_state == 'START_MENU':
                if self.start_button.handle_event(event): self.new_game()
                elif self.shop_button.handle_event(event): self.game_state = 'SHOP'
                elif self.credits_button.handle_event(event): self.game_state = 'CREDITS'
                elif self.quit_button.handle_event(event): self.is_running = False
            elif self.game_state == 'SHOP':
                if self.back_button.handle_event(event): self.game_state = 'START_MENU'
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for key, (rect, _) in self.shop_buttons.items():
                        if rect.collidepoint(event.pos): self.purchase_permanent_upgrade(key)
            elif self.game_state == 'CREDITS':
                if self.back_button.handle_event(event): self.game_state = 'START_MENU'
            elif self.game_state == 'GAME_OVER':
                if self.restart_button.handle_event(event): self.new_game()
                if self.game_over_main_menu_button.handle_event(event): self.return_to_main_menu()
            elif self.game_state == 'LEVEL_UP':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.upgrade_option_rects):
                        if rect.collidepoint(event.pos): self.apply_upgrade(self.current_upgrade_options[i]); break
            elif self.game_state == 'PAUSED':
                if self.resume_button.handle_event(event): self.unpause_game()
                elif self.main_menu_button.handle_event(event): self.return_to_main_menu()
                elif self.quit_from_pause_button.handle_event(event): self.is_running = False
    def purchase_permanent_upgrade(self, key):
        data, level = PERMANENT_UPGRADE_DATA[key], self.permanent_upgrades.get(key, 0)
        if level < data['max_level']:
            cost = int(data['base_cost'] * (data['cost_increase_factor'] ** level))
            if self.gold >= cost: self.gold -= cost; self.permanent_upgrades[key] += 1; self.save_game_data()
    def update(self):
        if self.game_state == 'PLAYING':
            self.quadtree.clear()
            for enemy in self.enemies: self.quadtree.insert(enemy)
            self.all_sprites.update(); self.camera.update(self.player); self.manage_enemy_spawning()
            
            # 투사체와 적 충돌 처리
            hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, True)
            for enemy, projs in hits.items():
                for proj in projs:
                    if gem_pos := enemy.take_damage(proj.damage):
                        self.kill_count += 1; gem = ExpGem(gem_pos, enemy.exp_drop)
                        self.all_sprites.add(gem); self.exp_gems.add(gem)
            
            # [수정] 새로운 접촉 피해 로직
            colliding_enemies = pygame.sprite.spritecollide(self.player, self.enemies, False)
            if colliding_enemies:
                if not self.player.is_in_contact_with_enemy: # 첫 충돌
                    self.player.is_in_contact_with_enemy = True
                    damage = 5 + len(colliding_enemies) # 기본 피해 + 닿은 적 수
                    self.player.take_contact_damage(damage)
                    self.player.last_contact_damage_time = pygame.time.get_ticks()
                else: # 지속 충돌
                    now = pygame.time.get_ticks()
                    if now - self.player.last_contact_damage_time > self.player.contact_damage_cooldown:
                        damage = 5 + len(colliding_enemies)
                        self.player.take_contact_damage(damage)
                        self.player.last_contact_damage_time = now
            else:
                self.player.is_in_contact_with_enemy = False

            # 경험치 젬 획득
            for gem in pygame.sprite.spritecollide(self.player, self.exp_gems, True): self.player.gain_exp(gem.exp_value)
            
            # 스킬과 적 충돌 처리
            skill_hits = pygame.sprite.groupcollide(self.enemies, self.skill_sprites, False, False)
            for enemy, skills in skill_hits.items():
                now = pygame.time.get_ticks()
                if now - enemy.last_skill_hit_time > enemy.skill_hit_cooldown:
                    enemy.last_skill_hit_time = now
                    if isinstance(skills[0], BibleSprite):
                        if gem_pos := enemy.take_damage(skills[0].skill.damage):
                            self.kill_count += 1; gem = ExpGem(gem_pos, enemy.exp_drop)
                            self.all_sprites.add(gem); self.exp_gems.add(gem)
    def draw(self):
        if self.game_state == 'START_MENU': self.draw_start_menu()
        elif self.game_state == 'SHOP': self.draw_shop_screen()
        elif self.game_state == 'CREDITS': self.draw_credits_screen()
        elif self.game_state in ['PLAYING', 'LEVEL_UP', 'GAME_OVER', 'PAUSED']:
            if self.all_sprites: self.draw_game_screen()
            else: self.draw_start_menu() # 게임 종료 후 리소스 정리됐을 때 대비
        pygame.display.flip()
    def draw_start_menu(self):
        self.screen.fill(DARK_GREY)
        title = self.title_font.render("Vampire Survivals", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, 150)))
        self.start_button.draw(self.screen); self.shop_button.draw(self.screen)
        self.credits_button.draw(self.screen); self.quit_button.draw(self.screen)
        gold = self.ui_font.render(f"소유 골드: {self.gold} G", True, YELLOW)
        self.screen.blit(gold, gold.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 50)))
    def draw_shop_screen(self):
        self.screen.fill(DARK_GREY); title = self.header_font.render("상점", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, 80)))
        gold = self.ui_font.render(f"소유 골드: {self.gold} G", True, YELLOW)
        self.screen.blit(gold, gold.get_rect(center=(SCREEN_WIDTH/2, 140)))
        item_w, item_h, item_gap, y = 800, 80, 20, 200
        for i, (key, data) in enumerate(PERMANENT_UPGRADE_DATA.items()):
            rect = pygame.Rect(SCREEN_WIDTH/2-item_w/2, y+i*(item_h+item_gap), item_w, item_h)
            pygame.draw.rect(self.screen, UI_BG_COLOR, rect, border_radius=10)
            level = self.permanent_upgrades.get(key, 0)
            name = self.ui_font.render(f"{data['name']} (Lv.{level}/{data['max_level']})", True, WHITE)
            self.screen.blit(name, (rect.x + 20, rect.y + 10))
            cost = int(data['base_cost'] * (data['cost_increase_factor'] ** level))
            cost_text = "MAX" if level >= data['max_level'] else f"{cost} G"
            btn_rect = pygame.Rect(rect.right - 140, rect.y + 15, 120, 50)
            self.shop_buttons[key] = (btn_rect, cost_text)
            btn_color = UI_OPTION_BG_COLOR if self.gold >= cost and level < data['max_level'] else DARK_GREY
            pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=10)
            cost_surf = self.ui_font.render(cost_text, True, YELLOW if self.gold >= cost else WHITE)
            self.screen.blit(cost_surf, cost_surf.get_rect(center=btn_rect.center))
        self.back_button.draw(self.screen)
    def draw_credits_screen(self):
        self.screen.fill(DARK_GREY); title = self.header_font.render("제작진", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, 150)))
        creator = self.ui_font.render("Created by MHA", True, WHITE)
        self.screen.blit(creator, creator.get_rect(center=(SCREEN_WIDTH/2, 350)))
        self.back_button.draw(self.screen)
    def draw_game_screen(self):
        self.screen.fill(DARK_GREY)
        self.screen.blit(self.background_image, self.camera.apply(self.background_rect))
        for sprite in self.all_sprites: self.screen.blit(sprite.image, self.camera.apply(sprite.rect))
        self.player.draw_hp_bar(self.screen, self.camera); self.draw_game_ui()
    def draw_game_ui(self):
        bar_w, bar_h = SCREEN_WIDTH - 40, 20
        exp_ratio = self.player.exp / self.player.exp_to_next_level if self.player.exp_to_next_level > 0 else 1
        pygame.draw.rect(self.screen, UI_BG_COLOR, (20, 20, bar_w, bar_h))
        pygame.draw.rect(self.screen, YELLOW, (20, 20, bar_w * exp_ratio, bar_h))
        pygame.draw.rect(self.screen, UI_BORDER_COLOR, (20, 20, bar_w, bar_h), 3)
        self.screen.blit(self.ui_font.render(f"LV {self.player.level}", True, WHITE), (30, 45))
        elapsed_ticks = (self.paused_time if self.game_state not in ['PLAYING'] else pygame.time.get_ticks()) - self.game_start_time
        mins, secs = divmod(elapsed_ticks // 1000, 60)
        timer = self.ui_font.render(f"{mins:02}:{secs:02}", True, WHITE)
        self.screen.blit(timer, timer.get_rect(center=(SCREEN_WIDTH / 2, 60)))
        kill_text = f"처치: {self.kill_count} | 골드: {self.session_gold} G"
        kills = self.ui_font.render(kill_text, True, WHITE)
        self.screen.blit(kills, kills.get_rect(topright=(SCREEN_WIDTH - 30, 45)))
        if self.game_state == 'LEVEL_UP':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180))
            self.screen.blit(overlay, (0, 0)); title = self.header_font.render("LEVEL UP!", True, YELLOW)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/5)))
            self.upgrade_option_rects.clear(); opt_w, opt_h = 500, 100
            start_y = SCREEN_HEIGHT/2 - (opt_h*1.5 + 20)
            for i, key in enumerate(self.current_upgrade_options):
                data, rect = UPGRADE_DATA[key], pygame.Rect(SCREEN_WIDTH/2 - opt_w/2, start_y + i * (opt_h + 20), opt_w, opt_h)
                self.upgrade_option_rects.append(rect)
                pygame.draw.rect(self.screen, UI_OPTION_BG_COLOR, rect, border_radius=10)
                pygame.draw.rect(self.screen, UI_BORDER_COLOR, rect, 3, border_radius=10)
                name = self.ui_font.render(data['name'], True, WHITE)
                self.screen.blit(name, name.get_rect(center=rect.center))
        elif self.game_state == 'GAME_OVER':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,200))
            self.screen.blit(overlay, (0, 0)); title = self.header_font.render("GAME OVER", True, RED)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/3)))
            self.restart_button.draw(self.screen)
            self.game_over_main_menu_button.draw(self.screen)
        elif self.game_state == 'PAUSED':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180))
            self.screen.blit(overlay, (0, 0)); title = self.header_font.render("PAUSED", True, WHITE)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH/2, 150)))
            self.resume_button.draw(self.screen); self.main_menu_button.draw(self.screen)
            self.quit_from_pause_button.draw(self.screen)

if __name__ == '__main__':
    game = Game()
    game.run()

