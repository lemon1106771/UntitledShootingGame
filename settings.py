# Screen Settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
DARK_GRAY  = (40,  45,  55)
GOLD       = (255, 215, 0)
RED        = (255, 50,  50)
GREEN      = (0,   200, 0)
UI_BG_COLOR = (30, 30,  30)
CYAN       = (0,   200, 255)
ORANGE     = (255, 140, 0)

# HUD palette (ULTRAKILL-style)
HUD_BG          = (15,  15,  18)   # near-black panel bg
HUD_BORDER      = (42,  42,  48)   # subtle panel border
HUD_RED         = (226, 75,  74)   # health / combo accent
HUD_BLUE        = (55,  138, 221)  # ammo / dash (pistol)
HUD_AMBER       = (250, 199, 117)  # score
HUD_GREEN       = (29,  158, 117)  # parry ready
HUD_GRAY        = (80,  80,  85)   # inactive / empty pips
HUD_DIM         = (55,  55,  60)   # empty bar fill
HUD_TEXT_DIM    = (100, 100, 108)  # label text
HUD_WHITE       = (230, 230, 235)  # bright text

# Weapon pip colors  (fill, border)
WEAPON_COLORS = {
    "pistol":  ((55,  138, 221), (24,  95,  165)),
    "shotgun": ((216, 90,  48),  (153, 60,  29)),
    "rifle":   ((99,  153, 34),  (59,  109, 17)),
}

# Style rank definitions  (min_combo, letter, label, color)
STYLE_RANKS = [
    (0,  "D",  "DEAD",     (136, 135, 128)),
    (2,  "C",  "CRUEL",    (93,  202, 175)),
    (4,  "B",  "BRUTAL",   (133, 183, 235)),
    (6,  "S",  "SAVAGE",   (250, 199, 117)),
    (8,  "SS", "SADISTIC", (239, 159, 39)),
    (10, "P",  "PRIME",    (226, 75,  74)),
]

# Player & Game Balance
PLAYER_START_X = 375
PLAYER_START_Y = 250
SPAWN_RATE     = 120   # frames between enemy spawns

# Dash
DASH_SPEED     = 18
DASH_DURATION  = 10   # frames the dash lasts
DASH_COOLDOWN  = 45   # frames before you can dash again

# Slow-mo hitStop
SLOWMO_DURATION   = 18   # frames of slow-mo on successful parry
SLOWMO_TIMESCALE  = 0.2  # velocities scaled by this during slow-mo

# Combo
COMBO_DECAY_FRAMES = 180  # frames before combo resets (3 s)