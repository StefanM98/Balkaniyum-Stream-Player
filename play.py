from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from pynput.keyboard import Key
from pynput.mouse import Button
import vlc
import json
import logging
import logging.handlers
import signal
import sys

def signal_handler(signal, frame):
    logger.debug("Signal received. Exiting...")
    exit_program()
    

def exit_program():
    global player
    global browser

    logger.debug("Terminating player...")
    if player:
        player.stop()
        player.release()

    logger.debug("Terminating browser...")
    if browser:
        browser.quit()

    logger.debug("Exiting...")
    sys.exit(0)

loginUrl = "https://www.balkaniyum.tv/srpski/tvuzivo.shtml"
playUrl = "http://www.balkaniyum.tv/srpski/tv/tvkanal_"
sessionCookie = ''

# TODO: Scrape the list of channels from the website
channels = ['RTRS', 'DMSAT', 'HappyTV']
channel_index = 0


# TODO: Cache a dictonary of channels and their corresponding media urls
# channels = {
#     'RTRS': 'http://www.balkaniyum.tv/srpski/tv/tvkanal_RTRS.m3u8',
#     'DMSAT': 'http://www.balkaniyum.tv/srpski/tv/tvkanal_DMSAT.m3u8',
#     'HappyTV': 'http://www.balkaniyum.tv/srpski/tv/tvkanal_HappyTV.m3u8'
# }

fetchedChannels = {}

# Setup signal handling
signal.signal(signal.SIGINT, signal_handler)

# Try to load settings from the config file
try:
    with open('config.json') as f:
        config = json.load(f)
        # Balkaniyum settings
        username = config['balkaniyum']['username']
        password = config['balkaniyum']['password']
        channels = config['balkaniyum']['channels']
        # Logger settings
        loggerLevel = config['logger']['level']
        syslogType = config['logger']['syslogType']
        syslogAddress = config['logger']['syslogAddress']
        syslogPort = config['logger']['syslogPort']
        # Browser settings
        headless = config['browser']['headless']
except Exception as e:
    print("Failed to load config file: " + str(e))
    sys.exit(1)


# Setup logging to syslog server
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = None
if syslogType == "udp":
    handler = logging.handlers.SysLogHandler(address=(syslogAddress, syslogPort))
elif syslogType == "local":
    handler = logging.handlers.SysLogHandler(address=syslogAddress)
else:
    logger.error("Invalid syslog type")
    exit_program()

formatter = logging.Formatter('%(name)s: %(levelname)s: %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)


# Get the logger level from the config file

if loggerLevel == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif loggerLevel == "INFO":
    logger.setLevel(logging.INFO)
elif loggerLevel == "WARNING":
    logger.setLevel(logging.WARNING)

# Configure Headless Chrome
options = Options()
options.headless = headless
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
browser = webdriver.Chrome(options=options)

def play_channel(chanel_index):
    global player
    is_set = set_channel(chanel_index)
    logger.debug("Playing stream " + channels[chanel_index])
    if is_set:
        status = player.play()
        if status == -1:
            logger.error("\nError playing Stream")
    else:
        logger.error("Failed to set media" + channels[chanel_index])

def get_channel_link(chanel_index):
    # Get the link for the channel
    return playUrl + channels[chanel_index] + ".shtml"

def get_video_url(chanel_index):
    # Get the video url
    browser.get(get_channel_link(chanel_index))
    browser.implicitly_wait(30)

    # Get the requests made to http://www.balkaniyum.tv/srpski/tv/tvkanal_*
    script_to_run = "var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network; performance.clearResourceTimings();"
    requests = browser.execute_script(script_to_run)

    url = False
    # From requests, return the list of objects with a name value starting with http://www.balkaniyum.tv/srpski/tv/tvkanal_{{channels[chanel_index]}}.m3u8
    for request in requests:
        if request['name'].startswith((playUrl + channels[chanel_index] + ".m3u8", playUrl + channels[chanel_index] + "_0.m3u8")):
            url = request['name']

    # Navigate to a blank page to avoid future requests
    browser.get("about:blank")

    return url

def set_channel(chanel_index):
    global instance
    global player  
    
    url = ""

    # Check if the channel is already fetched
    channelName = channels[chanel_index]
    if channelName in fetchedChannels: # use the cached url
        logger.debug("Channel " + channelName + " already loaded.")
        url = fetchedChannels[channelName]
    else: # fetch the channel
        logger.debug("Loading channel " + channelName)
        url = get_video_url(chanel_index)
        if url: fetchedChannels[channelName] = url
    
    if url:
        logger.info("\nSTREAM URL:\n" + url + "\n")
        media = instance.media_new(str(url))
        player.set_media(media)
        channel_title = "{} ({}/{})".format(channelName, chanel_index + 1, len(channels))
        player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, channel_title)
        return True
    else:
        logger.error("Failed to get URL for channel stream: " + channels[chanel_index])
        return False


def login():
    # Balkaniyum CSS selectors
    usernameTag = 'username'
    passwordTag = 'pass'

    # Login to the account
    usernameField = browser.find_element(by = By.ID, value = usernameTag)
    usernameField.send_keys(username)
    
    passwordField = browser.find_element(by = By.ID, value = passwordTag)
    passwordField.send_keys(password + Keys.RETURN)

    # Wait for the page to load
    browser.implicitly_wait(20)

    cookie = browser.get_cookie('sessionid')
    if cookie:
        logger.debug("Logged in successfully")
        # TODO: Store the cookie in a file and skip the login process next time
        # Save the cookie to a file
        # with open('cookie.json', 'w') as f:
        #     json.dump(cookie, f)
    else:
        logger.error("Failed to log in")
        exit_program()

    # Return the session cookie object
    return cookie

def next_channel():
    # Go to the next channel
    global channel_index

    if channel_index >= len(channels) - 1:
        channel_index = 0
    else:
        channel_index += 1

    player.set_pause(1)
    play_channel(channel_index)

def prev_channel():
    # Go to the previous channel
    global channel_index

    if channel_index <= 0:
        channel_index = len(channels) - 1
    else:
        channel_index -= 1

    player.set_pause(1)
    play_channel(channel_index)

def volume_up():
    # Increase the volume
    player.audio_set_volume(min(player.audio_get_volume() + 5, 100))

def volume_down():
    # Decrease the volume
    player.audio_set_volume(max(player.audio_get_volume() - 5, 0))



# Event handlers
def on_click(x, y, button, pressed):
    if pressed and button == Button.left: # left click
        logger.debug("Getting next channel...")
        next_channel()
    elif pressed and button == Button.right: # right click
        logger.debug("Getting previous channel...")
        prev_channel()

def on_scroll(x, y, dx, dy):
    if dy > 0:
        volume_up()
    else:
        volume_down()

def on_key_release(key):
    global terminated
    if key == Key.esc:  # Exit the program
        exit_program()
    elif key == 'f':    # Toggle fullscreen
        logger.debug("Toggling fullscreen...")
        player.toggle_fullscreen()


# Setup signal handler and event listeners
key_listener = KeyboardListener(on_release=on_key_release)
mouse_listener = MouseListener(on_click=on_click, on_scroll=on_scroll)
key_listener.daemon = True
mouse_listener.daemon = True

# Start VLC instance
instance = vlc.Instance("--sub-source=marq --video-title-show --video-title-timeout 1")
player = instance.media_player_new()
player.video_set_marquee_int(vlc.VideoMarqueeOption.Position, 6)
player.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, 6*1000)
player.video_set_marquee_int(vlc.VideoMarqueeOption.Size, 64)
player.toggle_fullscreen()

# Authenticate and get the session cookie
browser.get(loginUrl)
sessionCookie = login()
logger.info("Retrieved Balkaniyum session cookie: " + str(sessionCookie))

# Start the event listeners
key_listener.start()
mouse_listener.start()

# Play the first channel
play_channel(channel_index)

key_listener.join()
mouse_listener.join()
