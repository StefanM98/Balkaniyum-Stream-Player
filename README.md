# Balkaniyum Custom Player

This is a custom player for [Balkaniyum](https://balkaniyum.tv/) written in Python. Balkaniyum is a internet TV provider featuring dozens of TV channels from ex Yugoslavia.

## Motivation
My grandfather is suffering from dementia and experiences a lot of difficulty navigiating the existing Balkaniyum players. 

I decided to write a custom player for Balkaniyum that is intentionally simplistic and straightforward to use without any assistance.

## How it works
1. When the script runs, it will automatically launch a headless chrome window using [selenium](https://pypi.org/project/selenium/) and navigate to the Balkaniyum login page.
2. It will then login to Balkaniyum using the credentials provided in `config.json` and immediately navigate to the first channel in the list and extract the stream URL.
3. The video will then be played in fullscreen using VLC player.

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

## Requirements
- Python 3.6+
- Selenium
- ChromeDriver (ChromeDriver 2.36+ is recommended)
- Balkaniyum Account with at least one channel package

## Get Started
1. Clone the repository
2. Install dependencies
```pip install -r requirements.txt```
3. Create and populate the `config.json` file from the example:
```cp config.example.json config.json```
4. Run `python play.py`

## License
This project is licensed under the MIT license. 