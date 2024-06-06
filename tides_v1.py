#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
# Directories
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')

if os.path.exists(libdir):
    sys.path.append(libdir)

import time
import requests
import logging
from datetime import datetime
from waveshare_epd import epd2in7_V2
from PIL import Image, ImageDraw, ImageFont
import traceback
import subprocess

logging.basicConfig(level=logging.DEBUG)

def check_wifi():
    try:
        subprocess.check_call(['ping', '-c', '1', '8.8.8.8'])
        return True
    except subprocess.CalledProcessError:
        return False

def get_tide_data():
    try:
        response = requests.get('https://n8n.comedepreville.fr/webhook/f56a8cbc-f7be-41f8-ab13-4fd794cf7ddb/marees/1')
        response.raise_for_status()
        return response.json()[0]
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

def calculate_time_difference(tide_time_millis):
    tide_time = datetime.fromtimestamp(tide_time_millis / 1000)  # Convert milliseconds to seconds
    now = datetime.now()
    delta = tide_time - now
    return delta.total_seconds() / 3600  # Return difference in hours

def get_image_filename(delta_hours, tide_type):
    delta_hours = round(delta_hours)
    if tide_type == "haute":
        if delta_hours == 0:
            return '6.bmp'
        elif delta_hours == 6:
            return '0.bmp'
        else:
            for i in range(1, 5):
                if delta_hours == i:
                    return f'montante_{6-i}.bmp'
    else:  # tide_type == "basse"
        if delta_hours == 0:
            return '0.bmp'
        elif delta_hours == 6:
            return '6.bmp'
        else:
            for i in range(1, 5):
                if delta_hours == i:
                    return f'descendante_{i}.bmp'

def main():
    try:
        logging.info("Starting tide display script")

        # Initialize e-Paper display
        epd = epd2in7_V2.EPD()
        epd.init()
        font = ImageFont.truetype(os.path.join(picdir, 'heavitas.ttf'), 18)

        if not check_wifi():
            logging.info("No WiFi connection, displaying no_connexion.bmp")
            error_image = Image.open(os.path.join(picdir, 'no_connexion.bmp'))
            epd.display(epd.getbuffer(error_image))
            epd.sleep()
            return

        tide_data = get_tide_data()
        if tide_data is None:
            logging.error("Failed to retrieve tide data")
            epd.sleep()
            return

        tide_time_millis = tide_data["millis"]
        tide_type = tide_data["type"]
        tide_text = tide_data["heure"]
        tide_coefficient = tide_data["coef"]
        delta_hours = calculate_time_difference(tide_time_millis)
        image_filename = get_image_filename(delta_hours, tide_type)

        logging.info(f"Displaying {image_filename} for tide type {tide_type} with delta {delta_hours:.2f} hours")
        #Add image
        image = Image.open(os.path.join(picdir, image_filename))
        #Add tide time up right
        draw = ImageDraw.Draw(image)
        text = tide_text
        text_width, text_height = draw.textsize(text, font=font)
        x = epd.height - text_width - 10
        y = 10
        draw.text((x, y), text, font=font, fill=0)
        
        #Add tide coef bottom left in white
        text = str(tide_coefficient)
        text_width, text_height = draw.textsize(text, font=font)
        y = 10
        x = 10
        draw.text((x, y), text, font=font, fill=0)
        
        epd.display(epd.getbuffer(image))

        logging.info("Clearing and entering sleep mode")
        epd.sleep()

    except IOError as e:
        logging.error(f"IOError: {e}")
    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        epd2in7_V2.epdconfig.module_exit(cleanup=True)
        exit()

if __name__ == "__main__":
    main()
