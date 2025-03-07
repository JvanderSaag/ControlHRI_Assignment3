# Import modules
import pygame
import math
import numpy as np
import struct
import random
import socket
import os
import time
import datetime

x = 20
y = 150
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)

pygame.init()

# Initialize constants
white = (255, 255, 255)
red = (255, 0, 0)
orange = (255, 140, 0)
green = (0, 255, 0)
black = (0, 0, 0)

display_width = 800
display_height = 600

player_size = 10
fd_fric = 0.2
bd_fric = 0.4
player_max_speed = 20
player_max_rtspd = 10
bullet_speed = 15
saucer_speed = 5
small_saucer_accuracy = 10

# Initialize UDP receive and send sockets
send_force = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = np.zeros(2)
send_data = bytearray(struct.pack("=%sf" % msg.size, *msg))
send_force.sendto(send_data, ("127.0.0.1", 50504))

receive_position = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_position.bind(("127.0.0.1", 50503))

# Make surface and display
gameDisplay = pygame.display.set_mode((display_width, display_height))
pygame.display.set_caption("Asteroids")
timer = pygame.time.Clock()

# Import sound effects
snd_fire = pygame.mixer.Sound("Asteroids/Sounds/fire.wav")
snd_bangL = pygame.mixer.Sound("Asteroids/Sounds/bangLarge.wav")
snd_bangM = pygame.mixer.Sound("Asteroids/Sounds/bangMedium.wav")
snd_bangS = pygame.mixer.Sound("Asteroids/Sounds/bangSmall.wav")
snd_extra = pygame.mixer.Sound("Asteroids/Sounds/extra.wav")
snd_saucerB = pygame.mixer.Sound("Asteroids/Sounds/saucerBig.wav")
snd_saucerS = pygame.mixer.Sound("Asteroids/Sounds/saucerSmall.wav")

xc, yc = gameDisplay.get_rect().center  # window center
window_scale = 800
vector_1 = np.array([xc, yc])
trans_matrix = np.array([[1.33, 0], [0, 1.5]])
radius = 30

# Analysis variables
START_TIME = 0
TIME_ALIVE = None
ASTEROIDS_HIT = 0
SAUCERS_HIT = 0
SCORE = 0
POSITIONS = []
VELOCITIES = []
DISTANCE_TRAVELLED = None

# Trials configuration variables
haptic_feedback = True
if haptic_feedback == True:
    haptic_path = "with_haptics/"
else:
    haptic_path = "without_haptics/"
trial_folder_path = "trials/" + haptic_path
participant_number = "1/"

date_and_time = str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
output_filepath = trial_folder_path + participant_number + date_and_time
os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
print("TRIAL WILL BE WRITTEN TO: ", output_filepath)


def calculate_distance(positions):
    distance_travelled = 0
    p_prev = positions[0]

    for pos in positions:
        distance_travelled += np.sqrt((pos[0] - p_prev[0])**2 + (pos[1] - p_prev[1])**2)
        p_prev = pos

    return distance_travelled


def calculate_max_velocity(velocities):
    max_vel = 0

    for vel in velocities:
        magnitude = np.sqrt(vel[0]**2 + vel[1]**2)
        if magnitude > max_vel:
            max_vel = magnitude

    return max_vel


# Create function to draw texts
def drawText(msg, color, x, y, s, center=True):
    screen_text = pygame.font.SysFont("Calibri", s).render(msg, True, color)
    if center:
        rect = screen_text.get_rect()
        rect.center = (x, y)
    else:
        rect = (x, y)
    gameDisplay.blit(screen_text, rect)


# Create funtion to chek for collision
def isColliding(x, y, xTo, yTo, size):
    if xTo - size < x < xTo + size and yTo - size < y < yTo + size:
        return True
    return False


# Create class asteroid
class Asteroid:
    def __init__(self, x, y, t):
        self.x = x
        self.y = y
        if t == "Large":
            self.size = 30
        elif t == "Normal":
            self.size = 20
        else:
            self.size = 10
        self.t = t

        # Make random speed and direction
        self.speed = random.uniform(1, (40 - self.size) * 4 / 15)
        self.dir = random.randrange(0, 360) * math.pi / 180

        # Make random asteroid sprites
        full_circle = random.uniform(18, 36)
        dist = random.uniform(self.size / 2, self.size)
        self.vertices = []
        while full_circle < 360:
            self.vertices.append([dist, full_circle])
            dist = random.uniform(self.size / 2, self.size)
            full_circle += random.uniform(18, 36)

    def updateAsteroid(self):
        # Move asteroid
        self.x += self.speed * math.cos(self.dir)
        self.y += self.speed * math.sin(self.dir)

        # Check for wrapping
        if self.x > display_width:
            self.x = 0
        elif self.x < 0:
            self.x = display_width
        elif self.y > display_height:
            self.y = 0
        elif self.y < 0:
            self.y = display_height

        # Draw asteroid
        for v in range(len(self.vertices)):
            if v == len(self.vertices) - 1:
                next_v = self.vertices[0]
            else:
                next_v = self.vertices[v + 1]
            this_v = self.vertices[v]
            pygame.draw.line(gameDisplay, white, (self.x + this_v[0] * math.cos(this_v[1] * math.pi / 180),
                                                  self.y + this_v[0] * math.sin(this_v[1] * math.pi / 180)),
                             (self.x + next_v[0] * math.cos(next_v[1] * math.pi / 180),
                              self.y + next_v[0] * math.sin(next_v[1] * math.pi / 180)))


# Create class bullet
class Bullet:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.dir = direction
        self.life = 30

    def updateBullet(self):
        # Moving
        self.x += bullet_speed * math.cos(self.dir * math.pi / 180)
        self.y += bullet_speed * math.sin(self.dir * math.pi / 180)

        # Drawing
        pygame.draw.circle(gameDisplay, white, (int(self.x), int(self.y)), 3)

        # Wrapping
        if self.x > display_width:
            self.x = 0
        elif self.x < 0:
            self.x = display_width
        elif self.y > display_height:
            self.y = 0
        elif self.y < 0:
            self.y = display_height
        self.life -= 1


# Create class saucer
class Saucer:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.state = "Dead"
        self.type = "Large"
        self.dirchoice = ()
        self.bullets = []
        self.cd = 0
        self.bdir = 0
        self.soundDelay = 0

    def updateSaucer(self):
        # Move player
        self.x += saucer_speed * math.cos(self.dir * math.pi / 180)
        self.y += saucer_speed * math.sin(self.dir * math.pi / 180)

        # Choose random direction
        if random.randrange(0, 100) == 1:
            self.dir = random.choice(self.dirchoice)

        # Wrapping
        if self.y < 0:
            self.y = display_height
        elif self.y > display_height:
            self.y = 0
        if self.x < 0 or self.x > display_width:
            self.state = "Dead"

        # Shooting
        if self.type == "Large":
            self.bdir = random.randint(0, 360)
        if self.cd == 0:
            self.bullets.append(Bullet(self.x, self.y, self.bdir))
            self.cd = 30
        else:
            self.cd -= 1

        # Play SFX
        if self.type == "Large":
            pygame.mixer.Sound.play(snd_saucerB)
        else:
            pygame.mixer.Sound.play(snd_saucerS)

    def createSaucer(self):
        # Create saucer
        # Set state
        self.state = "Alive"

        # Set random position
        self.x = random.choice((0, display_width))
        self.y = random.randint(0, display_height)

        # Set random type
        if random.randint(0, 1) == 0:
            self.type = "Large"
            self.size = 20
        else:
            self.type = "Small"
            self.size = 10

        # Create random direction
        if self.x == 0:
            self.dir = 0
            self.dirchoice = (0, 45, -45)
        else:
            self.dir = 180
            self.dirchoice = (180, 135, -135)

        # Reset bullet cooldown
        self.cd = 0

    def drawSaucer(self):
        # Draw saucer
        pygame.draw.polygon(gameDisplay, white,
                            ((self.x + self.size, self.y),
                             (self.x + self.size / 2, self.y + self.size / 3),
                             (self.x - self.size / 2, self.y + self.size / 3),
                             (self.x - self.size, self.y),
                             (self.x - self.size / 2, self.y - self.size / 3),
                             (self.x + self.size / 2, self.y - self.size / 3)), 1)
        pygame.draw.line(gameDisplay, white,
                         (self.x - self.size, self.y),
                         (self.x + self.size, self.y))
        pygame.draw.polygon(gameDisplay, white,
                            ((self.x - self.size / 2, self.y - self.size / 3),
                             (self.x - self.size / 3, self.y - 2 * self.size / 3),
                             (self.x + self.size / 3, self.y - 2 * self.size / 3),
                             (self.x + self.size / 2, self.y - self.size / 3)), 1)


# Create class for shattered ship
class deadPlayer:
    def __init__(self, x, y, l):
        self.angle = random.randrange(0, 360) * math.pi / 180
        self.dir = random.randrange(0, 360) * math.pi / 180
        self.rtspd = random.uniform(-0.25, 0.25)
        self.x = x
        self.y = y
        self.lenght = l
        self.speed = random.randint(2, 8)

    def updateDeadPlayer(self):
        pygame.draw.line(gameDisplay, white,
                         (self.x + self.lenght * math.cos(self.angle) / 2,
                          self.y + self.lenght * math.sin(self.angle) / 2),
                         (self.x - self.lenght * math.cos(self.angle) / 2,
                          self.y - self.lenght * math.sin(self.angle) / 2))
        self.angle += self.rtspd
        self.x += self.speed * math.cos(self.dir)
        self.y += self.speed * math.sin(self.dir)


# Class player
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hspeed = 0
        self.vspeed = 0
        self.dir = -90
        self.rtspd = 0
        self.thrust = False

    def updatePlayer(self):
        # Move player
        speed = math.sqrt(self.hspeed ** 2 + self.vspeed ** 2)
        if self.thrust:
            if speed + fd_fric < player_max_speed:
                self.hspeed += fd_fric * math.cos(self.dir * math.pi / 180)
                self.vspeed += fd_fric * math.sin(self.dir * math.pi / 180)
            else:
                self.hspeed = player_max_speed * math.cos(self.dir * math.pi / 180)
                self.vspeed = player_max_speed * math.sin(self.dir * math.pi / 180)
        else:
            if speed - bd_fric > 0:
                change_in_hspeed = (bd_fric * math.cos(self.vspeed / self.hspeed))
                change_in_vspeed = (bd_fric * math.sin(self.vspeed / self.hspeed))
                if self.hspeed != 0:
                    if change_in_hspeed / abs(change_in_hspeed) == self.hspeed / abs(self.hspeed):
                        self.hspeed -= change_in_hspeed
                    else:
                        self.hspeed += change_in_hspeed
                if self.vspeed != 0:
                    if change_in_vspeed / abs(change_in_vspeed) == self.vspeed / abs(self.vspeed):
                        self.vspeed -= change_in_vspeed
                    else:
                        self.vspeed += change_in_vspeed
            else:
                self.hspeed = 0
                self.vspeed = 0

        self.x += self.hspeed
        self.y += self.vspeed

        # Check for wrapping
        if self.x > display_width:
            self.x = 0
        elif self.x < 0:
            self.x = display_width
        elif self.y > display_height:
            self.y = 0
        elif self.y < 0:
            self.y = display_height

        # Rotate player
        self.dir += self.rtspd

    def drawPlayer(self):
        a = math.radians(self.dir)
        x = self.x
        y = self.y
        s = player_size
        t = self.thrust
        # Draw player
        pygame.draw.line(gameDisplay, red,
                         (x - (s * math.sqrt(130) / 12) * math.cos(math.atan(7 / 9) + a),
                          y - (s * math.sqrt(130) / 12) * math.sin(math.atan(7 / 9) + a)),
                         (x + s * math.cos(a), y + s * math.sin(a)))

        pygame.draw.line(gameDisplay, red,
                         (x - (s * math.sqrt(130) / 12) * math.cos(math.atan(7 / 9) - a),
                          y + (s * math.sqrt(130) / 12) * math.sin(math.atan(7 / 9) - a)),
                         (x + s * math.cos(a), y + s * math.sin(a)))

        pygame.draw.line(gameDisplay, red,
                         (x - (s * math.sqrt(2) / 2) * math.cos(a + math.pi / 4),
                          y - (s * math.sqrt(2) / 2) * math.sin(a + math.pi / 4)),
                         (x - (s * math.sqrt(2) / 2) * math.cos(-a + math.pi / 4),
                          y + (s * math.sqrt(2) / 2) * math.sin(-a + math.pi / 4)))
        if t:
            pygame.draw.line(gameDisplay, orange,
                             (x - s * math.cos(a),
                              y - s * math.sin(a)),
                             (x - (s * math.sqrt(5) / 4) * math.cos(a + math.pi / 6),
                              y - (s * math.sqrt(5) / 4) * math.sin(a + math.pi / 6)))
            pygame.draw.line(gameDisplay, orange,
                             (x - s * math.cos(-a),
                              y + s * math.sin(-a)),
                             (x - (s * math.sqrt(5) / 4) * math.cos(-a + math.pi / 6),
                              y + (s * math.sqrt(5) / 4) * math.sin(-a + math.pi / 6)))

    def killPlayer(self):
        # Reset the player
        self.x = display_width / 2
        self.y = display_height / 2
        self.thrust = False
        self.dir = -90
        self.hspeed = 0
        self.vspeed = 0


def gameLoop(startingState):
    global START_TIME
    global SCORE
    global ASTEROIDS_HIT
    global SAUCERS_HIT
    global POSITIONS
    global VELOCITIES

    # Init variables
    gameState = startingState
    player_state = "Alive"
    player_blink = 0
    player_pieces = []
    player_dying_delay = 0
    player_invi_dur = 0
    hyperspace = 0
    next_level_delay = 0
    bullet_capacity = 2
    bullets = []
    asteroids = []
    stage = 3
    SCORE = 0
    live = 2
    oneUp_multiplier = 1
    playOneUpSFX = 0
    intensity = 0
    player = Player(display_width / 2, display_height / 2)
    saucer = Saucer()

    # Send a UDP dummy command
    msg = np.zeros(2)
    send_data = bytearray(struct.pack("=%sf" % msg.size, *msg))
    send_force.sendto(send_data, ("127.0.0.1", 50504))

    # Main loop
    while gameState != "Exit":
        # noinspection PyBroadException
        try:
            # Receive UDP commanded position
            data, address = receive_position.recvfrom(32)
            position = np.array(struct.unpack("2f", data), dtype=np.float32)
            # print("Received commanded position: {pos}".format(pos=position))
        except:
            print("UDP connection broken, quitting...")
            gameState = "Exit"

        # Game menu
        clock = pygame.time.Clock()
        counter = 5
        font = pygame.font.SysFont(None, 300)
        text = font.render(str(counter), True, (255, 255, 255))
        timer_event = pygame.USEREVENT + 1
        pygame.time.set_timer(timer_event, 1000)
        counter_done = True

        while gameState == "Menu":
            gameDisplay.fill(black)
            drawText("ASTEROIDS", white, display_width / 2, display_height / 2, 100)
            drawText("Press any key to START", white, display_width / 2, display_height / 2 + 100, 50)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    gameState = "Exit"
                if event.type == pygame.KEYDOWN:

                    while counter_done:
                        gameDisplay.fill(black)
                        drawText("Center the haply device", white, display_width / 2, display_height / 10 + 100, 50)
                        clock.tick(60)
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                run = False
                            elif event.type == timer_event:
                                counter -= 1
                                text = font.render(str(counter), True, (255, 255, 255))
                                if counter == 0:
                                    pygame.time.set_timer(timer_event, 0)
                                    counter_done = False
                        text_rect = text.get_rect(center=gameDisplay.get_rect().center)
                        gameDisplay.blit(text, text_rect)
                        pygame.display.flip()

                    gameState = "Playing"
                    START_TIME = time.time()
            pygame.display.update()
            timer.tick(5)

        # User inputs
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                gameState = "Exit"
                if gameState == "Game Over":
                    gameState = "Exit"
                if event.key == pygame.K_LSHIFT:
                    hyperspace = 30
            elif event.type == pygame.KEYUP:
                if event.key == ord('q'):  ##Force to quit
                    gameState = "Exit"

        # Keep track of players positions and velocities
        POSITIONS.append(np.array([player.x, player.y]))
        VELOCITIES.append(np.array([player.hspeed, player.vspeed]))

        vector_2 = trans_matrix @ np.array([position[0], position[1]])
        player.dir = math.degrees(math.atan2(vector_2[1] - vector_1[1], vector_2[0] - vector_1[0]))

        dx = abs(vector_2[0] - xc)
        dy = abs(vector_2[1] - yc)

        if dx > radius or dy > radius or dx**2 + dy**2 > radius**2:
            player.thrust = True
        else:
            player.thrust = False

        if len(bullets) < bullet_capacity:
            bullets.append(Bullet(player.x, player.y, player.dir))
            pygame.mixer.Sound.play(snd_fire)

        # print("hspeed: ", player.hspeed, "  vspeed: ", player.vspeed)

        # Update player
        player.updatePlayer()

        # Checking player invincible time
        if player_invi_dur != 0:
            player_invi_dur -= 1
        elif hyperspace == 0:
            player_state = "Alive"

        # Reset display
        gameDisplay.fill(black)

        # Hyperspace
        if hyperspace != 0:
            player_state = "Died"
            hyperspace -= 1
            if hyperspace == 1:
                player.x = random.randrange(0, display_width)
                player.y = random.randrange(0, display_height)

        # Check for collision w/ asteroid
        for a in asteroids:
            a.updateAsteroid()
            if player_state != "Died":
                if isColliding(player.x, player.y, a.x, a.y, a.size):
                    # Create ship fragments
                    player_pieces.append(
                        deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                    player_pieces.append(
                        deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                    player_pieces.append(deadPlayer(player.x, player.y, player_size))

                    # Kill player
                    player_state = "Died"
                    player_dying_delay = 30
                    player_invi_dur = 120
                    player.killPlayer()

                    if live != 0:
                        live -= 1
                    else:
                        gameState = "Game Over"

                    # Split asteroid
                    if a.t == "Large":
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        SCORE += 20
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangL)
                    elif a.t == "Normal":
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        SCORE += 50
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangM)
                    else:
                        SCORE += 100
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangS)
                    asteroids.remove(a)

        # Update ship fragments
        for f in player_pieces:
            f.updateDeadPlayer()
            if f.x > display_width or f.x < 0 or f.y > display_height or f.y < 0:
                player_pieces.remove(f)

        # Check for end of stage
        if len(asteroids) == 0 and saucer.state == "Dead":
            if next_level_delay < 30:
                next_level_delay += 1
            else:
                stage += 1
                intensity = 0
                # Spawn asteroid away of center
                for i in range(stage):
                    xTo = display_width / 2
                    yTo = display_height / 2
                    while xTo - display_width / 2 < display_width / 4 and yTo - display_height / 2 < display_height / 4:
                        xTo = random.randrange(0, display_width)
                        yTo = random.randrange(0, display_height)
                    asteroids.append(Asteroid(xTo, yTo, "Large"))
                next_level_delay = 0

        # Update intensity
        if intensity < stage * 450:
            intensity += 1

        # Saucer
        if saucer.state == "Dead":
            if random.randint(0, 6000) <= (intensity * 2) / (stage * 9) and next_level_delay == 0:
                saucer.createSaucer()
                # Only small saucers >40000
                if SCORE >= 40000:
                    saucer.type = "Small"
        else:
            # Set saucer targer dir
            acc = small_saucer_accuracy * 4 / stage
            saucer.bdir = math.degrees(
                math.atan2(-saucer.y + player.y, -saucer.x + player.x) + math.radians(random.uniform(acc, -acc)))

            saucer.updateSaucer()
            saucer.drawSaucer()

            # Check for collision w/ asteroid
            for a in asteroids:
                if isColliding(saucer.x, saucer.y, a.x, a.y, a.size + saucer.size):
                    # Set saucer state
                    saucer.state = "Dead"

                    # Split asteroid
                    if a.t == "Large":
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangL)
                    elif a.t == "Normal":
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangM)
                    else:
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangS)
                    asteroids.remove(a)

            # Check for collision w/ bullet
            for b in bullets:
                if isColliding(b.x, b.y, saucer.x, saucer.y, saucer.size):
                    # Add points
                    if saucer.type == "Large":
                        SCORE += 200
                    else:
                        SCORE += 1000

                    # Set saucer state
                    saucer.state = "Dead"
                    SAUCERS_HIT += 1

                    # Play SFX
                    pygame.mixer.Sound.play(snd_bangL)

                    # Remove bullet
                    bullets.remove(b)

            # Check collision w/ player
            if isColliding(saucer.x, saucer.y, player.x, player.y, saucer.size):
                if player_state != "Died":
                    # Create ship fragments
                    player_pieces.append(
                        deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                    player_pieces.append(
                        deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                    player_pieces.append(deadPlayer(player.x, player.y, player_size))

                    # Kill player
                    player_state = "Died"
                    player_dying_delay = 30
                    player_invi_dur = 120
                    player.killPlayer()

                    if live != 0:
                        live -= 1
                    else:
                        gameState = "Game Over"

                    # Play SFX
                    pygame.mixer.Sound.play(snd_bangL)

            # Saucer's bullets
            for b in saucer.bullets:
                # Update bullets
                b.updateBullet()

                # Check for collision w/ asteroids
                for a in asteroids:
                    if isColliding(b.x, b.y, a.x, a.y, a.size):
                        # Split asteroid
                        if a.t == "Large":
                            asteroids.append(Asteroid(a.x, a.y, "Normal"))
                            asteroids.append(Asteroid(a.x, a.y, "Normal"))
                            # Play SFX
                            pygame.mixer.Sound.play(snd_bangL)
                        elif a.t == "Normal":
                            asteroids.append(Asteroid(a.x, a.y, "Small"))
                            asteroids.append(Asteroid(a.x, a.y, "Small"))
                            # Play SFX
                            pygame.mixer.Sound.play(snd_bangL)
                        else:
                            # Play SFX
                            pygame.mixer.Sound.play(snd_bangL)

                        # Remove asteroid and bullet
                        asteroids.remove(a)
                        saucer.bullets.remove(b)

                        break

                # Check for collision w/ player
                if isColliding(player.x, player.y, b.x, b.y, 5):
                    if player_state != "Died":
                        # Create ship fragments
                        player_pieces.append(
                            deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                        player_pieces.append(
                            deadPlayer(player.x, player.y, 5 * player_size / (2 * math.cos(math.atan(1 / 3)))))
                        player_pieces.append(deadPlayer(player.x, player.y, player_size))

                        # Kill player
                        player_state = "Died"
                        player_dying_delay = 30
                        player_invi_dur = 120
                        player.killPlayer()

                        if live != 0:
                            live -= 1
                        else:
                            gameState = "Game Over"

                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangL)

                        # Remove bullet
                        saucer.bullets.remove(b)

                if b.life <= 0:
                    try:
                        saucer.bullets.remove(b)
                    except ValueError:
                        continue

        # Bullets
        for b in bullets:
            # Update bullets
            b.updateBullet()

            # Check for bullets collide w/ asteroid
            for a in asteroids:
                if a.x - a.size < b.x < a.x + a.size and a.y - a.size < b.y < a.y + a.size:
                    # Split asteroid
                    if a.t == "Large":
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        asteroids.append(Asteroid(a.x, a.y, "Normal"))
                        SCORE += 20
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangL)
                    elif a.t == "Normal":
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        asteroids.append(Asteroid(a.x, a.y, "Small"))
                        SCORE += 50
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangM)
                    else:
                        SCORE += 100
                        # Play SFX
                        pygame.mixer.Sound.play(snd_bangS)
                    asteroids.remove(a)
                    ASTEROIDS_HIT += 1
                    bullets.remove(b)

                    break

            # Destroying bullets
            if b.life <= 0:
                try:
                    bullets.remove(b)
                except ValueError:
                    continue

        # Extra live
        if SCORE > oneUp_multiplier * 10000:
            oneUp_multiplier += 1
            live += 1
            playOneUpSFX = 60
        # Play sfx
        if playOneUpSFX > 0:
            playOneUpSFX -= 1
            pygame.mixer.Sound.play(snd_extra, 60)

        # Draw player
        if gameState != "Game Over":
            if player_state == "Died":
                if hyperspace == 0:
                    if player_dying_delay == 0:
                        if player_blink < 5:
                            if player_blink == 0:
                                player_blink = 10
                            else:
                                player.drawPlayer()
                        player_blink -= 1
                    else:
                        player_dying_delay -= 1
            else:
                player.drawPlayer()
        else:
            break
            # drawText("Game Over", white, display_width / 2, display_height / 2, 100)
            # drawText("Press \"R\" to restart!", white, display_width / 2, display_height / 2 + 100, 50)
            # live = -1

        # Draw SCORE
        drawText(str(SCORE), white, 60, 20, 40, False)

        # Draw Lives
        for l in range(live + 1):
            Player(75 + l * 25, 75).drawPlayer()

        # Update screen
        pygame.display.update()

        # Tick fps
        timer.tick(30)

        # Send UDP force feedback
        # TODO This is still a dummy packet now
        force_msg = np.array([player.hspeed, player.vspeed])
        send_data = bytearray(struct.pack("=%sf" % force_msg.size, *force_msg))
        send_force.sendto(send_data, ("127.0.0.1", 50504))


# Start game
gameLoop("Menu")

TIME_ALIVE = time.time() - START_TIME
DISTANCE_TRAVELLED = calculate_distance(POSITIONS)
MAX_VELOCITY = calculate_max_velocity(VELOCITIES)
print("TIME ALIVE: {t}".format(t=TIME_ALIVE))
print("SCORE: {s}".format(s=SCORE))
print("ASTEROIDS HIT: {ast_hit}".format(ast_hit=ASTEROIDS_HIT))
print("SAUCERS HIT: {sauce_hit}".format(sauce_hit=SAUCERS_HIT))
print("DISTANCE TRAVELLED: {dist}".format(dist=DISTANCE_TRAVELLED))
print("MAX VELOCITY: {max_vel}".format(max_vel=MAX_VELOCITY))


outfile = open(output_filepath + ".txt", 'w')
outfile.write('TIME_ALIVE, {0}\n'
              'SCORE, {1}\n'
              'ASTEROIDS HIT, {2}\n'
              'SAUCERS_HIT, {3}\n'
              'DISTANCE_TRAVELLED, {4}\n'
              'MAX_VELOCITY, {5}'.format(TIME_ALIVE, SCORE, ASTEROIDS_HIT,
                                         SAUCERS_HIT, DISTANCE_TRAVELLED, MAX_VELOCITY))
outfile.close()

# Close all sockets, and send that you are closing to the receiving end
send_force.sendto("close".encode('utf-8'), ("127.0.0.1", 50504))
send_force.close()
receive_position.close()

# End game
pygame.quit()
quit()
