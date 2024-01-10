import pygame
import random
import time

# Initialize Pygame
pygame.init()

# Game variables
screen_width, screen_height = 400, 600
bird_x, bird_y = 100, screen_height // 2
bird_change_y = 0
gravity = 0.5
obstacle_width = 70
obstacle_height = random.randint(150, 450)
obstacle_x = 400
obstacle_speed = 2
gap = 200
score = 0
level = 0

# Set up the display
screen = pygame.display.set_mode((screen_width, screen_height))

def reset_game():
    global bird_y, bird_change_y, obstacle_x, obstacle_height, score, obstacle_speed, gap, level
    bird_y = screen_height // 2
    bird_change_y = 0
    obstacle_x = 400
    obstacle_height = random.randint(150, 450)
    score = 0
    obstacle_speed = 2
    gap = 200
    level = 0

# Update game difficulty
def update_difficulty():
    global obstacle_speed, gap
    obstacle_speed += 0.5
    gap = max(150, gap - 10)

# Game loop
running = True
while running:
    screen.fill((135, 206, 250))  # Sky blue background

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                bird_change_y = -10

    # Bird mechanics
    bird_change_y += gravity
    bird_y += bird_change_y

    # Obstacle mechanics
    obstacle_x -= obstacle_speed
    if obstacle_x < -obstacle_width:
        obstacle_x = screen_width
        obstacle_height = random.randint(200, 400)
        score += 1
        if score % 5 == 0:  # Every 5 points, increase the difficulty
            update_difficulty()
            level += 1

    # Draw bird
    pygame.draw.rect(screen, (255, 255, 0), (bird_x, bird_y, 30, 30))

    # Draw obstacles
    pygame.draw.rect(screen, (0, 128, 0), (obstacle_x, 0, obstacle_width, obstacle_height))
    pygame.draw.rect(screen, (0, 128, 0), (obstacle_x, obstacle_height + gap, obstacle_width, screen_height))

    # Collision detection
    game_over = bird_y > screen_height - 30 or bird_y < 0 or (obstacle_x < bird_x + 30 < obstacle_x + obstacle_width and (bird_y < obstacle_height or bird_y > obstacle_height + gap))

    # Display score and level
    font = pygame.font.SysFont(None, 36)
    score_text = font.render(f'Score: {score}', True, (255, 255, 255))
    level_text = font.render(f'Level: {level}', True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    screen.blit(level_text, (10, 50))

    # Game over
    if game_over:
        game_over_text = font.render('Game Over', True, (255, 255, 255))
        screen.blit(game_over_text, (screen_width // 2 - game_over_text.get_width() // 2, screen_height // 2 - game_over_text.get_height() // 2))
        pygame.display.update()
        time.sleep(2)  # Wait for 2 seconds
        reset_game()
        continue

    # Update screen
    pygame.display.update()
    pygame.time.Clock().tick(60)

# Quit game
pygame.quit()
