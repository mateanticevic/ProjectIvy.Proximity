#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import datetime
import asyncio
import requests
import websockets
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'assets')
font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'fonts')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
import time
import traceback
from PIL import Image, ImageDraw, ImageFont, ImageOps
from waveshare_epd import epd2in13_V2
from geopy import distance

start_time = datetime.datetime.now()

logging.basicConfig(level=logging.DEBUG, handlers=[
    logging.FileHandler('/var/log/proximity/{log_file_name}.txt'.format(log_file_name = start_time.strftime('%Y-%m-%d_%H:%M:%S'))),
    logging.StreamHandler()
])

font = ImageFont.truetype(os.path.join(font_dir, 'font.ttc'), 20)

home_location = (45.799502, 15.909997)
end_in_x_seconds = 100
draw_text_x = 115
draw_text_y_first = 20
draw_text_y_second = 50
draw_text_y_third = 80

string_x_km_away = "{distance:.0f}km away"
string_x_m_away = "{distance:.0f}m away"
string_home_location = "in {name}"

class EndOfProgramException(Exception):
    pass

class Location:
    def __init__(self, tracking, name):
        self.tracking = tracking
        self.name = name
    def __eq__(self, other):
        return self.tracking == other.tracking

def endIfTimeElapsed():
    if (datetime.datetime.now() - start_time).total_seconds() > end_in_x_seconds:
        logging.info('ending program')
        raise EndOfProgramException()

def drawImage(epd, location):
    image_name = 'away.bmp' if location.name is None else 'home.bmp'
    image = Image.open(os.path.join(assets_dir, image_name))
    draw = ImageDraw.Draw(image)
    draw.text((draw_text_x, draw_text_y_first), 'Mate is', font = font, fill = 0)

    if location.name is None:
        distance_between = distance.distance(location.tracking, home_location).km
        line = string_x_m_away if distance_between < 1 else string_x_km_away
        distance_formated = distance_between * 1000 if distance_between < 1 else distance_between
        second_line = line.format(distance = distance_formated)
    else:
        second_line = 'home'

    logging.info(second_line)
    draw.text((draw_text_x, draw_text_y_second), second_line, font = font, fill = 0)

    if location.name is not None:
        draw.text((draw_text_x, draw_text_y_third), string_home_location.format(name = location.name), font = font, fill = 0)

    epd.display(epd.getbuffer(ImageOps.flip(image)))

    return image

def getLastTracking():
    uri = "https://api2.anticevic.net/tracking/lastLocation"
    response = requests.get(uri, headers={"Authorization": os.environ['PROJECT_IVY_TOKEN']})
    json = response.json()

    return Location((json["tracking"]["lat"], json["tracking"]["lng"]), json["location"]["name"] if json["location"] is not None else None)

try:
    logging.info("main started")
    
    epd = epd2in13_V2.EPD()
    logging.info("init and clear")
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)

    lastLocation = Location((0,0), None)

    while True:
        location = getLastTracking()
        if location != lastLocation:
            logging.info("new location received")
            img = drawImage(epd, location)
            lastLocation = location
        endIfTimeElapsed()

        logging.info("waiting 10s")
        time.sleep(10)
    
    logging.info("1.Drawing on the image...")
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame    
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([(0,0),(50,50)],outline = 0)
    draw.rectangle([(55,0),(100,50)],fill = 0)
    draw.line([(0,0),(50,50)], fill = 0,width = 1)
    draw.line([(0,50),(50,0)], fill = 0,width = 1)
    draw.chord((10, 60, 50, 100), 0, 360, fill = 0)
    draw.ellipse((55, 60, 95, 100), outline = 0)
    draw.pieslice((55, 60, 95, 100), 90, 180, outline = 0)
    draw.pieslice((55, 60, 95, 100), 270, 360, fill = 0)
    draw.polygon([(110,0),(110,50),(150,25)],outline = 0)
    draw.polygon([(190,0),(190,50),(150,25)],fill = 0)
    draw.text((120, 60), 'e-Paper demo', font = font, fill = 0)
    draw.text((110, 90), u'微雪电子', font = font, fill = 0)
    epd.display(epd.getbuffer(image))
    time.sleep(2)
    
    # # partial update
    logging.info("4.show time...")
    time_image = Image.new('1', (epd.height, epd.width), 255)
    time_draw = ImageDraw.Draw(time_image)
    
    epd.init(epd.FULL_UPDATE)
    epd.displayPartBaseImage(epd.getbuffer(time_image))
    
    epd.init(epd.PART_UPDATE)
    num = 0
    while (True):
        time_draw.rectangle((120, 80, 220, 105), fill = 255)
        time_draw.text((120, 80), time.strftime('%H:%M:%S'), font = font, fill = 0)
        epd.displayPartial(epd.getbuffer(time_image))
        num = num + 1
        if(num == 10):
            break
    
    logging.info("Clear...")
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)
    
    logging.info("Goto Sleep...")
    epd.sleep()
    epd.Dev_exit()

except EndOfProgramException:
    exit()
        
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in13_V2.epdconfig.module_exit()
    exit()
