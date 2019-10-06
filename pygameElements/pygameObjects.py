import sys
import platform
import pandas
import matplotlib
import matplotlib.pyplot
import matplotlib.backends.backend_agg as agg
import os
import datetime
import socket
import pygame
from pygame.locals import *
from PIL import Image
from climata.usgs import DailyValueIO
import requests
from bs4 import BeautifulSoup

# from html.parser import HTMLParser
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
PATH_IMAGE_GRAPH_TEMPERATURE = os.path.join(os.path.join(DIR_BASE, 'resource'), 'graph_temp_lake.png')
PATH_IMAGE_BURLINGTON_LEFT = os.path.join(os.path.join(DIR_BASE, 'resource'), 'burlington_left.jpg')
PATH_IMAGE_BURLINGTON_RIGHT = os.path.join(os.path.join(DIR_BASE, 'resource'), 'burlington_right.jpg')
PATH_IMAGE_SPONSOR = os.path.join(os.path.join(DIR_BASE, 'resource'), 'sponsor.jpg')
PATH_ICON_SLIDESHOW = os.path.join(os.path.join(DIR_BASE, 'resource'), 'mode_slideshow.png')
PATH_ICON_MANA = os.path.join(os.path.join(DIR_BASE, 'resource'), 'Mana.png')

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
pygame.time.set_timer(USEREVENT + 3, 6000)  # Every minute, refresh the clock.
# pygame.time.set_timer(USEREVENT + 4, 0)  # Not an event that needs to be set here, but just pointing out it exists.
# pygame.time.set_timer(USEREVENT + 5, 0)  # Not an event that needs to be set here, but just pointing out it exists.
pygame.time.set_timer(USEREVENT + 6, 900000)  # Every 15 minutes, download burlington pictures.

# Fonts
# print(pygame.font.get_fonts())
if platform.system() == "Windows":
    print("Windows fonts")
    #  TODO: Fix directory access outside of local directory
    FONT_FALLOUT = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'r_fallouty.ttf'), 30)
    FONT_BM = pygame.font.Font(os.path.join(DIR_BASE, 'resource/fonts/', 'din1451alt.ttf'), 10)
elif platform.system() == "Linux":
    pygame.mouse.set_visible(False)
    print("Linux fonts")
    FONT_FALLOUT = pygame.font.Font('resource/fonts/r_fallouty.ttf', 30)
    FONT_BM = pygame.font.Font('resource/fonts/din1451alt.ttf', 10)
else:
    print("default fonts")
    FONT_FALLOUT = pygame.font.SysFont(None, 30)
    FONT_BM = pygame.font.SysFont(None, 13)
#  TODO: Fix Font not working on Raspberry Pi

screen = pygame.display.set_mode(DIM_SCREEN)

# colors
COLOR_BLACK = 0, 0, 0
COLOR_WHITE = 255, 255, 255
COLOR_GRAY_19 = 31, 31, 31
COLOR_GRAY_21 = 54, 54, 54
COLOR_GRAY_41 = 105, 105, 105
COLOR_ORANGE = 251, 126, 20
COLOR_LAVENDER = 230, 230, 250

# urls
URL_MAINSTREET = "https://www.mainstreetlanding.com"

# Icon Constants
ICON_SLIDESHOW = 0  # Slideshow Icon
ICON_TEST = 1  # Slideshow Icon

# Content switching
CONTENT_TEMPERATURE = {"number":    0,
                       "name":      "Temperature: Lake"}
CONTENT_PICTURE = {"number":    1,
                   "name":      "Burlington Live Camera"}
CONTENT_MAINSTREET = {"number": 2,
                      "name":   "Mainstreet Landing Movies"}
CONTENT_SHUTTLE = {"number":    3,
                   "name":      "Shuttle Map"}


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
    def __init__(self, color=COLOR_GRAY_19, dim=(150, 450, 100, 50), width=1):
        self.color = color
        self.dim = dim
        self.width = width
        self.state = False

    def active(self, mouse):
        if self.dim[0] + self.dim[2] > mouse['position'][0] > self.dim[0]\
                and self.dim[1] + self.dim[3] > mouse['position'][1] > self.dim[1]\
                and mouse['click']:
            pygame.draw.rect(screen, COLOR_ORANGE, self.dim)
            self.state = True
        else:
            pygame.draw.rect(screen, self.color, self.dim, self.width)
            self.state = False


class Page:
    def __init__(self, background=pygame.transform.scale(pygame.image.load(PATH_IMAGE_OFFLINE),
                                                         DIM_SCREEN), buttons=[]):
        self.background = background
        self.buttons = buttons


class Environment:
    def __init__(self):
        # Initialize data buffers
        self.data_temperature_water = None
        self.mouse = {"position": (0, 0),
                      "click": False}
        self.movies = []
        self.gui = {}
        self.gui_picture_toggle = True

        self.sponsor = Card
        # Define content list TODO: Settings - Save enabled/disabled content
        self.contentList = [[CONTENT_TEMPERATURE, PATH_IMAGE_GRAPH_TEMPERATURE, lambda func: self.surf_plot()],
                            [CONTENT_PICTURE, PATH_IMAGE_BURLINGTON_LEFT, lambda func: self.surf_picture()],
                            # [CONTENT_MAINSTREET['number'], PATH_IMAGE_STARTUP, lambda func: self.surf_mainstreet()],
                            # [CONTENT_SHUTTLE['number'], PATH_IMAGE_STARTUP, lambda func: self.surf_shuttle()]
                            ]
        self.surf_background = pygame.transform.scale(pygame.image.load(PATH_IMAGE_OFFLINE),
                                                      DIM_SCREEN)  # Set surface image to offline
        self.time_text = (None, None)  # Time Buffer
        self.slideshow = True  # slideshow toggler
        self.buttonDelay = False  # Button delay
        self.backlight = True  # Backlight is On
        self.cIndex = CONTENT_TEMPERATURE['number']  # Start with lake temperature

        # Icons
        self.icon = [pygame.transform.scale(pygame.image.load(PATH_ICON_SLIDESHOW),
                                            DIM_ICON),  # Slideshow
                     pygame.transform.scale(pygame.image.load(PATH_ICON_MANA), DIM_ICON)
                     # Test
                     ]
        # Pull data from internet/system
        self.pullTime()  # Set time
        self.pullData()  # Download data
        self.graph_temp()  # Graph data
        self.pullImageBurlington()  # Download Burlington images

        # You have to run a set-surface function before the slides start up.
        self.surf_background = pygame.image.load(self.contentList[self.cIndex][1])
        # self.surf_startup()  # Start with lake temperature
        if platform.system() == "Linux":
            # Only use the sleep function for raspberry pi
            pygame.time.set_timer(USEREVENT + 5, 60000)  # 1 minute # 600000) # 10 minutes

    def menu(self):
        crashed = False
        while not crashed:
            for event in pygame.event.get():
                # Every 8 hours, download data
                if event.type == USEREVENT + 1:  # Every 8 hours, download new data and render images.
                    self.pullData()
                    self.graph_temp()
                if event.type == USEREVENT + 2 and self.slideshow:  # 10 seconds # 120000)  # Every 10 seconds, switch the surface.
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
                if event.type == pygame.QUIT:
                    crashed = True

                # mouse
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse['click'] = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse['click'] = False
                else:
                    self.mouse['click'] = False

                if event.type == pygame.KEYDOWN and not self.buttonDelay:
                    if platform.system() == "Linux":
                        self.reset_backlight()
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
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
            # TODO: Move changes to the gui buttons to out here.

            # TODO: Touching the screen makes the screen refresh and the slideshow time reset
            # if self.slideshow:


            # Scan the buttons
            for k in button_map:  # TODO: IMPLEMENT BUTTONS FOR ALL PI PLATFORMS
                if not GPIO.input(k) and not self.buttonDelay and DIST == "000e":  # platform.system() == "Linux":
                    if k == button_map[0]:
                        pygame.quit()
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
            self.cIndex = self.contentList.index(self.contentList[self.cIndex - 1])  # Iterate cIndex backwards
        else:
            if self.cIndex + 1 >= len(self.contentList):  # Iterate cIndex forwards
                self.cIndex = 0
            else:
                self.cIndex = self.cIndex + 1
        print(self.contentList[self.cIndex][0]['name'])
        self.surf_background = pygame.image.load(self.contentList[self.cIndex][1])  # set background

    def refresh(self):
        screen.blit(self.surf_background, (0, 0))  # Background

        self.contentList[self.cIndex][2](self)  # run the content function

        # Icons Todo: make icon bar toggleable in options
        pygame.draw.rect(screen, COLOR_WHITE, pygame.Rect((0, 0), (DIM_SCREEN[0], 13)), 0)  # Icon bar backing
        if self.buttonDelay:  # if the buttonDelay bool is enabled, display the icon.
            screen.blit(self.icon[ICON_TEST], (59, 1))
        if self.slideshow:  # if the slideshow bool is enabled, display the icon.
            screen.blit(self.icon[ICON_SLIDESHOW], (44, 1))

        # Content Name
        cont__name = FONT_BM.render(self.contentList[self.cIndex][0]['name'], True, COLOR_BLACK)
        screen.blit(cont__name, ((DIM_SCREEN[0]-cont__name.get_size()[0])-2, 1))

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
        # https://stackoverflow.com/questions/6339057/draw-a-transparent-rectangle-in-pygame
        # Set buttons
        # buttons = [Button(COLOR_WHITE, pygame.Rect((DIM_SCREEN[0] - 60, 0), (60, DIM_SCREEN[1])), 0),
        #            Button(COLOR_WHITE, pygame.Rect((0, 0), (60, DIM_SCREEN[1])), 0)
        #            ]
        # self.page = Page(pygame.image.load(PATH_IMAGE_BURLINGTON_LEFT), buttons)
        self.gui.clear()  # clear gui
        if self.gui_picture_toggle:
            self.gui['button_right'] = Button(COLOR_WHITE, pygame.Rect((DIM_SCREEN[0]-60, 0), (60, DIM_SCREEN[1])), 0)# (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        else:
            self.gui['button_left'] = Button(COLOR_WHITE, pygame.Rect((0, 0), (60, DIM_SCREEN[1])), 0)# (COLOR_GRAY_19, (150, 450, 100, 50), width=1)
        for element in self.gui.items():
            element[1].active(self.mouse)
            if element[1].state:  # if clicked
                if element[0] == "button_left":
                    self.contentList[self.cIndex][1] = PATH_IMAGE_BURLINGTON_LEFT
                elif element[0] == "button_right":
                    self.contentList[self.cIndex][1] = PATH_IMAGE_BURLINGTON_RIGHT
                self.gui_picture_toggle = not self.gui_picture_toggle
        self.surf_background = pygame.image.load(self.contentList[self.cIndex][1])  # load the background anyways
        # TODO: Either remove self.gui or clear it in self.setContent

    def surf_mainstreet(self):
        # TODO: https://www.mainstreetlanding.com/performing-arts-center/daily-rental-information/movies-at-main-street-landing/
        # TODO: https://stackoverflow.com/questions/18294711/extracting-images-from-html-pages-with-python
        # TODO: Make a sub-screen that allows you to flip through the content held in the movie cards.
        # and scroll through movie descriptions
        pass

    def surf_shuttle(self):  # TODO: https://shuttle.champlain.edu/
        pass

    def surf_plot(self):
        pass

    def graph_temp(self):
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
        self.resizeImage(PATH_IMAGE_SPONSOR, "JPEG", self.scale(constraintH=80, size=im.size))
        self.sponsor = Card(
            title=str(sponsor_raw.contents[1].contents[1].contents[1].attrs['alt']),
            # TODO: Parse description html (maybe allow it to italicize when printing it?)
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

            self.resizeImage(movieImagePath, "JPEG", self.scale(constraintH=80, size=im.size))

            self.movies.append(Card(
                title=str(listing.contents[1].contents[3].contents[1].contents[0]),
                # TODO: Parse description html (maybe allow it to italicize when printing it?)
                desc=str(listing.contents[1].contents[3].contents[5]),
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

    def imChecker(self, iSize, im, movieImagePath):
        try:
            im = Image.open(movieImagePath)  # Rescale the image to fit into the screen
        except IOError as e:
            im = None
            print(e)
            print("Attempting \"", iSize[28:30], "\" next.")
        return im

    def pullImageBurlington(self):
        # Download image from Camnet
        downloadImage('burlington_left.jpg', 'https://hazecam.net/images/large/burlington_left.jpg')
        self.resizeImage(PATH_IMAGE_BURLINGTON_LEFT, "JPEG", DIM_SCREEN)
        downloadImage('burlington_right.jpg', 'https://hazecam.net/images/large/burlington_right.jpg')
        self.resizeImage(PATH_IMAGE_BURLINGTON_RIGHT, "JPEG", DIM_SCREEN)

    def resizeImage(self, imgPath, imgType, imgDim):
        im = Image.open(imgPath)
        im_resized = im.resize(imgDim, Image.ANTIALIAS)
        im_resized.save(imgPath, imgType)

    def pullTime(self):
        d = datetime.datetime.strptime(str(datetime.datetime.now().time()), "%H:%M:%S.%f")
        self.time_text = (
            FONT_BM.render(d.strftime("%I:%M"), True, COLOR_BLACK), FONT_BM.render(d.strftime("%p"), True, COLOR_BLACK))

    def toggleSlideshow(self):
        if self.slideshow:  # if the slideshow bool is enabled:
            pygame.time.set_timer(USEREVENT + 2, 0)  # turn off the slideshow userevent
        else:  # if the slideshow bool is disabled:
            pygame.time.set_timer(USEREVENT + 2, 10000)  # turn on the slideshow userevent
        self.slideshow = not self.slideshow  # toggle the slideshow bool

    def scale(self, constraintH, size):
        return [int(size[0] / (size[1] / constraintH)), constraintH]
