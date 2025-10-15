import pygame
import random
import math

# --- Pygame 초기화 ---
pygame.init()

# --- 화면 설정 ---
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("갤러그 스타일 슈팅 게임 by Gemini")

# --- 색상 정의 ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 180, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)

# --- 배경 별 설정 ---
stars = []
for _ in range(150):
    x = random.randrange(0, screen_width)
    y = random.randrange(0, screen_height)
    size = random.randint(1, 2)
    speed = random.randint(1, 4)
    stars.append({'x': x, 'y': y, 'size': size, 'speed': speed})

# --- 플레이어 설정 ---
player_width = 50
player_height = 40
player_rect = pygame.Rect((screen_width - player_width) / 2, screen_height - player_height - 20, player_width, player_height)
player_speed = 7
player_move_x = 0
player_move_y = 0

# --- 적(Enemy) 설정 ---
enemy_width = 40
enemy_height = 40
enemies = []
max_enemies = 10
enemy_spawn_timer = 0
enemy_spawn_delay = 30 # 숫자가 작을수록 더 빨리 스폰됨
enemy_fire_rate = 80 # 숫자가 낮을수록 더 자주 발사

# --- 총알(Bullet) 설정 ---
player_bullet_speed = 15
player_bullets = []
enemy_bullet_speed = 6
enemy_bullets = [] # 이제 총알은 딕셔너리 {'rect': rect, 'vx': vx, 'vy': vy} 형태로 관리

# --- 점수 설정 ---
score_value = 0
font = pygame.font.Font(None, 36)

def spawn_enemy():
    """새로운 적을 화면 상단에 생성합니다."""
    x = random.randint(0, screen_width - enemy_width)
    y = random.randint(-100, -50)
    speed_y = random.randint(2, 4)
    enemy_rect = pygame.Rect(x, y, enemy_width, enemy_height)
    enemies.append({'rect': enemy_rect, 'speed_y': speed_y})

def show_score():
    """화면에 점수를 표시합니다."""
    score_text = font.render(f"Score: {score_value}", True, WHITE)
    screen.blit(score_text, (10, 10))

def draw_player(rect):
    """플레이어를 그립니다."""
    pygame.draw.polygon(screen, GREEN, [
        (rect.centerx, rect.top),
        (rect.left, rect.bottom),
        (rect.right, rect.bottom)
    ])

def draw_enemy(rect):
    """적을 그립니다."""
    pygame.draw.rect(screen, RED, rect)

def draw_stars():
    """배경의 별들을 그립니다."""
    for star in stars:
        pygame.draw.circle(screen, GRAY, (star['x'], star['y']), star['size'])

def update_stars(scroll):
    """별들의 위치를 업데이트하여 스크롤 효과를 줍니다."""
    for star in stars:
        star['y'] += star['speed'] + scroll
        if star['y'] > screen_height:
            star['y'] = random.randrange(-10, 0)
            star['x'] = random.randrange(0, screen_width)

def game_over_text():
    """게임 오버 텍스트를 표시합니다."""
    over_font = pygame.font.Font(None, 72)
    over_text = over_font.render("GAME OVER", True, WHITE)
    text_rect = over_text.get_rect(center=(screen_width / 2, screen_height / 2))
    screen.blit(over_text, text_rect)
    
    restart_font = pygame.font.Font(None, 36)
    restart_text = restart_font.render("Press 'R' to Restart", True, WHITE)
    restart_rect = restart_text.get_rect(center=(screen_width / 2, screen_height / 2 + 50))
    screen.blit(restart_text, restart_rect)

def reset_game():
    """게임을 초기 상태로 리셋합니다."""
    global score_value, game_over, player_move_x, player_move_y
    score_value = 0
    game_over = False
    enemies.clear()
    player_bullets.clear()
    enemy_bullets.clear()
    player_rect.centerx = screen_width / 2
    player_rect.bottom = screen_height - 20
    player_move_x = 0
    player_move_y = 0


# --- 게임 루프 ---
running = True
game_over = False
clock = pygame.time.Clock()

while running:
    clock.tick(60) # FPS 60으로 설정
    
    # --- 이벤트 처리 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if not game_over:
                if event.key == pygame.K_LEFT: player_move_x = -player_speed
                if event.key == pygame.K_RIGHT: player_move_x = player_speed
                if event.key == pygame.K_UP: player_move_y = -player_speed
                if event.key == pygame.K_DOWN: player_move_y = player_speed
                if event.key == pygame.K_SPACE:
                    bullet_rect = pygame.Rect(player_rect.centerx - 2, player_rect.top, 5, 15)
                    player_bullets.append(bullet_rect)
            else:
                if event.key == pygame.K_r:
                    reset_game()

        if event.type == pygame.KEYUP:
            if event.key in [pygame.K_LEFT, pygame.K_RIGHT]: player_move_x = 0
            if event.key in [pygame.K_UP, pygame.K_DOWN]: player_move_y = 0

    # --- 게임 로직 (게임 오버가 아닐 때만 실행) ---
    if not game_over:
        # 위/아래 이동에 따른 스크롤 값 계산 (위로 가면(-), 스크롤은(+) / 아래로 가면(+), 스크롤은(-))
        scroll = -player_move_y

        # 배경 별 위치 업데이트
        update_stars(scroll)

        # 플레이어 위치 업데이트 (수평 이동만 적용)
        player_rect.x += player_move_x
        player_rect.left = max(0, player_rect.left)
        player_rect.right = min(screen_width, player_rect.right)

        # 적 생성
        if len(enemies) < max_enemies:
            enemy_spawn_timer += 1
            if enemy_spawn_timer >= enemy_spawn_delay:
                spawn_enemy()
                enemy_spawn_timer = 0
        
        # 적 이동 및 공격
        for enemy in enemies[:]:
            enemy['rect'].y += enemy['speed_y'] + scroll
            if enemy['rect'].top > screen_height:
                enemies.remove(enemy)

            # 무작위로 적 총알 발사
            if random.randint(1, enemy_fire_rate) == 1:
                vx, vy = 0, enemy_bullet_speed
                # 20% 확률로 플레이어를 조준하는 탄 발사
                if random.randint(1, 5) == 1:
                    dx = player_rect.centerx - enemy['rect'].centerx
                    dy = player_rect.centery - enemy['rect'].centery
                    dist = math.hypot(dx, dy)
                    if dist > 0:
                        vx = (dx / dist) * enemy_bullet_speed
                        vy = (dy / dist) * enemy_bullet_speed

                bullet_rect = pygame.Rect(enemy['rect'].centerx - 2, enemy['rect'].bottom, 5, 10)
                enemy_bullets.append({'rect': bullet_rect, 'vx': vx, 'vy': vy})

        # 플레이어 총알 이동 (스크롤에 영향받지 않음)
        player_bullets = [b for b in player_bullets if b.bottom > 0]
        for bullet in player_bullets:
            bullet.y -= player_bullet_speed

        # 적 총알 이동
        enemy_bullets_on_screen = []
        for bullet in enemy_bullets:
            bullet['rect'].x += bullet['vx']
            bullet['rect'].y += bullet['vy'] + scroll
            if bullet['rect'].top < screen_height and bullet['rect'].bottom > 0:
                 enemy_bullets_on_screen.append(bullet)
        enemy_bullets = enemy_bullets_on_screen

        # --- 충돌 감지 ---
        # 플레이어 총알 vs 적
        for bullet in player_bullets[:]:
            for enemy in enemies[:]:
                if bullet.colliderect(enemy['rect']):
                    player_bullets.remove(bullet)
                    enemies.remove(enemy)
                    score_value += 10
                    break
        
        # 적 총알 vs 플레이어
        for bullet in enemy_bullets:
            if player_rect.colliderect(bullet['rect']):
                game_over = True
                break

    # --- 렌더링 (화면에 그리기) ---
    screen.fill(BLACK)
    draw_stars()
    
    if not game_over:
        draw_player(player_rect)
        for enemy in enemies:
            draw_enemy(enemy['rect'])
        for bullet in player_bullets:
            pygame.draw.rect(screen, BLUE, bullet)
        for bullet in enemy_bullets:
            pygame.draw.rect(screen, YELLOW, bullet['rect'])
    
    show_score()

    if game_over:
        game_over_text()

    pygame.display.update()

pygame.quit()


