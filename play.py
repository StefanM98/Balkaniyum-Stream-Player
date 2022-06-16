from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from pynput.keyboard import Key
from pynput.mouse import Button, Controller as MouseController
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

    key_listener.join()
    mouse_listener.join()
    key_listener.stop()
    mouse_listener.stop()

    logger.debug("Exiting...")
    sys.exit(0)

loginUrl = "https://www.balkaniyum.tv/srpski/tv/tvuzivo.shtml"
playUrl = "http://www.balkaniyum.tv/srpski/tv/tvkanal_"

# Setup signal handling
signal.signal(signal.SIGINT, signal_handler)

# Try to load settings from the config file
try:
    with open('config.json') as f:
        config = json.load(f)
        # Balkaniyum settings
        username = config['balkaniyum']['username']
        password = config['balkaniyum']['password']
        startChannel = config['balkaniyum']['startChannel']
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
options = webdriver.ChromeOptions()
options.headless = headless
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")

service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service = service, options = options)

def play_channel(chanel_index):
    global player
    global channels

    player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, "LOADING...")

    is_set = set_channel(chanel_index)
    logger.debug("Playing stream " + channels[chanel_index])
    if is_set:
        status = player.play()
        if status == -1:
            logger.error("Error playing Stream")
            player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, "ERROR")
    else:
        logger.error("Failed to set media for channel " + channels[chanel_index])
        player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, "ERROR")

def get_channel_link(channel_name):
    # Get the link for the channel
    return playUrl + channel_name + ".shtml"

def load_channels():
    global browser
    global fetched_channels

    logger.info("Loading channels...")
    # try to load channels from the debug file
    try:
        with open('channels.json') as f:
            all_channels = json.load(f)
            logger.info("Loaded {0} channels from file.".format(len(all_channels)))
            return all_channels
    except Exception as e:
        logger.warning("Failed to load channels file: " + str(e))

    browser.implicitly_wait(30)
    channel_list = browser.find_element(by = By.ID, value = "channels")
    channelContainers = channel_list.find_elements(by = By.CLASS_NAME, value = "channel")
    browser.implicitly_wait(30)

    channelNames = []

    for container in channelContainers:
        # Get the channel name from id
        channelName = container.get_attribute("id")  

        # Only include live channels (without _NUM suffix)
        if channelName.endswith(("_6", "_9", "_16")):
            continue

        # Remove the "channel_" prefix and _0 suffix if present
        channelNames.append(channelName[8:].replace("_0", "")) 

    logger.info(
        "Loaded {0} channels. Checking availability..."
        .format(str(len(channelNames))))

    invalid_channels = []

    for channelName in channelNames:
        url = get_video_url(channelName)
        error = None
        try:
            error = browser.find_element(
                by = By.XPATH, 
                value = "//div[@id='player']//a[@href='https://www.balkaniyum.tv/srpski/pretplata/paketi.shtml']"
            )
            logger.debug("Channel {0} is not in the user's current channel package.".format(channelName))
        except NoSuchElementException:
            logger.debug("Channel {0} is in channel package.".format(channelName))
        
        if url is None or error is not None:
            logger.warning("Channel {0} is unavailable.".format(channelName))
            invalid_channels.append(channelName)
        else:
            logger.info("Channel {0} is available. URL: {1}".format(channelName, url))
            fetched_channels[channelName] = url

    # Remove unavailable channels from the list
    for channel in invalid_channels:
        channelNames.remove(channel)

    # Write the channels to a file
    with open('channels.json', 'w') as f:
        json.dump(channelNames, f)

    logger.info("{0} channels are available.".format(str(len(channelNames))))
    logger.info("{0} channels are unavailable.".format(str(len(invalid_channels))))
        
    return channelNames

def get_video_url(channel_name):
    # Navigate to the video url
    browser.get(get_channel_link(channel_name))
    
    browser.implicitly_wait(5)

    # Get the requests made to http://www.balkaniyum.tv/srpski/tv/tvkanal_*
    script_to_run = "var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network; performance.clearResourceTimings();"
    requests = browser.execute_script(script_to_run)

    url = None
    # From requests, return the list of objects with a name value starting with: 
    # http://www.balkaniyum.tv/srpski/tv/tvkanal_{{CHANNEL_NAME}}.m3u8
    for request in requests:
        baseUrl = playUrl + channel_name
        if request['name'].startswith((
            (baseUrl + "_0.m3u8"), 
            (baseUrl + ".m3u8")
        )):
            url = request['name']

    return url

def set_channel(chanel_index):
    global instance
    global player  
    global channels
    global fetched_channels
    
    url = False

    # Check if the channel is already fetched
    channelName = channels[chanel_index]
    if channelName in fetched_channels: # use the cached url
        logger.debug("Channel " + channelName + " already loaded. Using cached url.")
        url = fetched_channels[channelName]
    else: # fetch the channel
        logger.debug("Loading channel " + channelName)
        url = get_video_url(channelName)
        if url: fetched_channels[channelName] = url
    
    if url:
        logger.debug("STREAM URL: " + url)
        media = instance.media_new(str(url))
        player.set_media(media)
        channel_title = "{} ({}/{})".format(channelName, chanel_index + 1, len(channels))
        player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, channel_title)
        return True
    else:
        logger.error("Failed to get URL for channel stream: " + channels[chanel_index])
        player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, "ERROR")
        
        # Clear the channel from fetched_channels
        if channelName in fetched_channels:
            del fetched_channels[channelName]

        return False


def login():
    # Login to the account
    usernameField = browser.find_element(by = By.ID, value = "username")
    usernameField.send_keys(username)
    
    passwordField = browser.find_element(by = By.ID, value = "pass")
    passwordField.send_keys(password + Keys.RETURN)

    # Wait for the page to load
    browser.implicitly_wait(20)

    cookie = browser.get_cookie("sessionid")
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
    global channels

    if channel_index >= len(channels) - 1:
        channel_index = 0
    else:
        channel_index += 1

    play_channel(channel_index)


def prev_channel():
    # Go to the previous channel
    global channel_index
    global channels

    if channel_index <= 0:
        channel_index = len(channels) - 1
    else:
        channel_index -= 1

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
        logger.debug("User exiting program...")
        exit_program()
    elif 'char' in dir(key): # check if char method exists
        if key.char == 'f' or key.char == 'F': 
            logger.debug("Toggling fullscreen...")
            player.toggle_fullscreen()


# Setup signal handler and event listeners
key_listener = KeyboardListener(on_release=on_key_release)
mouse_listener = MouseListener(on_click=on_click, on_scroll=on_scroll)
key_listener.daemon = True
mouse_listener.daemon = True

# Start VLC instance
instance = vlc.Instance("--intf rc --rc-host 127.0.0.1:44500 --video-on-top --mouse-hide-timeout=0 --sub-source=marq --video-title-show --video-title-timeout 1")
player = instance.media_player_new()
player.video_set_marquee_int(vlc.VideoMarqueeOption.Position, 6)
player.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, 6*1000)
player.video_set_marquee_int(vlc.VideoMarqueeOption.Size, 64)
player.toggle_fullscreen()
player.video_set_mouse_input(False)

# Authenticate and get the session cookie
browser.get(loginUrl)
sessionCookie = login()
logger.debug("Retrieved Balkaniyum session cookie: " + str(sessionCookie))

# Load the available channels
fetched_channels = {}
channels = load_channels()

# Play the start channel
channel_index = 0
try:
    channel_index = channels.index(startChannel)
except ValueError:
    logger.error("Failed to find the start channel: " + str(startChannel))
    player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, "ERROR")
lastState = player.get_state()
play_channel(channel_index)

# Start the event listeners
key_listener.start()
mouse_listener.start()

# Navigate to a blank page to avoid further requests
browser.get("about:blank")

# Start the main loop
mouse = MouseController()

while True:
    state = player.get_state()
    if lastState != state:
        lastState = state 
        logger.debug("Player state changed: {0}-> {1}".format(str(lastState), str(state)))

    # mouse.position = (0, 0)
    # time.sleep(0.1)