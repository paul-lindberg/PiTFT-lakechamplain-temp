import sys
import platform
import math
import pandas
import matplotlib
import matplotlib.pyplot
import matplotlib.backends.backend_agg as agg
import os
import os.path
import fileinput
import subprocess
import time
import socket
import pygame
from pygame.locals import *
from PIL import Image
from climata.usgs import DailyValueIO
import requests
from bs4 import BeautifulSoup
import json
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import datetime

# from html.parser import HTMLParser

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

DIST = ""

if platform.system() == "Windows":
    import fake_rpi

    sys.modules['RPi'] = fake_rpi.RPi  # Fake RPi (GPIO)
    sys.modules['smbus'] = fake_rpi.smbus  # Fake smbus (I2C)
    from fake_rpi import toggle_print

    toggle_print(False)
from RPi import GPIO

if platform.system() == "Linux":
    DIST = GPIO.RPI_INFO['REVISION']  # Inspect RPi Revisions:
    # https://www.raspberrypi.org/documentation/hardware/raspberrypi/revision-codes/README.md

matplotlib.use("Agg")

# Directories
DIR_BASE = os.path.join(os.path.dirname(__file__), '..')  # Base Directory
# DIR_RESOURCE = os.path.join(DIR_BASE, 'resource')

# Paths
PATH_IMAGE_OFFLINE = os.path.join(os.path.join(DIR_BASE, 'resource'), 'PiOffline.png')
PATH_IMAGE_STARTUP = os.path.join(os.path.join(DIR_BASE, 'resource'), 'PiOnline.png')
PATH_IMAGE_BLANK = os.path.join(os.path.join(DIR_BASE, 'resource'), 'Blank.png')
PATH_IMAGE_GRAPH_TEMPERATURE = os.path.join(os.path.join(DIR_BASE, 'resource'), 'graph_temp_lake.png')
PATH_IMAGE_BURLINGTON_LEFT = os.path.join(os.path.join(DIR_BASE, 'resource'), 'burlington_left.jpg')
PATH_IMAGE_BURLINGTON_RIGHT = os.path.join(os.path.join(DIR_BASE, 'resource'), 'burlington_right.jpg')
PATH_IMAGE_SPONSOR = os.path.join(os.path.join(DIR_BASE, 'resource'), 'sponsor.jpg')
PATH_IMAGE_MOVIES = os.path.join(os.path.join(DIR_BASE, 'resource'), 'msl-movies.png')
PATH_ICON_SLIDESHOW = os.path.join(os.path.join(DIR_BASE, 'resource'), 'mode_slideshow.png')
PATH_ICON_MANA = os.path.join(os.path.join(DIR_BASE, 'resource'), 'Mana.png')
PATH_ICON_MAP = os.path.join(os.path.join(DIR_BASE, 'resource'), 'Map_0.png')
PATH_KINECT_LOGGER = os.path.join(DIR_BASE, *"kinectElements/Sacknet.KinectFacialRecognitionLogger/bin/Release/Sacknet.KinectFacialRecognitionLogger.exe".split("/"))
PATH_KINECT_SCANNER = os.path.join(DIR_BASE, *"kinectElements/Sacknet.KinectFacialRecognitionScanner/bin/Release/Sacknet.KinectFacialRecognitionScanner.exe".split("/"))

# Tracking Status
TRACKING_DEFAULT = "Not tracking for next class."
TRACKING_NULL = "Not logged in."
TRACKING_TIMEOUT = "No approaching bus has been detected."

# Username
USER_DEFAULT = "Default"

# PiTFT Button Map
button_map = (23, 22, 27, 18)

# PiTFT Screen Dimensions
if DIST == 'a020d3':  # Model 3B+
    DIM_SCREEN = 480, 320  # 3.5" = (480x320)
    # PiTFT Button Map
    # button_map = (23, 22, 27, 18)
elif DIST == '000e':  # Model B, Revision 2
    DIM_SCREEN = 320, 240  # 2.8" = (320x240)
else:
    DIM_SCREEN = 960, 640  # Desktop dimensions

DIM_ICON = 10, 10  # Icon Dimensions

# Setup the GPIOs as inputs with Pull Ups since the buttons are connected to GND
GPIO.setmode(GPIO.BCM)
for k in button_map:
    GPIO.setup(k, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# TODO: Once buttons are soldered on: https://web.archive.org/web/20151027165018/http://jeremyblythe.blogspot.com/2014/09/raspberry-pi-pygame-ui-basics.html

# Initialize OS Screen
os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')
os.putenv('SDL_MOUSEDRV', 'TSLIB')

# Initialize Pygame
pygame.init()
# Initialize Events TODO: Settings - Save slideshow incriments and frequency of downloading data.
pygame.time.set_timer(USEREVENT + 1, 28800000)  # Every 8 hours, download temperature and movie data.
pygame.time.set_timer(USEREVENT + 2, 10000)  # 10 seconds # 120000)  # Every 10 seconds, switch the surface.
pygame.time.set_timer(USEREVENT + 3, 60000)  # Every minute, refresh the clock.
# pygame.time.set_timer(USEREVENT + 4, 0)  # Not an event that needs to be set here, but just pointing out it exists.
# pygame.time.set_timer(USEREVENT + 5, 0)  # Not an event that needs to be set here, but just pointing out it exists.
pygame.time.set_timer(USEREVENT + 6, 900000)  # Every 15 minutes, download burlington pictures.
pygame.time.set_timer(USEREVENT + 7, 5000)  # Every 5 seconds, download shuttle data.

# Fonts
# print(pygame.font.get_fonts())
if platform.system() == "Windows":
    print("Windows fonts")
    #  TODO: Test these full-path fonts on linux systems, then move fonts out of platform.system()-if statements.
    FONT_FALLOUT = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'r_fallouty.ttf'), 30)
    FONT_BM = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'din1451alt.ttf'), 10)
    FONT_MOVIE_TITLE = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'din1451alt.ttf'), 40)
    FONT_MOVIE_DESC = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'din1451alt.ttf'), 20)
    FONT_CLASS = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'din1451alt.ttf'), 40)
elif platform.system() == "Linux":
    pygame.mouse.set_visible(False)
    print("Linux fonts")
    FONT_FALLOUT = pygame.font.Font('resource/fonts/r_fallouty.ttf', 30)
    FONT_BM = pygame.font.Font('resource/fonts/din1451alt.ttf', 10)
    FONT_MOVIE_TITLE = pygame.font.Font('resource/fonts/din1451alt.ttf', 40)
    FONT_MOVIE_DESC = pygame.font.Font('resource/fonts/din1451alt.ttf', 20)
    FONT_CLASS = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/din1451alt.ttf'), 40)
else:
    print("default fonts")
    FONT_FALLOUT = pygame.font.SysFont(None, 30)
    FONT_BM = pygame.font.SysFont(None, 13)
#  TODO: Fix Font not working on Raspberry Pi

screen = pygame.display.set_mode(DIM_SCREEN)

# colors
COLOR_BLACK = 0, 0, 0
COLOR_BLUE = 52, 113, 235
COLOR_WHITE = 255, 255, 255
COLOR_GRAY_19 = 31, 31, 31
COLOR_GRAY_21 = 54, 54, 54
COLOR_GRAY_41 = 105, 105, 105
COLOR_GREEN = 158, 235, 52
COLOR_ORANGE = 251, 126, 20
COLOR_LAVENDER = 230, 230, 250
COLOR_ALPHA_WHITE = 255, 255, 255, 70  # 128
COLOR_ALPHA_ORANGE = 251, 126, 20, 70  # 128
COLOR_ALPHA_LAVENDER = 230, 230, 250, 128

# urls
URL_MAINSTREET = "https://www.mainstreetlanding.com"

# Icon Constants
ICON_SLIDESHOW = 0  # Slideshow Icon
ICON_TEST = 1  # Slideshow Icon
ICON_MAP = 2  # Slideshow Icon

# Content switching
CONTENT_PROFILE = {"number": 0,
                 "name": "Profile Login"}
CONTENT_PICTURE = {"number": 1,
                   "name": "Burlington Live Camera"}
CONTENT_MAINSTREET = {"number": 2,
                      "name": "Mainstreet Landing Movies"}
CONTENT_SHUTTLE = {"number": 3,
                   "name": "Shuttle Map"}
CONTENT_CLASS = {"number": 4,
                 "name": "Class Shuttle Alert"}
CONTENT_TEMPERATURE = {"number": 5,
                       "name": "Temperature: Lake"}


class Card:
    def __init__(self, title="", desc="",
                 img=pygame.image.load(PATH_IMAGE_OFFLINE)):
        self.title = title
        self.desc = desc
        self.img = img


# TODO: Error Checking requests.get() error
def downloadImage(output, address):
    f = open(os.path.join(os.path.join(DIR_BASE, 'resource'), output), 'wb')
    f.write(requests.get(address).content)
    f.close()


class Button:
    def __init__(self, color_active=COLOR_ALPHA_ORANGE, color_inactive=COLOR_ALPHA_WHITE, surf=None, dim=None, width=1):
        self.color_inactive = color_inactive
        self.color_active = color_active
        self.surf = surf  # (DIM_SCREEN[0] - 60, 0), (60, DIM_SCREEN[1]) right
        self.dim = dim
        self.width = width
        self.state = False

    def active(self, mouse):
        if self.dim[0] + self.dim[2] > mouse['position'][0] > self.dim[0] \
                and self.dim[1] + self.dim[3] > mouse['position'][1] > self.dim[1] \
                and mouse['click']:
            # pygame.draw.rect(screen, COLOR_ORANGE, self.surf)
            self.surf.fill(self.color_active)  # notice the alpha value in the color
            self.state = True
        else:
            # pygame.draw.rect(screen, self.color, self.surf, self.width)
            # https://stackoverflow.com/questions/6339057/draw-a-transparent-rectangle-in-pygame
            self.surf.fill(self.color_inactive)  # notice the alpha value in the color
            self.state = False
        screen.blit(self.surf, (self.dim[0], self.dim[1]))


#
# class Page:
#     def __init__(self, background=pygame.transform.scale(pygame.image.load(PATH_IMAGE_OFFLINE),
#                                                          DIM_SCREEN), buttons=[]):
#         self.background = background
#         self.buttons = buttons

class Profile:
    def __init__(self, name=USER_DEFAULT, calendars=["Class Times"], pages=[]):
        self.name = name
        self.calendars = calendars
        self.pages = pages


class Environment:
    def __init__(self):
        # Initialize data buffers
        self.classTrackingTime = None
        self.classTrackingStatus = TRACKING_NULL
        self.className = None
        self.map = None
        self.defaultIndex = -1
        self.custom_overlays = []
        self.markers = []
        self.buses = []
        self.data_temperature_water = None
        self.mouse = {"position": (0, 0),
                      "click": False}
        self.movies = []
        self.profiles = []
        self.user = Profile()  # Default profile name
        self.gui = {}
        self.gui_picture_toggle = True
        self.gui_mainstreet_iter = 0

        self.sponsor = Card
        # Define content list TODO: Settings - Save enabled/disabled content
        self.contentList = [
            [CONTENT_PROFILE, PATH_IMAGE_BLANK, lambda func: self.surf_profile()],
            [CONTENT_PICTURE, PATH_IMAGE_BURLINGTON_LEFT, lambda func: self.surf_picture()],
            [CONTENT_MAINSTREET, PATH_IMAGE_BLANK, lambda func: self.surf_mainstreet()],
            [CONTENT_SHUTTLE, PATH_IMAGE_STARTUP, lambda func: self.surf_shuttle()],
            [CONTENT_CLASS, PATH_IMAGE_BLANK, lambda func: self.surf_class()],
            [CONTENT_TEMPERATURE, PATH_IMAGE_GRAPH_TEMPERATURE, lambda func: self.surf_plot()],
        ]
        surf = pygame.Surface(DIM_SCREEN)
        surf.convert()
        surf.fill(COLOR_WHITE)
        pygame.image.save(surf, os.path.join(os.path.join(DIR_BASE, 'resource'), 'Blank.png'))
        self.surf_background = pygame.transform.scale(pygame.image.load(PATH_IMAGE_BLANK),
                                                      DIM_SCREEN)  # Set surface image to offline
        self.time_text = (None, None)  # Time Buffer
        self.slideshow = False  # slideshow toggler
        self.buttonDelay = False  # Button delay
        self.backlight = True  # Backlight is On
        self.cIndex = CONTENT_PROFILE['number']  # Start with profile

        # Icons
        self.icon = [pygame.transform.scale(pygame.image.load(PATH_ICON_SLIDESHOW), DIM_ICON),  # Slideshow
                     pygame.transform.scale(pygame.image.load(PATH_ICON_MANA), DIM_ICON),  # Test
                     pygame.transform.scale(pygame.image.load(PATH_ICON_MAP), DIM_ICON)  # Test
                     ]
        # Pull data from internet/system
        self.pullTime()  # Set time
        self.pullData()  # Download data
        self.graph_temp()  # Graph data
        self.pullImageBurlington()  # Download Burlington images
        self.getMarkerInfo()
        self.pullShuttle()
        self.pullProfiles()  # Load Profiles
        # self.setTracking()  # TODO: *****************TEMPORARY*******************
        self.setProfile(USER_DEFAULT)  # TODO: Allow an option for the last user to be re-logged in upon bootup

        # You have to run a set-surface function before the slides start up.
        self.surf_background = pygame.image.load(self.user.pages[self.cIndex][1])
        # self.surf_startup()  # Start with lake temperature
        if platform.system() == "Linux":
            # Only use the sleep function for raspberry pi
            pygame.time.set_timer(USEREVENT + 5, 60000)  # 1 minute # 600000) # 10 minutes

    def menu(self):
        crashed = False
        while not crashed:
            content_list_enough = len(self.user.pages) > 1  # larger than one
            for event in pygame.event.get():
                # Every 8 hours, download data
                if event.type == USEREVENT + 1:  # Every 8 hours, download new data and render images.
                    self.pullData()
                    self.graph_temp()
                if event.type == USEREVENT + 2 and content_list_enough and self.slideshow:  # 10 seconds # 120000)  # Every 10 seconds, switch the surface.
                    self.content_iterate()
                if event.type == USEREVENT + 3:  # Every minute, refresh the clock.
                    self.pullTime()  # TODO: Make time toggleable and an options menu to do it.
                if event.type == USEREVENT + 4:
                    self.buttonDelay = False  # Button time buffer
                    pygame.time.set_timer(USEREVENT + 4,
                                          0)  # TODO: Update to pygame 2.0.0dev3 to upgrade pygame.time.set_timer()
                if event.type == USEREVENT + 5:
                    print("Sleep mode activated")
                    os.system("sudo sh -c \'echo \"0\" > /sys/class/backlight/soc\:backlight/brightness\'")  # Off
                    self.backlight = False  # "backlight is not on"
                    pygame.time.set_timer(USEREVENT + 5, 0)  # Shut off sleep timer
                if event.type == USEREVENT + 6:
                    self.pullImageBurlington()  # Every 15 minutes, download burlington images.
                if event.type == USEREVENT + 7:
                    self.pullShuttle()
                if event.type == pygame.QUIT:
                    crashed = True

                # mouse
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse['click'] = True
                    if platform.system() == "Linux":
                        self.reset_backlight()  # Whenever the user touches the screen, reset the backlight
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse['click'] = False
                else:
                    self.mouse['click'] = False

                if event.type == pygame.KEYDOWN and not self.buttonDelay:
                    if platform.system() == "Linux":
                        self.reset_backlight()
                    if event.key == pygame.K_ESCAPE:
                        exit()# pygame.quit()
                    if content_list_enough:
                        if event.key == pygame.K_BACKSLASH:
                            self.toggleSlideshow()
                        if event.key == pygame.K_LEFT:
                            self.content_iterate(True)
                            self.reset_slideshow()
                        if event.key == pygame.K_RIGHT:
                            self.content_iterate()
                            self.reset_slideshow()
                    self.reset_buttondelay()

            self.mouse['position'] = pygame.mouse.get_pos()

            # TODO: Touching the screen makes the screen refresh and the slideshow time reset
            # if self.slideshow:

            # Scan the buttons
            for k in button_map:  # TODO: IMPLEMENT BUTTONS FOR ALL PI PLATFORMS
                if not GPIO.input(k) and not self.buttonDelay and DIST == "000e":  # platform.system() == "Linux":
                    if k == button_map[0]:
                        pygame.quit()
                    if content_list_enough:
                        if k == button_map[1]:
                            self.toggleSlideshow()
                        if k == button_map[2]:
                            self.content_iterate(True)
                            self.reset_slideshow()
                        if k == button_map[3]:
                            self.content_iterate()
                            self.reset_slideshow()
                    self.reset_buttondelay()  # Reset the tactile button delay
                    self.reset_backlight()  # Whenever the user presses a button, reset the backlight
            self.refresh()

    def reset_buttondelay(self):
        self.buttonDelay = True
        pygame.time.set_timer(USEREVENT + 4, 200)  # delay is 1/5th of a second

    def reset_slideshow(self):
        if self.slideshow:  # if the slideshow bool is enabled, reset the timer:
            pygame.time.set_timer(USEREVENT + 2, 10000)  # 10 seconds

    def reset_backlight(self):
        pygame.time.set_timer(USEREVENT + 5, 60000)  # 1 minute # 600000) # 10 minutes
        # Prevents the backlight from constantly getting set on instead of just to turn it back on.
        if not self.backlight:  # if "backlight turn-on has been tripped"
            os.system("sudo sh -c \'echo \"1\" > /sys/class/backlight/soc\:backlight/brightness\'")  # On
            self.backlight = True  # "backlight turn-on has been tripped"

    def content_iterate(self, prev=False):
        self.gui.clear()  # clear gui
        if prev:
            self.cIndex = self.user.pages.index(self.user.pages[self.cIndex - 1])  # Iterate cIndex backwards
        else:
            if self.cIndex + 1 >= len(self.user.pages):  # Iterate cIndex forwards
                self.cIndex = 0
            else:
                self.cIndex = self.cIndex + 1
        print(self.user.pages[self.cIndex][0]['name'])
        self.surf_background = pygame.image.load(self.user.pages[self.cIndex][1])  # set background

    def refresh(self):
        screen.blit(self.surf_background, (0, 0))  # Background

        self.user.pages[self.cIndex][2](self)  # run the content function

        # Icons Todo: make icon bar toggleable in options
        pygame.draw.rect(screen, COLOR_WHITE, pygame.Rect((0, 0), (DIM_SCREEN[0], 13)), 0)  # Icon bar backing
        if self.slideshow:  # if the slideshow bool is enabled, display the icon.
            screen.blit(self.icon[ICON_SLIDESHOW], (44, 1))
        if self.buttonDelay:  # if the buttonDelay bool is enabled, display the icon.
            screen.blit(self.icon[ICON_TEST], (59, 1))
        if self.classTrackingTime:  # if tracking the next bus, bool is enabled, display the icon.
            screen.blit(self.icon[ICON_MAP], (74, 1))

        # Content Name
        cont__name = FONT_BM.render(self.user.pages[self.cIndex][0]['name'], True, COLOR_BLACK)
        screen.blit(cont__name, ((int(DIM_SCREEN[0] / 2) - cont__name.get_size()[0]) - 2, 1))

        # Profile Name
        if self.user.name != USER_DEFAULT:
            profile__name = FONT_BM.render("User: " + self.user.name, True, COLOR_BLACK)
        else:
            profile__name = FONT_BM.render("Not Logged In", True, COLOR_BLACK)
        screen.blit(profile__name, ((DIM_SCREEN[0] - profile__name.get_size()[0]) - 2, 1))

        # Clock
        # pygame.draw.rect(screen, COLOR_WHITE, pygame.Rect((0, 0), (40, 13)), 0)  # Clock backing
        screen.blit(self.time_text[0], (2, 1))  # time text 12:00
        screen.blit(self.time_text[1], (25, 1))  # time text am/pm

        pygame.display.update()

    # def surf_startup(self):
    #     print("Startup")
    #     # Set surface image
    #     self.surf_background = pygame.image.load(PATH_IMAGE_STARTUP)

    def surf_picture(self):
        # TODO: https://developers.google.com/drive/api/v3/manage-downloads
        # TODO: http://blog.vogella.com/2011/06/21/creating-bitmaps-from-the-internet-via-apache-httpclient/
        # Set buttons
        # buttons = [Button(COLOR_WHITE, pygame.Rect((DIM_SCREEN[0] - 60, 0), (60, DIM_SCREEN[1])), 0),
        #            Button(COLOR_WHITE, pygame.Rect((0, 0), (60, DIM_SCREEN[1])), 0)
        #            ]
        # self.page = Page(pygame.image.load(PATH_IMAGE_BURLINGTON_LEFT), buttons)
        self.gui.clear()  # clear gui
        if self.gui_picture_toggle:
            # https://stackoverflow.com/questions/6339057/draw-a-transparent-rectangle-in-pygame
            self.gui['button_right'] = Button(color_inactive=COLOR_ALPHA_WHITE,
                                              surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                  pygame.HWSURFACE | pygame.SRCALPHA),
                                              dim=(DIM_SCREEN[0] - 60, 0, 60, DIM_SCREEN[1]),
                                              width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        else:
            self.gui['button_left'] = Button(color_inactive=COLOR_ALPHA_WHITE,
                                             surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                 pygame.HWSURFACE | pygame.SRCALPHA),
                                             dim=(0, 0, 60, DIM_SCREEN[1]),
                                             width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        for element in self.gui.items():
            element[1].active(self.mouse)
            if element[1].state:  # if clicked
                if element[0] == "button_left":
                    self.user.pages[self.cIndex][1] = PATH_IMAGE_BURLINGTON_LEFT
                elif element[0] == "button_right":
                    self.user.pages[self.cIndex][1] = PATH_IMAGE_BURLINGTON_RIGHT
                self.gui_picture_toggle = not self.gui_picture_toggle
        self.surf_background = pygame.image.load(self.user.pages[self.cIndex][1])  # load the background anyways
        # TODO: Either remove self.gui or clear it in self.setContent

    def surf_mainstreet(self):
        # TODO: https://www.mainstreetlanding.com/performing-arts-center/daily-rental-information/movies-at-main-street-landing/
        # TODO: https://stackoverflow.com/questions/18294711/extracting-images-from-html-pages-with-python
        # TODO: Make descriptions easier to read and scroll through.

        self.gui.clear()  # clear gui
        self.surf_background = pygame.image.load(self.user.pages[self.cIndex][1])  # load the background
        if 0 < self.gui_mainstreet_iter < len(self.movies) - 1:  # if in middle of movie list
            self.gui['button_right'] = Button(color_inactive=COLOR_ALPHA_LAVENDER,
                                              surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                  pygame.HWSURFACE | pygame.SRCALPHA),
                                              dim=(DIM_SCREEN[0] - 60, 0, 60, DIM_SCREEN[1]),
                                              width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=
            self.gui['button_left'] = Button(color_inactive=COLOR_ALPHA_LAVENDER,
                                             surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                 pygame.HWSURFACE | pygame.SRCALPHA),
                                             dim=(0, 0, 60, DIM_SCREEN[1]),
                                             width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        elif self.gui_mainstreet_iter == 0:
            self.gui['button_right'] = Button(color_inactive=COLOR_ALPHA_LAVENDER,
                                              surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                  pygame.HWSURFACE | pygame.SRCALPHA),
                                              dim=(DIM_SCREEN[0] - 60, 0, 60, DIM_SCREEN[1]),
                                              width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=
        elif self.gui_mainstreet_iter == len(self.movies) - 1:  # if at back of movie list
            self.gui['button_left'] = Button(color_inactive=COLOR_ALPHA_LAVENDER,
                                             surf=pygame.Surface((60, DIM_SCREEN[1]),
                                                                 pygame.HWSURFACE | pygame.SRCALPHA),
                                             dim=(0, 0, 60, DIM_SCREEN[1]),
                                             width=0)  # (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        for element in self.gui.items():
            element[1].active(self.mouse)
            if element[1].state and not self.buttonDelay:  # if clicked
                if element[0] == "button_left":
                    self.gui_mainstreet_iter = self.gui_mainstreet_iter - 1
                elif element[0] == "button_right":
                    self.gui_mainstreet_iter = self.gui_mainstreet_iter + 1
                self.reset_buttondelay()

        movie = self.movies[self.gui_mainstreet_iter]  # Movie Object

        screen.blit(movie.img, (int((int(DIM_SCREEN[0] / 2) - int(movie.img.get_size()[0] / 2)) / 4),
                                int(DIM_SCREEN[1] / 2) - int(movie.img.get_size()[1] / 2)))  # Image
        text__title = FONT_MOVIE_TITLE.render(movie.title, True, COLOR_BLACK)  # Title
        screen.blit(text__title, ((DIM_SCREEN[0] - text__title.get_size()[0] - 60),
                                  int((int(DIM_SCREEN[1] / 2) - int(movie.img.get_size()[1] / 2)) / 4)))
        logo = pygame.image.load(PATH_IMAGE_MOVIES)
        screen.blit(logo, (int((int(DIM_SCREEN[0] / 2) - int(logo.get_size()[0] / 2)) / 4),
                           int((int(DIM_SCREEN[1] / 2) - int(logo.get_size()[1] / 2)) / 4) - text__title.get_size()[1]))  # Logo Image


        # pygame.Surface()
        self.drawText(screen,
                      movie.desc,
                      COLOR_BLACK,
                      pygame.Rect(int(DIM_SCREEN[0] / 3), int((int(DIM_SCREEN[1] / 2) - int(movie.img.get_size()[1] / 2)) / 4) + text__title.get_size()[1], int(DIM_SCREEN[0] / 2), DIM_SCREEN[1]),
                      FONT_MOVIE_DESC
                      )

    def surf_shuttle(self):  # TODO: https://shuttle.champlain.edu/
        pass

    def surf_class(
            self):  # TODO: Consists of a button or scanner that activates an alert for the bus before your next class.
        self.gui.clear()  # clear gui
        self.drawText(screen,
                      self.classTrackingStatus,
                      COLOR_BLACK,
                      pygame.Rect(int(DIM_SCREEN[0] / 4),
                                  int(DIM_SCREEN[1] / 5),
                                  int(DIM_SCREEN[0] * 0.75),
                                  int(DIM_SCREEN[1] * 0.75)),
                      FONT_CLASS
                      )
        # text__status = FONT_CLASS.render(self.classTrackingStatus, True, COLOR_BLACK)
        # screen.blit(text__status, (int((DIM_SCREEN[0] / 2) - int(text__status.get_size()[0] / 2)) - 2, int(DIM_SCREEN[1] / 5)))
        self.gui['button_tracker'] = Button(color_inactive=COLOR_BLACK,
                                            surf=pygame.Surface((80, 80), pygame.HWSURFACE),
                                            dim=(int(DIM_SCREEN[0] / 2) - 80, int(DIM_SCREEN[1] / 2), 80, 80),
                                            width=0)  # (left top width, left top height, right bottom width, right bottom height)
        text__tracker = FONT_CLASS.render("Bus Tracker", True, COLOR_BLACK)
        screen.blit(text__tracker, (int(DIM_SCREEN[0] / 2) - int(text__tracker.get_size()[0] / 2), int(DIM_SCREEN[1] / 3)))
        for element in self.gui.items():
            element[1].active(self.mouse)
            if element[1].state and not self.buttonDelay:  # if clicked
                if element[0] == "button_tracker":  # if the tracker was pressed
                    if self.classTrackingTime:
                        self.setTracking(False)
                    else:
                        self.setTracking()
                self.reset_buttondelay()
            if element[0] == "button_tracker" and self.classTrackingTime:  # button enabled state
                element[1].surf.fill(element[1].color_active)
                screen.blit(element[1].surf, (element[1].dim[0], element[1].dim[1]))

    def surf_profile(self):
        self.gui.clear()
        if platform.system() == "Windows":
            if self.user.name is not "Default":
                self.gui['button_logger'] = Button(color_inactive=COLOR_GREEN,
                                                    surf=pygame.Surface((80, 80), pygame.HWSURFACE),
                                                    dim=(int(DIM_SCREEN[0] / 4) - 80, int(DIM_SCREEN[1] / 2), 80, 80),
                                                    width=0)  # (left top width, left top height, right bottom width, right bottom height)
                text__logger = FONT_CLASS.render("Log Faces", True, COLOR_BLACK)
                screen.blit(text__logger, (int(DIM_SCREEN[0] / 4) - int(text__logger.get_size()[0] / 2), int(DIM_SCREEN[1] / 3)))
                self.gui['button_scanner'] = Button(color_inactive=COLOR_GREEN,
                                                    surf=pygame.Surface((80, 80), pygame.HWSURFACE),
                                                    dim=(int(DIM_SCREEN[0] * 0.75) - 80, int(DIM_SCREEN[1] / 2), 80, 80),
                                                    width=0)  # (left top width, left top height, right bottom width, right bottom height)
                text__scanner = FONT_CLASS.render("Scan", True, COLOR_BLACK)
                screen.blit(text__scanner, (int(DIM_SCREEN[0] * 0.75) - int(text__scanner.get_size()[0] / 2), int(DIM_SCREEN[1] / 3)))
        if self.user.name is "Default":
            text__logger = FONT_CLASS.render("Login:", True, COLOR_BLACK)
            screen.blit(text__logger,
                        (int(DIM_SCREEN[0] / 4) - int(text__logger.get_size()[0] / 2), int(DIM_SCREEN[1] / 5)))
            space = 0
            for profile in self.profiles:
                self.gui['button_' + profile.name] = Button(color_inactive=COLOR_GREEN,
                                                    surf=pygame.Surface((80, 80), pygame.HWSURFACE),
                                                    dim=(int(DIM_SCREEN[0] / 4) - 80 + space, int(DIM_SCREEN[1] / 2), 80, 80),
                                                    width=0)  # (left top width, left top height, right bottom width, right bottom height)
                text__profile = FONT_CLASS.render(profile.name, True, COLOR_BLACK)
                screen.blit(text__profile, (int(DIM_SCREEN[0] / 4) - int(text__profile.get_size()[0] / 2) + space, int(DIM_SCREEN[1] / 3)))
                space = space + 120
        else:
            self.gui['button_logout'] = Button(color_inactive=COLOR_BLUE,
                                                surf=pygame.Surface((80, 80), pygame.HWSURFACE),
                                                dim=(DIM_SCREEN[0] - 80, int(DIM_SCREEN[1] / 4), 80, 80),
                                                width=0)  # (left top width, left top height, right bottom width, right bottom height)
            text__logout = FONT_CLASS.render("Logout", True, COLOR_BLACK)
            screen.blit(text__logout,
                        (DIM_SCREEN[0] - int(text__logout.get_size()[0] / 2), int(DIM_SCREEN[1] / 5)))
        for element in self.gui.items():
            element[1].active(self.mouse)
            if element[1].state and not self.buttonDelay:  # and self.user.name is not "Default":  # if clicked
                if element[0] == "button_logger":
                    kinectProcess_logger = subprocess.Popen([PATH_KINECT_LOGGER, "--User", str("\"" + self.user.name + "\"")], stdout=subprocess.PIPE)
                    # print("Logger: " + str(kinectProcess_logger.communicate()[0]))
                if element[0] == "button_scanner":
                    kinectProcess_scanner = subprocess.Popen([PATH_KINECT_SCANNER], stdout=subprocess.PIPE)
                    user = kinectProcess_scanner.communicate()[0].decode()
                    print("Scanner: " + user)
                    #TODO: Implement if-statement here so that it takes the outputted username, sets the profile to it,
                    #TODO: and then starts tracking the bus for the user.
                    if user != "":
                        self.setProfile(user)
                        self.setTracking()
                if element[0] == "button_logout":
                    self.setProfile(USER_DEFAULT)
                for profile in self.profiles:
                    if element[0] == str("button_" + profile.name):
                        self.setProfile(profile.name)
                        # self.cIndex = CONTENT_PROFILE['number']  # set index to profile
                        self.setTracking()
                self.reset_buttondelay()

    def surf_plot(self):
        pass

    def graph_temp(self):
        if self.data_temperature_water:
            for series in self.data_temperature_water:  # Create list of date-flow values
                dates = [r[0] for r in series.data]
                flow = [r[1] for r in series.data]
            # render matplotgraph to bitmap
            fig = matplotlib.pyplot.figure(figsize=[DIM_SCREEN[0] * (0.02), DIM_SCREEN[1] * (0.02)],  # 6.4, 4.8],  # Inches
                                           dpi=50,  # 100 dots per inch, so the resulting buffer is 400x400 pixels
                                           )
            ax = fig.gca()
            # Convert Celsius to Fahrenheit
            for i, cel in enumerate(flow):
                flow[i] = (cel * (9 / 5)) + 32
            # Format dates
            for i, day in enumerate(dates):
                dates[i] = '{:%b-%d\n(%a)}'.format(datetime.datetime.strptime(str(dates[i]), '%Y-%m-%d %H:%M:%S'))
            ax.grid(True)
            ax.set_ylim(50, 70)
            ax.plot(dates, flow)
            # print(flow)
            # print(dates)
            # Source name
            # fig.text(0.02, 0.5, series.variable_name, fontsize=10, rotation='vertical', verticalalignment='center')
            fig.text(0.02, 0.5, 'Water Temperature (\N{DEGREE SIGN}F)', fontsize=10, rotation='vertical',
                     verticalalignment='center')
            fig.text(0.5, 0.9, series.site_name, fontsize=18, horizontalalignment='center')
            fig.text(0.84, 0.81, str(round(flow[-1])) + '\N{DEGREE SIGN}F', fontsize=25,
                     bbox=dict(boxstyle="round", pad=0.1, fc='#ee8d18', ec="#a05d0c", lw=2))
            # TODO: better annotation:
            # https://matplotlib.org/users/annotations.html#plotting-guide-annotation
            # Draw raw data
            canvas = agg.FigureCanvasAgg(fig)
            canvas.draw()
            renderer = canvas.get_renderer()
            # size = canvas.get_width_height()
            raw_data = renderer.tostring_rgb()

            # close figure
            matplotlib.pyplot.close(fig)
            # Save surface image
            pygame.image.save(pygame.image.fromstring(raw_data, DIM_SCREEN, "RGB"),
                              os.path.join(os.path.join(DIR_BASE, 'resource'), 'graph_temp_lake.png'))
        else:
            pygame.image.save(pygame.image.load(PATH_IMAGE_OFFLINE), os.path.join(os.path.join(DIR_BASE, 'resource'), 'graph_temp_lake.png'))

    def pullData(self):  # TODO: Account for an error return
        # Download lake temperature graph data
        ndays = 11  # 11 days
        station_id = "04294500"
        param_id = "00010"
        data = self.pullStationData(ndays, param_id, station_id)
        self.data_temperature_water = data

        # # Download precipitation graph data
        # ndays = 11  # 11 days
        # station_id = "04294500"
        # param_id = "00010"
        # data = self.pullStationData(ndays, param_id, station_id)
        # self.data_temperature_water = data

        # Download image and text data from mainstreetlanding.com
        html = requests.get(
            "https://www.mainstreetlanding.com/performing-arts-center/daily-rental-information/movies-at-main-street-landing/")
        soup = BeautifulSoup(html.text, features="html.parser")
        listings_raw = soup.findAll("article", {"class": "listing"})
        # Download sponsor data
        sponsor_raw = listings_raw.pop(-1)  # Remove end div because it's always the sponsor
        downloadImage('sponsor.jpg',
                      URL_MAINSTREET + "/" + str(sponsor_raw.contents[1].contents[1].contents[1].attrs['src']))
        im = Image.open(PATH_IMAGE_SPONSOR)  # Rescale the image to fit into the screen
        self.resizeImage(PATH_IMAGE_SPONSOR, "JPEG", self.scale(constraintH=int(DIM_SCREEN[1] / 2), size=im.size))
        self.sponsor = Card(
            title=str(sponsor_raw.contents[1].contents[1].contents[1].attrs['alt']),
            desc=str(sponsor_raw.contents[1].contents[3].contents[1]),
            img=pygame.image.load(PATH_IMAGE_SPONSOR)
        )
        # Download movie data
        for listing in listings_raw:
            m_image_name = 'movie' + str(listings_raw.index(listing)) + '.jpg'
            movieImagePath = os.path.join(os.path.join(DIR_BASE, 'resource'), m_image_name)
            im = None
            sizesBuffer = []
            sizes = []
            sizesBuffer = str(listing.contents[1].contents[1].contents[1].attrs['srcset']).split(" ")
            for ded in range(0, len(sizesBuffer), 2):
                sizes.append(sizesBuffer[ded])
            for iSize in sizes:
                downloadImage(m_image_name,
                              URL_MAINSTREET + iSize)
                im = self.imChecker(iSize, im, movieImagePath)
                if im:
                    break

            self.resizeImage(movieImagePath, "JPEG", self.scale(constraintH=int(DIM_SCREEN[1] / 2), size=im.size))

            desc = listing.contents[1].contents[3].contents[5].text
            tags = []
            for tag in list(filter(lambda x: (type(x) is type(listing.contents[1].contents[3].contents[5])),
                        listing.contents[1].contents[3].contents[5:])):
                tags.append(tag.text)
            if len(tags) > 1:
                desc = "\n".join(tags)

            self.movies.append(Card(
                title=listing.contents[1].contents[3].contents[1].text,
                # TODO: Parse description html (maybe allow it to italicize when printing it?)
                desc=desc,
                # TODO: If no image is downloaded, assign img to PATH_IMAGE_OFFLINE
                img=pygame.image.load(movieImagePath),
            ))

    def pullStationData(self, ndays, param_id, station_id):
        datelist = pandas.date_range(end=pandas.datetime.today(), periods=ndays).tolist()
        data = None  # https://www.earthdatascience.org/tutorials/acquire-and-visualize-usgs-hydrology-data/
        try:
            data = DailyValueIO(
                start_date=datelist[0],
                end_date=datelist[-1],
                station=station_id,
                parameter=param_id,
            )
        except (requests.exceptions.ConnectionError, socket.gaierror, ConnectionError) as e:
            print(e)
        return data
    def pullImageBurlington(self):
        # Download image from Camnet
        downloadImage('burlington_left.jpg', 'https://hazecam.net/images/large/burlington_left.jpg')
        self.resizeImage(PATH_IMAGE_BURLINGTON_LEFT, "JPEG", DIM_SCREEN)
        downloadImage('burlington_right.jpg', 'https://hazecam.net/images/large/burlington_right.jpg')
        self.resizeImage(PATH_IMAGE_BURLINGTON_RIGHT, "JPEG", DIM_SCREEN)

    def pullTime(self):
        d = datetime.datetime.strptime(str(datetime.datetime.now().time()), "%H:%M:%S.%f")
        self.time_text = (
            FONT_BM.render(d.strftime("%I:%M"), True, COLOR_BLACK), FONT_BM.render(d.strftime("%p"), True, COLOR_BLACK))

    def pullShuttle(self):
        html = requests.get("https://shuttle.champlain.edu/shuttledata")
        self.getBusLocations(html)

    def setProfile(self, user=USER_DEFAULT):
        if user == USER_DEFAULT:
            self.user = Profile(pages=self.contentList)
        else:
            for profile in self.profiles:
                if profile.name is user:
                    self.user = profile

    def pullProfiles(self):
        self.profiles.clear()  # clear profiles
        # self.profiles.append(Profile(pages=self.contentList))#[[CONTENT_PROFILE, PATH_IMAGE_BLANK, lambda func: self.surf_profile()]]))  # add default profile
        files = [f for f in os.listdir(os.path.join(DIR_BASE, 'profiles')) if os.path.isfile(os.path.join(os.path.join(DIR_BASE, 'profiles'), f))]
        for file in files:
            with open(os.path.join(os.path.join(DIR_BASE, 'profiles'), file)) as fp:
                calendars = fp.readline()  # Calendars
                pages = str(fp.readline()).split(", ")  # Pages
                pagesContent = [[CONTENT_PROFILE, PATH_IMAGE_BLANK, lambda func: self.surf_profile()]]
                if pages != [""]:
                    for page in pages:
                        pagesContent.append(self.contentList[int(page)])
                self.profiles.append(Profile(name=file[:-4], calendars=str(calendars).split(", "), pages=pagesContent))

    # Code Adapted from https://www.pygame.org/wiki/TextWrap
    # draw some text into an area of a surface
    # automatically wraps words
    # returns any text that didn't get blitted
    def drawText(self, surface, text, color, rect, font, aa=False, bkg=None):
        y = rect.top
        lineSpacing = -2

        # get the height of the font
        fontHeight = font.size("Tg")[1]

        while text:
            i = 1

            # determine if the row of text will be outside our area
            if y + fontHeight > rect.bottom:
                break

            # determine maximum width of line
            while font.size(text[:i])[0] < rect.width and i < len(text):
                i += 1

            # if we've wrapped the text, then adjust the wrap to the last word
            if i < len(text):
                i = text.rfind(" ", 0, i) + 1

            # render the line and blit it to the surface
            if bkg:
                image = font.render(text[:i], 1, color, bkg)
                image.set_colorkey(bkg)
            else:
                image = font.render(text[:i], aa, color)

            surface.blit(image, (rect.left, y))
            y += fontHeight + lineSpacing

            # remove the text we just blitted
            text = text[i:]

        return text

    def toggleSlideshow(self):
        if self.slideshow:  # if the slideshow bool is enabled:
            pygame.time.set_timer(USEREVENT + 2, 0)  # turn off the slideshow userevent
        else:  # if the slideshow bool is disabled:
            pygame.time.set_timer(USEREVENT + 2, 10000)  # turn on the slideshow userevent
        self.slideshow = not self.slideshow  # toggle the slideshow bool

    def imChecker(self, iSize, im, movieImagePath):
        try:
            im = Image.open(movieImagePath)  # Rescale the image to fit into the screen
        except IOError as e:
            im = None
            print(e)
            print("Attempting \"", iSize[28:30], "\" next.")
        return im


    def resizeImage(self, imgPath, imgType, imgDim):
        im = Image.open(imgPath)
        im_resized = im.resize(imgDim, Image.ANTIALIAS)
        im_resized.save(imgPath, imgType)

    def scale(self, constraintH, size):
        return [int(size[0] / (size[1] / constraintH)), constraintH]

    # Get Maps display information from Champlain College Shuttle Maps Markers API:
    # https://docs.google.com/spreadsheets/d/1CPgjCQZ-AUcNNvq8wAMlwfm9lKmsQuThwg9oh_EI0n0/edit#gid=0
    # For access to this sheet, contact champlaindevs@gmail.com.  Stops and busses are added to the CC_SHUTTLE.custom_overlays|buses.
    # Each "custom_overlays" and "bus" marker is composed of a model and a view - the model is information collected from Champlain APIs
    # (CC_SHUTTLE.<custom_overlays|markers|buses>.api_data) and the view is the corresponding Google Maps Marker (CC_SHUTTLE.<custom_overlays|markers|buses>.bottom_right).
    def getMarkerInfo(self):
        #  Validate result from Shuttle Maps Markers API Spreadsheet
        html = requests.get("https://forms.champlain.edu/googlespreadsheet/find/type/shuttlemapsapi")
        result = json.loads(html.text)
        if type(result) == 'undefined' or type(result['message']) == 'undefined' or type(
                result['message']) != list or len(result['message']) is None:
            print('Unable to load data from Champlain Shuttle Maps Markers API.')
            return

        #  Only records with map type of "shuttle" should be displayed on shuttle.champlain.edu
        # TODO: Make this a filter using lambda.
        # results = filter(lambda x: x['map_type'] == 'shuttle', result['message'])
        results = []
        for message in result['message']:
            if message['map_type'] == 'shuttle':
                results.append(message)

        #  Loop through each custom_overlays returned from the Shuttle Maps Markers API Spreadsheet looking for buses and custom_overlays
        for record in results:
            record['direction'] = ""
            if record['record_type'] == 'bus':
                self.buses.append({
                    'api_data': record,
                    'gm_object': False  # None
                })
            elif record['record_type'] == 'marker':
                marker = None
                marker = {
                    'api_data': record,
                    'gm_object': False  # None  # gmaps.Marker(gmaps.LatLng(record.lat, record.lon), label=record['id'], info_box_content=record['id'])
                    # What USED to be inside of 'gm_object':
                    # {'position': gmaps.LatLng(record.lat, record.lon),
                    # 'map': self.map,  # map, #TODO: make map variable and object
                    # 'icon': {
                    #     'url': record['image_url'],
                    #     'size': google.maps.Size(record['width'], record['height']),
                    #     'origin': google.maps.Point(0, 0),
                    #     'anchor': google.maps.Point(math.floor(record.width / 2), math.floor(record.height / 2))
                    # },
                    # 'zIndex': 1}
                }
                self.markers.append(marker)

                #  Uncomment to debug markers
                #  print(marker);
            elif record['record_type'] == 'custom_overlays':
                self.custom_overlays.append({
                    'api_data': record,
                    'gm_object': False  # None
                })

        #  End results.forEach ...

        #  End return $.getJSON to CC Shuttle Maps Marker API.

    def getBusLocations(self, html):
        result = json.loads(html.text)
        for bus in result:
            busIndex = -1

            # If all required attributes are returned from the shuttle tracking API, process the new bus tracking data and update the bus location on the map
            if type(bus['UnitID']) == 'undefined' or type(bus['Date_Time_ISO']) == 'undefined' or type(
                    bus['Lat']) == 'undefined' or type(bus['Lon']) == 'undefined':
                print("Bus from Shuttle Tracking API has missing attributes:")
                print(bus)

            for i in range(len(self.buses)):

                #  Get current bus ID
                if self.buses[i]['api_data']['id'] == bus['UnitID']:
                    busIndex = i
                #  Get default bus index, which is used when a bus does not have display info configured in Shuttle Maps Markers API
                if not self.defaultIndex and self.buses[i]['api_data']['id'] == 'default':
                    self.defaultIndex = i

            #  If no bus display information was found (i.e. bus ID was not in CC Shuttle Maps Marker API), then use default config
            #  that should be set up in that api (Look for bus with ID column set to "default").
            if busIndex == -1 and self.defaultIndex:
                self.buses.extend(
                    self.buses)  # self.buses.push($.extend({}, self.buses[self.defaultIndex]))  # TODO: test and make sure this is actually extending the list
                self.buses[len(self.buses) - 1]['api_data']['id'] = bus['UnitID']

            if busIndex == -1:
                print("Cannot display bus " + bus[
                    'UnitID'] + ": no bus with this ID exists AND there is no default bus configured in Shuttle Maps Markers API");
                return

            #  Determine how many minutes ago the shuttle was updated
            bApi = self.buses[busIndex]['api_data']
            bMarker = self.buses[busIndex]['gm_object']
            updated = datetime.datetime.strptime((bus['Date_Time']).replace('\\', ''), "%d/%m/%Y %H:%M:%S %p")  # old way: datetime.datetime.strptime((bus['Date_Time_ISO'][:19]).strip(), "%Y-%m-%dT%H:%M:%S")

            now = datetime.datetime.today()
            # Adapted from https://stackoverflow.com/questions/2788871/date-difference-in-minutes-in-python
            # Convert to Unix timestamp
            d1_ts = time.mktime(now.timetuple())
            d2_ts = time.mktime(updated.timetuple())

            # They are now in seconds, subtract and then divide by 60 to get minutes.
            bApi['minutesAgoUpdated'] = int(d1_ts - d2_ts) / 60

            #  new, recently moved or stale?
            isNewBus = bMarker,  # TODO: Does this even work?
            hasMovedSinceLastUpdate = False
            if isNewBus.__contains__(True):
                latChange = abs(float(bApi['lat']) - float(bus['Lat']))
                lonChange = abs(float(bApi['lon']) - float(bus['Lon']))
                if latChange > .0001 or lonChange > .0001:
                    hasMovedSinceLastUpdate = True

            # if bApi['minutesAgoUpdated'] < 2000:
            #     print("      : \"" + bApi['title'] + "\" : \"" + bApi['id'] + "\" : " + str(round(bApi['minutesAgoUpdated'], 2)) + " direction: " + bus['Direction'])

            #  update bus's model with new lat, lon
            bApi['lat'] = bus['Lat']
            bApi['lon'] = bus['Lon']
            bApi['direction'] = bus['Direction']  # add 'direction' to api_data
            self.buses[busIndex]['api_data'] = bApi  # update the bus at its index in self.buses

            #  If bus has been active within the last 30 minutes, then display it on the map.  In order for a bus to show up, it needs
            #  to be broadcasting its location and not be still for 30 or more minutes.
            if isNewBus.__contains__(True) and hasMovedSinceLastUpdate: # and 44.455 >= float(self.buses[busIndex]['api_data']['lat']):
                # if (type(bus.animation == "undefined") or !bus.animation.animating):
                # bMarker.setPosition(google.maps.LatLng(bApi.lat,bApi.lon));
                self.animateBus(self.buses[busIndex], {
                    'lat': bus['Lat'],
                    'lon': bus['Lon']
                })
                # }
                print(">     : \"" + bApi['title'] + "\" : \"" + bApi['id'] + "\" : " + str(round(bApi['minutesAgoUpdated'], 2)) + " direction: " + bus['Direction'] + " : " + self.buses[busIndex]['api_data']['lat'] + ", " + self.buses[busIndex]['api_data']['lon'])
            elif isNewBus.__contains__(False):

                #  update view with new GM Marker for bus
                marker = True  # None
                # marker = google.maps.Marker({
                #     'position': google.maps.LatLng(float(bApi['lat']), float(bApi['lon'])),
                #     'map': self.map,
                #     'icon': {
                #         'url': bApi['image_url'],
                #         'size': google.maps.Size(int(bApi['width']), int(bApi['height'])),
                #         'origin': google.maps.Point(0,0),
                #         'anchor': google.maps.Point(math.floor(bApi['width']/2), bApi['height'])
                #     },
                #     'title': bApi['title'],
                #     'zIndex': 3
                # })
                self.buses[busIndex]['gm_object'] = marker

                #  Uncomment to debug bus marker creation
                #  print("created bus: ", self.buses[busIndex])
                if bApi['minutesAgoUpdated'] < 30:
                    print(">New! : \"" + bApi['title'] + "\" : \"" + bApi['id'] + "\" : " + str(round(bApi['minutesAgoUpdated'], 2)) + " direction: " + bus['Direction'] + " : " + self.buses[busIndex]['api_data']['lat'] + ", " + self.buses[busIndex]['api_data']['lon'])

            # Bus notification
            # TODO: Make bus tracking a separate function and make location checking based off of a bus object.
            if self.classTrackingTime:
                thirtyminsbefore = datetime.datetime.now() > self.classTrackingTime - datetime.timedelta(minutes=30)
                threeminsbefore = datetime.datetime.now() > self.classTrackingTime - datetime.timedelta(minutes=3)
                # if latRange > 0.01
                busRange = {}
                busRange['lat'] = 44.4693  #44.4685   #44.47
                busRange['lon'] = -73.2151  #-73.2150  #-73.21
                busRange['direction'] = 360

                latRange = abs(float(busRange['lat']) - float(self.buses[busIndex]['api_data']['lat']))
                lonRange = abs(float(busRange['lon']) - float(self.buses[busIndex]['api_data']['lon']))
                dirRange = abs(int(busRange['direction'])) - int(self.buses[busIndex]['api_data']['direction'])
                # if 44.478 >= float(self.buses[busIndex]['api_data']['lat']) >= 44.465 and -73.208 >= float(self.buses[busIndex]['api_data']['lon']) >= -73.216 and (100 >= int(self.buses[busIndex]['api_data']['direction']) >= 0): #and thirtyminsbefore:
                if .005 > latRange and .005 > lonRange and 30 > dirRange:  # and thirtyminsbefore:
                    print(self.buses[busIndex]['api_data']['id'] + " is here!")
                    self.alertHere(self.buses[busIndex])
                    # TODO: Play sound
                    # TODO: Everything below should be put into a function to reset the tracking state.
                    self.classTrackingTime = None

                if threeminsbefore:
                    print("No approaching bus has been detected to give the user enough time to make it to their next class.")
                    self.classTrackingStatus = TRACKING_TIMEOUT
                    self.classTrackingTime = None

    # Implement Animate Marker Functionality
    # -------------------------------------
    # Rather than just set the position of a bus when it moves to a new location, these functions
    # smoothly animate it to the new location.

    def animateBus(self, bus, newLatLon):
        pass
        # bus.animation = {
        #     'animating': True,
        #     'i': 0,
        #     'deltaLat': (float(newLatLon['lat']) - float(bus['api_data']['lat'])) / 50,
        #     'deltaLon': (float(newLatLon['lon']) - float(bus['api_data']['lon'])) / 50
        # }
        # self._animateBus(bus)

    def _animateBus(self, bus):
        # update model
        bus['api_data']['lat'] = float(bus['api_data']['lat']) + bus['animation']['deltaLat']
        bus['api_data']['lon'] = float(bus['api_data']['lon']) + bus['animation']['deltaLon']

        # update view
        # latlng = google.maps.LatLng(bus['api_data']['lat'], bus['api_data']['lon'])
        # bus['gm_object'].setPosition(latlng)  # TODO: Find out how setPosition() is supposed to work
        # google.maps.event.trigger(self.map, 'resize')
        if bus['animation']['i'] != 50:
            bus['animation']['i'] = bus['animation']['i'] + 1
            # TODO: implement setTimeout https://codeburst.io/javascript-like-settimeout-functionality-in-python-18c4773fa1fd
            # setTimeout(function() {
            #     _animateBus(bus)
            # }, 10)

    def showCustomOverlays(self, zoom_level):
        pass
        # TODO: From here and down is not converted from JavaScript yet.
        # if (CC_SHUTTLE.overlays_initialized && CC_SHUTTLE.zoom_level == zoom_level) return;
        #
        # // update model's zoom_level
        # CC_SHUTTLE.zoom_level = zoom_level;
        #
        # // update view
        # CC_SHUTTLE.custom_overlays.forEach(function(overlay) {
        #     if (parseInt(overlay.api_data.zoom_level) === parseInt(zoom_level)) {
        #         if (overlay.gm_object === null) {
        #
        #             // Custom overlays are added to the map by defining a rectangular region using lat/lon coordinates of the upper left and bottom
        #             // right.  We're storing that info in bounds.
        #             var bounds = new google.maps.LatLngBounds(
        #                 new google.maps.LatLng(overlay.api_data.bounds_southwest_lat, overlay.api_data.bounds_southwest_lon),
        #                 new google.maps.LatLng(overlay.api_data.bounds_northeast_lat, overlay.api_data.bounds_northeast_lon)
        #             );
        #
        #             var gm_object = new ShuttleOverlay(bounds, overlay.api_data.image_url, map);
        #             overlay.gm_object = gm_object;
        #         }
        #         else {
        #             overlay.gm_object.show();
        #         }
        #     }
        #     else {
        #         if (overlay.gm_object !== null) {
        #             overlay.gm_object.hide();
        #         }
        #     }
        # });

    def scaleIcons(self, marker_scale):
        pass
        # if (CC_SHUTTLE.overlays_initialized && CC_SHUTTLE.marker_scale == marker_scale) return;
        #
        # // update model
        # CC_SHUTTLE.marker_scale = marker_scale;
        #
        # // update view icon size
        # CC_SHUTTLE.buses.forEach(function(bus) {
        #     if (!bus.gm_object) return;
        #     var newIconWidth = Math.floor(bus.api_data.width * mapSize.marker_scale),
        #         iconSizeDelta = bus.api_data.width - newIconWidth,
        #         newIconHeight;
        #     if (newIconWidth < bus.api_data.width) {
        #         newIconHeight = parseFloat(bus.api_data.height) - iconSizeDelta;
        #     }
        #     else {
        #         newIconHeight = parseFloat(bus.api_data.height) + iconSizeDelta;
        #     }
        #
        #     bus.gm_object.setIcon({
        #         url: bus.api_data.image_url,
        #         size: new google.maps.Size(parseFloat(bus.api_data.width), parseFloat(bus.api_data.height)),
        #         scaledSize: new google.maps.Size(newIconWidth, newIconHeight),
        #         origin: new google.maps.Point(0, 0),
        #         anchor: new google.maps.Point(Math.floor(newIconWidth/2), newIconHeight)
        #     });
        #
        # });

    def getMapSize(self):
        pass
        # var zoom = 15,
        #
        # // height should be applied to padding-bottom of the map_container div
        # // E.g., for a ratio 16:9, use 100%/16*9 = "56.25%"
        #     height = '50%',
        #     marker_scale = 1,
        #     viewWidth = $(window).width() + getScrollBarWidth(),
        #     viewHeight = $(window).height();
        #
        # if (viewWidth <= 350) {
        #     zoom =  14;
        #     height = '95%';
        #     marker_scale = .5;
        # }
        # else if (viewWidth <= 400) {
        #     zoom =  14;
        #     height = '85%';
        #     marker_scale = .5;
        # }
        # else if (viewWidth <= 455) {
        #     zoom =  14;
        #     height = '85%';
        #     marker_scale = .5;
        # }
        # else if (viewWidth <= 550) {
        #     zoom =  14;
        #     height = '75%';
        #     marker_scale = .5;
        # }
        # else if (viewWidth <= 768) {
        #     zoom =  14;
        #     height = '55%';
        #     marker_scale = .5;
        # }
        # else if (viewWidth <= 992) {
        #     zoom =  15;
        #     height = '75%';
        #     marker_scale = 1;
        # }
        # else if (viewWidth <= 1200) {
        #     zoom =  15;
        #     height = '65%';
        #     marker_scale = 1;
        # }
        #
        # // This tweak is for the /index/embedshuttle action, which is used on campus signage screens.  It
        # // ensures that the dimensions of the map matches the height of the viewport.
        # if (/embedshuttle/.test(window.location.href)) {
        #     height = '100vh';
        #     zoom = viewHeight < 540 || viewWidth < 555 ? 14 : 15;
        #     marker_scale = zoom == 14 ? .5 : 1;
        # }
        #
        # return {
        #     zoom: zoom,
        #     height: height,
        #     marker_scale: marker_scale
        # }

    def refreshOverlays(self):
        pass
        # mapSize = getMapSize();
        #
        # // Check if icons need to be resized
        # if (mapSize.marker_scale !== CC_SHUTTLE.marker_scale) {
        #     scaleIcons(mapSize.marker_scale);
        # }
        #
        # showCustomOverlays(mapSize.zoom);
        #
        # $(".map_container").css('padding-bottom',mapSize.height);
        #
        # map.setZoom(Math.floor(mapSize.zoom));
        #
        # setTimeout(function() {
        #     map.panTo(CC_SHUTTLE.center);
        # }, 100);
        #
        # google.maps.event.trigger(map, 'resize');
        #
        # CC_SHUTTLE.overlays_initialized = true;

    #  Utility Functions
    #  -----------------
    def getScrollBarWidth(self):
        pass
        # var $outer = $('<div>').css({visibility: 'hidden', width: 100, overflow: 'scroll'}).appendTo('body'),
        #     widthWithScroll = $('<div>').css({width: '100%'}).appendTo($outer).outerWidth();
        # $outer.remove();
        # return 100 - widthWithScroll;

    def setTracking(self, track=True):
        if track:
            eTime, event = self.pullCalendarClass()
            if not eTime:
                postmessage = " Not tracking."
                self.classTrackingStatus = event + postmessage
                self.classTrackingTime = None
            else:
                self.classTrackingTime = eTime
                self.className = event
                self.classTrackingStatus = "\"" + self.className + "\" at " + self.classTrackingTime.strftime("%I:%M %p")
        else:
            self.classTrackingStatus = TRACKING_DEFAULT
            self.classTrackingTime = None

    def alertHere(self, bus):
        self.classTrackingStatus = bus['api_data']['title'] + " " + bus['api_data']['id'] + " is here for " + self.className + "\" at " + self.classTrackingTime.strftime("%I:%M %p")

    #  Adapted from https://developers.google.com/calendar/quickstart/python
    def pullCalendarClass(self):
        """Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        if self.user.name is USER_DEFAULT:
            print('No user logged in, no class schedule loaded.')
            return None, TRACKING_NULL
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        pathname = "token_" + self.user.name + ".pickle"
        if os.path.exists(pathname):
            with open(pathname, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                    # 'credentials_' + self.user.name + '.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(pathname, 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.today().isoformat() + 'Z'  # 'Z' indicates UTC time
        tonight = datetime.datetime.combine(datetime.datetime.utcnow(),
                                            datetime.datetime.max.time()).isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting upcoming classes for today')
        calendars = service.calendarList().list().execute()  # grab all calendars
        calID = None
        for calendar in calendars['items']:
            if "Class Times" in calendar['summary']:
                calID = calendar['id']
        if not calID:
            print(
                "No \'Class Times\' calendar found for user. Please designate class times with a calendar that includes \'Class Times\' in the title.")
            return None, "No \'Class Times\' calendar found!"
        else:
            cal_day_result = service.events().list(calendarId=calID,
                                                   maxResults=10,  # Only retrieve one class.
                                                   timeMin=now, timeMax=tonight,
                                                   singleEvents=True,
                                                   orderBy="startTime").execute()

            event = None
            for course in cal_day_result['items']:
                if datetime.datetime.strptime(course['start']['dateTime'][:19].strip(),
                                              "%Y-%m-%dT%H:%M:%S") > datetime.datetime.today():
                    event = course  # Only retrieve one class from the list.
                    break

            if not event:
                print('No upcoming class found.')
                return None, "No upcoming classes!"
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start[:19].strip(), event['summary'])
            return datetime.datetime.strptime(start[:19].strip(), "%Y-%m-%dT%H:%M:%S"), event['summary']
