# BalkaniYUm.TV Custom Player

This is a custom, lightweight player for [BalkaniYUm.TV](https://balkaniyum.tv/) written in Python. BalkaniYUm is a internet TV provider featuring dozens of TV channels from ex Yugoslavia.

**NOTE:** I am not affiliated with BalkaniYUm or any of its channels. This is a personal project I have written for my own use. Please refer to the BalkaniYUm website for their offical terms of use. Keep in mind this API is unofficial and some methods are simply scraping BalkaniYUm pages. This naturally makes the library more fragile, so keep an eye out for frequent updates.

## Motivation
My grandfather is suffering from dementia and experiences a lot of difficulty navigiating the existing BalkaniYUm players. After realizing the Amazon Fire TV and Roku remotes were too complicated, I decided to build him this custom player which is very simple and straightforward for him to use without any assistance using a simple two-button PC mouse.

## How it works
1. On the first run, it will automatically launch a headless chrome window using [selenium](https://pypi.org/project/selenium/) and navigate to the BalkaniYUm login page.
2. It will then login to BalkaniYUm using the credentials provided in `config.json`, identify the channels available in the user's package, and store the URLs of each of the channel streams.
3. Finally, VLC Media Player will be launched and the user's default channel will play.

## Features
- Configurable logging
- Stream URL caching (for faster channel switching to previously viewed channels)
- Current channel overlay in top right corner
- Requires only a mouse to opperate and runs without a desktop environment

## Controls
| Key | Action |
| --- | --- |
| Scroll-Up | Increase volume (5%) |
| Scroll-Down | Decrease volume (5%) |
| Left Click | Previous channel |
| Right Click | Next channel |
| f | Toggle fullscreen |
| ESC | Exit player |

## Requirements
- BalkaniYUm Account with at least one channel package
- Python 3.6+
- Chrome or Chromium browser
- ChromeDriver (ChromeDriver 2.36+ is recommended)
- Selenium

## Get Started
1. Clone the repository
2. Install dependencies
    ```
    pip install -r requirements.txt
    ```
3. Create and populate the `config.json` file from the example:
    ```
    cp config.example.json config.json
    ```
4. Run 
    ```
    python play.py
    ```

## License
This project is licensed under the MIT license. 