import pygame    
import random    
import sys       

pygame.init()          
pygame.mixer.init()    
pygame.joystick.init() 


joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
for joy in joysticks:
    joy.init()

WIDTH, HEIGHT = 1900, 1000 
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Death Track Dash") 

THEME_COLOR = (255, 165, 0) 
DARK_GREY = (30, 30, 30)    

PLAY_AREA_WIDTH = 575 
CENTER_X = WIDTH // 2 

lanes = [CENTER_X - 190, CENTER_X, CENTER_X + 190] 


start_sound = pygame.mixer.Sound("sound/Starting_sound.mp3") 
zombie_sound = pygame.mixer.Sound("sound/Zombie.mp3")         
run_sound = pygame.mixer.Sound("sound/run.mp3")               
shout_sound = pygame.mixer.Sound("sound/shouting.mp3")       
jump_sound = pygame.mixer.Sound("sound/fall.mp3")            
shooting_sound=pygame.mixer.Sound("sound/realistic.mp3")

bg_image = pygame.image.load("assets/back.png").convert() 
bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT)) 
bg_flipped = pygame.transform.flip(bg_image, False, True) 
    

player_size = (80, 110) 
player_frames = [
        
        pygame.transform.scale(pygame.image.load("assets/boy11.png").convert_alpha(), player_size),
        pygame.transform.scale(pygame.image.load("assets/boy22.png").convert_alpha(), player_size)
    ]
    

player_fire_img = pygame.transform.scale(pygame.image.load("assets/boy3(2).png").convert_alpha(), player_size)
    

zombie_size = (90, 120)
zombie_frames = [
        pygame.transform.scale(pygame.image.load("assets/zombe.png").convert_alpha(), zombie_size),
        pygame.transform.scale(pygame.image.load("assets/zombe1.png").convert_alpha(), zombie_size)
    ]

front_zombie_frames = [
        pygame.transform.scale(pygame.image.load("assets/zz.png").convert_alpha(), zombie_size),
        pygame.transform.scale(pygame.image.load("assets/zz1.png").convert_alpha(), zombie_size)
    ]


ROADBLOCK_IMG = pygame.transform.scale(pygame.image.load("assets/roadblock(2).png").convert_alpha(), (120, 80)) 
COIN_IMG = pygame.transform.scale(pygame.image.load("assets/coin.png").convert_alpha(), (70, 70)) 
HEART_IMG = pygame.image.load("assets/h.png").convert_alpha() 
HEART_UI = pygame.transform.scale(HEART_IMG, (50, 50)) 
ENERGY_IMG = pygame.transform.scale(pygame.image.load("assets/energe.png").convert_alpha(), (70, 70))
CAPSULE_IMG = pygame.transform.scale(pygame.image.load("assets/K.png").convert_alpha(), (70, 70)) 
    

TRAIN_W, TRAIN_H = 140, 350 
train_images = [pygame.transform.scale(pygame.image.load(f"assets/trainn{i}.png").convert_alpha(), (TRAIN_W, TRAIN_H)) for i in [1, 2, 3]]


font_ui = pygame.font.SysFont("Arial", 40, bold=True)    
font_btn = pygame.font.SysFont("Arial", 50, bold=True)   
font_small = pygame.font.SysFont("Arial", 25, bold=True) 
font_large = pygame.font.SysFont("Arial", 100, bold=True)


class FrontZombie:
    def __init__(self, lane_idx):
        self.lane = lane_idx 
        self.x = lanes[lane_idx] - 45 
        self.y = -150 
        self.frame_idx = 0 
        self.rect = pygame.Rect(self.x, self.y, 90, 120) 

    def update(self, current_speed):
        self.y += current_speed 
        self.rect.y = self.y 
        self.frame_idx = (self.frame_idx + 0.1) % len(front_zombie_frames) 
        return self.y < HEIGHT + 100
    def draw(self, surface):
        img = front_zombie_frames[int(self.frame_idx)] 
        surface.blit(img, (self.rect.x, self.rect.y)) 


class SmartJumpingZombie:
    def __init__(self, start_lane, y_pos):
        self.lane = start_lane 
        self.x = lanes[start_lane] - 45
        self.y_base = y_pos
        self.target_y_base = HEIGHT - 100 
        self.y_offset = 0 
        self.frame_idx = 0
        self.speed = 0.12 
        self.is_jumping = False
        self.is_alive = True 
        self.lane_change_cooldown = 0 

    def update(self, obstacles, scroll_speed, is_boosted):
        if not self.is_alive: return 
        self.frame_idx = (self.frame_idx + 0.1) % len(zombie_frames) 
        
        
        if is_boosted:
            if self.y_base < HEIGHT + 150: self.y_base += 6
        else:
            
            if self.y_base > self.target_y_base: self.y_base -= 2
            elif self.y_base < self.target_y_base: self.y_base += 2

        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown -= 1 
        
        
        collision_imminent = False
        for obj in obstacles:
            if obj["lane"] == self.lane:
                
                if self.y_base - 250 < obj["rect"].y < self.y_base:
                    collision_imminent = True
                    break
        
        
        if collision_imminent and self.lane_change_cooldown == 0:
            possible_lanes = [0, 1, 2]
            random.shuffle(possible_lanes) 
            for candidate in possible_lanes:
                if candidate != self.lane:
                    safe = True
                    for obj in obstacles:
                        
                        if obj["lane"] == candidate and self.y_base - 250 < obj["rect"].y < self.y_base:
                            safe = False
                            break
                    if safe:
                        self.lane = candidate 
                        self.lane_change_cooldown = 30 
                        break

        
        self.x += ((lanes[self.lane] - 45) - self.x) * self.speed

    def draw(self, surface): 
        if self.is_alive: 
            surface.blit(zombie_frames[int(self.frame_idx)], (self.x, self.y_base + self.y_offset))


game_state = "MENU"
last_score, last_coins = 0, 0 
current_level, current_lane = 1, 1 
lives, score, coins_collected = 3, 0, 0 
scroll_speed = 5.0 
boost_timer, shield_timer = 0, 0 
is_boosted = False 
is_firing = False 
fire_duration = 0 
bullets = [] 
front_zombies = [] 
front_spawn_timer = 0 
menu_selection = 0 
stick_cooldown = 0


player_x, player_base_y, player_y_offset = lanes[1], HEIGHT - 350, 0
is_jumping, jump_velocity, gravity = False, -20, 0.9 
player_frame_idx, invincible_timer = 0, 0 
zombies, obstacles, items = [], [], [] 
spawn_timer, bg_y, game_over = 0, 0, False 


def reset_game(level):
    global game_state, current_level, current_lane, lives, score, coins_collected, scroll_speed, \
           boost_timer, shield_timer, is_boosted, player_x, player_y_offset, is_jumping, \
           invincible_timer, zombies, obstacles, items, spawn_timer, game_over, is_firing, bullets, fire_duration, \
           front_zombies, front_spawn_timer
    start_sound.stop() 
    zombie_sound.set_volume(0.5); zombie_sound.play(-1) 
    run_sound.play(-1) 
    game_state, current_level, current_lane, lives, score, coins_collected = "PLAYING", level, 1, 3, 0, 0
    scroll_speed, boost_timer, shield_timer, is_boosted, player_y_offset, is_jumping, invincible_timer = 5.0, 0, 0, False, 0, False, 0
    is_firing, fire_duration, bullets, front_zombies, front_spawn_timer = False, 0, [], [], 0
    player_x, obstacles, items, spawn_timer, game_over = lanes[current_lane], [], [], 0, False
    
    if level == 1:
        zombies = [SmartJumpingZombie(0, HEIGHT + 100)]
    else:
        zombies = [SmartJumpingZombie(0, HEIGHT + 100), SmartJumpingZombie(2, HEIGHT + 100)]


def spawn_everything():
    lanes_pool = [0, 1, 2]; random.shuffle(lanes_pool)
    num_to_spawn = 1 if random.random() > 0.3 else 2 
    for i in range(num_to_spawn):
        choice = random.choice(["train", "roadblock"])
        lane_idx = lanes_pool[i]
        if choice == "train":
        
            obstacles.append({"type": "train", "lane": lane_idx, "rect": pygame.Rect(lanes[lane_idx]-70, -TRAIN_H, TRAIN_W, TRAIN_H), "img": random.choice(train_images)})
        else:
        
            obstacles.append({"type": "roadblock", "lane": lane_idx, "rect": pygame.Rect(lanes[lane_idx]-60, -150, 120, 80)})

    
    lane = random.choice([0, 1, 2])
    rv = random.random()
    if rv < 0.05 and scroll_speed > 12.0: items.append({"type": "capsule", "rect": pygame.Rect(lanes[lane]-35, -200, 70, 70)})
    elif rv < 0.10: items.append({"type": "energy", "rect": pygame.Rect(lanes[lane]-35, -200, 70, 70)}) 
    elif rv < 0.15 and lives < 3: items.append({"type": "heart", "rect": pygame.Rect(lanes[lane]-40, -200, 80, 80)}) 
    elif rv < 0.40: items.append({"type": "coin", "rect": pygame.Rect(lanes[lane]-35, -200, 70, 70)}) 

start_sound.play(-1) 
clock = pygame.time.Clock() 


while True:
    mouse_pos = pygame.mouse.get_pos() 
    if stick_cooldown > 0: stick_cooldown -= 1 

    for event in pygame.event.get(): 
        if event.type == pygame.QUIT: 
            pygame.quit(); sys.exit() 
        
        
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0: 
                if game_state == "PLAYING" and not game_over and not is_jumping:
                    is_jumping = True; jump_velocity = -20; jump_sound.play()
                elif game_state == "MENU":
                    if menu_selection == 0: reset_game(1)
                    elif menu_selection == 1: reset_game(2)
                    elif menu_selection == 2: pygame.quit(); sys.exit()
                elif game_state == "PAUSED":
                    if menu_selection == 0: 
                        game_state = "PLAYING"; zombie_sound.set_volume(0.5); run_sound.play(-1)
                    else:
                        last_score, last_coins = score // 10, coins_collected
                        game_state = "MENU"; zombie_sound.stop(); run_sound.stop(); start_sound.play(-1)
            
            
            if event.button == 2 and game_state == "PLAYING" and current_level == 2:
                is_firing = True; fire_duration = 10 ; shooting_sound.play()
                bullets.append(pygame.Rect(player_x + 35, player_base_y + player_y_offset, 15, 30))

            if event.button == 1: 
                if game_state == "PLAYING":
                    game_state = "PAUSED"; zombie_sound.set_volume(1.0); run_sound.stop(); menu_selection = 0
                elif game_over:
                    last_score, last_coins = score // 10, coins_collected
                    game_state = "MENU"; start_sound.play(-1); zombie_sound.stop()

            if event.button == 3 and game_over: 
                reset_game(current_level)

        
        if event.type == pygame.JOYAXISMOTION and stick_cooldown == 0:
            if event.axis == 0: 
                if event.value > 0.5: 
                    if game_state == "PLAYING" and current_lane < 2: current_lane += 1; stick_cooldown = 15
                elif event.value < -0.5: 
                    if game_state == "PLAYING" and current_lane > 0: current_lane -= 1; stick_cooldown = 15
            if event.axis == 1: 
                if event.value > 0.5: 
                    menu_selection = (menu_selection + 1) % (3 if game_state == "MENU" else 2)
                    stick_cooldown = 15
                elif event.value < -0.5: 
                    menu_selection = (menu_selection - 1) % (3 if game_state == "MENU" else 2)
                    stick_cooldown = 15

        
        if event.type == pygame.KEYDOWN:
            if game_state == "PLAYING" and not game_over:
                if current_level == 2 and event.key == pygame.K_SPACE: 
                    is_firing = True; fire_duration = 10 ; shooting_sound.play()
                    bullets.append(pygame.Rect(player_x + 35, player_base_y + player_y_offset, 15, 30))
                if event.key == pygame.K_LEFT and current_lane > 0: current_lane -= 1 
                if event.key == pygame.K_RIGHT and current_lane < 2: current_lane += 1 
                if (event.key in [pygame.K_UP]) and not is_jumping:
                    is_jumping = True; jump_velocity = -20; jump_sound.play()
                if event.key == event.key == pygame.K_p: 
                    game_state = "PAUSED"; zombie_sound.set_volume(1.0); run_sound.stop(); menu_selection = 0
            elif game_over:
                if event.key == pygame.K_r: reset_game(current_level) 
                if event.key == pygame.K_q:
                    last_score, last_coins = score // 10, coins_collected
                    game_state = "MENU"; start_sound.play(-1); zombie_sound.stop()

        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "MENU":
                
                btn_w, btn_h = 450, 90
                for i in range(3):
                    rect = pygame.Rect(WIDTH//2 - btn_w//2, 450 + (i * 120), btn_w, btn_h)
                    if rect.collidepoint(mouse_pos):
                        if i == 0: reset_game(1)
                        elif i == 1: reset_game(2)
                        elif i == 2: pygame.quit(); sys.exit()
            elif game_state == "PAUSED":
                for i in range(2):
                    b_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 10 + (i*120), 400, 80)
                    if b_rect.collidepoint(mouse_pos):
                        if i == 0: 
                            game_state = "PLAYING"; zombie_sound.set_volume(0.5); run_sound.play(-1)
                        elif i == 1: 
                            last_score, last_coins = score // 10, coins_collected
                            game_state = "MENU"; zombie_sound.stop(); run_sound.stop(); start_sound.play(-1)

    
    if game_state == "MENU":
        
        screen.blit(bg_image, (0, 0)) 
        title_surf = font_large.render("Death TRACK DASH", True, THEME_COLOR)
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH//2, 200))) 
        
        
        if last_score > 0 or last_coins > 0:
            last_stat_text = f"LAST RUN - SCORE: {last_score} | COINS: {last_coins}"
            last_stat_surf = font_ui.render(last_stat_text, True, (255, 255, 255))
            stat_rect = last_stat_surf.get_rect(center=(WIDTH//2, 320))
            screen.blit(last_stat_surf, stat_rect)


        ctrl_hint = font_small.render("Controller: Stick to Move | X to Select ", True, (200, 200, 200))
        screen.blit(ctrl_hint, ctrl_hint.get_rect(center=(WIDTH//2, HEIGHT - 80)))

        
        menu_options = ["LEVEL 1", "LEVEL 2", "EXIT"]
        for i, text in enumerate(menu_options):
            btn_rect = pygame.Rect(WIDTH//2 - 225, 450 + (i * 120), 450, 90)
            is_selected = (menu_selection == i) or btn_rect.collidepoint(mouse_pos)
            color = (80, 80, 80) if is_selected else (30, 30, 30) 
            pygame.draw.rect(screen, color, btn_rect, border_radius=25) 
            pygame.draw.rect(screen, THEME_COLOR if is_selected else (100, 100, 100), btn_rect, 4, border_radius=25) 
            screen.blit(font_btn.render(text, True, (255, 255, 255)), font_btn.render(text, True, (255, 255, 255)).get_rect(center=btn_rect.center))

    elif game_state == "PLAYING" or game_state == "PAUSED":
        
        if game_state == "PLAYING" and not game_over:
            
            if not is_jumping:
                if not pygame.mixer.Channel(1).get_busy(): pygame.mixer.Channel(1).play(run_sound)
            else: run_sound.stop()

            
            effective_speed = scroll_speed * 1.4 if boost_timer > 0 else scroll_speed
            if boost_timer > 0: boost_timer -= 1
            if shield_timer > 0: shield_timer -= 1 
            scroll_speed = min(30.0, scroll_speed + 0.003) 
            score += 2 if boost_timer > 0 else 1 
            bg_y = (bg_y + effective_speed) % (HEIGHT * 2) 
            
            
            player_x += ((lanes[current_lane] - 40) - player_x) * 0.22

            if is_jumping:
                player_y_offset += jump_velocity 
                jump_velocity += gravity 
                if player_y_offset >= 0: 
                    player_y_offset = 0; is_jumping = False
            
            
            if is_firing:
                fire_duration -= 1
                if fire_duration <= 0: is_firing = False

            
            if current_level == 2:
                front_spawn_timer += 1
                if front_spawn_timer > 100: 
                    possible_lanes = [0, 1, 2]
                
                    for obj in obstacles:
                        if obj["type"] == "train" and obj["rect"].y < 250:
                            if obj["lane"] in possible_lanes: possible_lanes.remove(obj["lane"])
                    if possible_lanes: front_zombies.append(FrontZombie(random.choice(possible_lanes)))
                    front_spawn_timer = 0
                
            
                player_hitbox = pygame.Rect(player_x + 25, player_base_y + player_y_offset + 30, 30, 50)
                for fz in front_zombies[:]:
                    if not fz.update(effective_speed): front_zombies.remove(fz); continue
                    if player_hitbox.colliderect(fz.rect):
                        if shield_timer <= 0 and invincible_timer == 0:
                            lives -= 1; invincible_timer = 90; shout_sound.play()
                            front_zombies.remove(fz)
                            if lives <= 0: game_over = True; run_sound.stop(); start_sound.play(-1)
                        elif shield_timer > 0: 
                            front_zombies.remove(fz)

            
            for b in bullets[:]:
                b.y -= 20 
                hit_detected = False
            
                for fz in front_zombies[:]:
                    if b.colliderect(fz.rect): front_zombies.remove(fz); hit_detected = True; break
                
                if not hit_detected:
                    for z in zombies:
                        z_rect = pygame.Rect(z.x, z.y_base + z.y_offset, 90, 120)
                        if b.colliderect(z_rect) and z.is_alive: z.is_alive = False; hit_detected = True; break
                if hit_detected or b.y < -50:
                    if b in bullets: bullets.remove(b)

            
            player_frame_idx = (player_frame_idx + 0.15) % len(player_frames)
            if invincible_timer > 0: invincible_timer -= 1
            spawn_timer += 1
            
            if spawn_timer > max(20, 90 - int(scroll_speed * 2.5)): spawn_everything(); spawn_timer = 0
            
            
            for z in zombies: z.update(obstacles, effective_speed, boost_timer > 0)

            
            player_hitbox = pygame.Rect(player_x + 25, player_base_y + player_y_offset + 30, 30, 50)
            for obj in obstacles[:]:
                obj["rect"].y += effective_speed
                if player_hitbox.colliderect(obj["rect"].inflate(-50, -50)): 
                    if shield_timer <= 0:
                        if obj["type"] == "train" and not (is_jumping and player_y_offset < -280):
                            
                            game_over = True; shout_sound.play(); run_sound.stop(); start_sound.play(-1)
                        elif obj["type"] == "roadblock" and invincible_timer == 0 and not (is_jumping and player_y_offset < -60):
                            
                            lives -= 1; invincible_timer = 60; shout_sound.play()
                            if lives <= 0: game_over = True; run_sound.stop(); start_sound.play(-1)
                if obj["rect"].y > HEIGHT: obstacles.remove(obj) 

        
            for item in items[:]:
                item["rect"].y += effective_speed
                if player_hitbox.colliderect(item["rect"]):
                    if item["type"] == "coin": coins_collected += 1
                    elif item["type"] == "heart" and lives < 3: lives += 1
                    elif item["type"] == "energy": boost_timer = 300
                    elif item["type"] == "capsule": shield_timer = 600
                    items.remove(item)
                elif item["rect"].y > HEIGHT: items.remove(item)

        
        
        
        screen.blit(bg_image, (0, (bg_y % (HEIGHT * 2)) - HEIGHT * 2))
        screen.blit(bg_flipped, (0, (bg_y % (HEIGHT * 2)) - HEIGHT))
        screen.blit(bg_image, (0, bg_y % (HEIGHT * 2)))
    
    
        for obj in obstacles: screen.blit(obj["img"] if obj["type"]=="train" else ROADBLOCK_IMG, obj["rect"])
        
        
        for item in items: 
            img = pygame.transform.scale(HEART_IMG, (70, 70)) if item["type"] == "heart" else (CAPSULE_IMG if item["type"] == "capsule" else (COIN_IMG if item["type"] == "coin" else ENERGY_IMG))
            screen.blit(img, item["rect"])
            
        
        for z in zombies: z.draw(screen)
        for fz in front_zombies: fz.draw(screen) 
        for b in bullets: pygame.draw.rect(screen, (255, 255, 0), b) 

        
        if shield_timer > 0:
            s = pygame.Surface((120, 150), pygame.SRCALPHA); pygame.draw.ellipse(s, (255, 255, 0, 100), (0, 0, 120, 150), 10)
            screen.blit(s, (player_x - 20, player_base_y + player_y_offset - 20))

        
        if invincible_timer % 10 < 5:
            if is_firing and current_level == 2: screen.blit(player_fire_img, (player_x, player_base_y + player_y_offset))
            else: screen.blit(player_frames[int(player_frame_idx)], (player_x, player_base_y + player_y_offset))
        
        
        for i in range(lives): screen.blit(HEART_UI, (50 + (i * 65), 30)) 
        screen.blit(font_ui.render(f"SCORE: {score // 10}", True, THEME_COLOR), (50, 100))
        screen.blit(font_ui.render(f"COINS: {coins_collected}", True, THEME_COLOR), (50, 160))
        
        
        if game_state == "PAUSED":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180)) 
            screen.blit(overlay, (0,0))
            panel_w, panel_h = 600, 450
            panel = pygame.Rect(WIDTH//2 - panel_w//2, HEIGHT//2 - panel_h//2, panel_w, panel_h)
            pygame.draw.rect(screen, (10, 10, 10), panel.move(10, 10), border_radius=30) 
            pygame.draw.rect(screen, (40, 40, 40), panel, border_radius=30) 
            pygame.draw.rect(screen, THEME_COLOR, panel, 4, border_radius=30)
            p_title = font_large.render("PAUSED", True, THEME_COLOR)
            screen.blit(p_title, p_title.get_rect(center=(WIDTH//2, HEIGHT//2 - 130)))
            for i, txt in enumerate(["RESUME", "MAIN MENU"]):
                b_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 + (i*110), 400, 85)
                is_sel = (menu_selection == i) or b_rect.collidepoint(mouse_pos)
                b_color = (60, 60, 60) if is_sel else (30, 30, 30)
                pygame.draw.rect(screen, b_color, b_rect, border_radius=20)
                screen.blit(font_btn.render(txt, True, (255, 255, 255)), font_btn.render(txt, True, (255, 255, 255)).get_rect(center=b_rect.center))

    
        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0,0))
            panel_rect = pygame.Rect(WIDTH//2 - 350, HEIGHT//2 - 250, 700, 500)
            pygame.draw.rect(screen, (20, 20, 20), panel_rect, border_radius=30); pygame.draw.rect(screen, THEME_COLOR, panel_rect, 5, border_radius=30)
            screen.blit(font_large.render("GAME OVER", True, (255, 0, 0)), font_large.render("GAME OVER", True, (255, 0, 0)).get_rect(center=(WIDTH//2, HEIGHT//2 - 150)))
            screen.blit(font_btn.render(f"SCORE: {score // 10}", True, (255, 255, 255)), font_btn.render(f"SCORE: {score // 10}", True, (255, 255, 255)).get_rect(center=(WIDTH//2, HEIGHT//2)))
            screen.blit(font_btn.render(f"COINS: {coins_collected}", True, THEME_COLOR), font_btn.render(f"COINS: {coins_collected}", True, THEME_COLOR).get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))
            screen.blit(font_ui.render("R / (Tri): Retry | Q / (O): Menu", True, (200, 200, 200)), font_ui.render("R / (Tri): Retry | Q / (O): Menu", True, (200, 200, 200)).get_rect(center=(WIDTH//2, HEIGHT//2 + 180)))

    
    pygame.display.flip() 
    clock.tick(60) 