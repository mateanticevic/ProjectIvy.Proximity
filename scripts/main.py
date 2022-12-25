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
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V2
from geopy import distance

start_time = datetime.datetime.now()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', handlers=[
    logging.FileHandler('/var/log/proximity/{log_file_name}.txt'.format(log_file_name = start_time.strftime('%Y-%m-%d_%H:%M:%S'))),
    logging.StreamHandler()
])

font = ImageFont.truetype(os.path.join(font_dir, 'font.ttc'), 20)

home_location = (44.117965, 15.234143)
end_in_x_seconds = 3600 * 24
draw_text_x = 120
draw_text_y_first = 20
draw_text_y_second = 50
draw_text_y_third = 80

string_user_first_line = "Mate is"
string_x_km_away = "{distance:.0f}km away"
string_x_m_away = "{distance:.0f}m away"
string_home_location = "at {name}"
string_response_took = "http response took {elapsed}s"

session = requests.session()

class UnauthorizedException(Exception):
    pass

class EndOfProgramException(Exception):
    pass

class Location:
    def __init__(self, tracking, name, typeId):
        self.tracking = tracking
        self.name = name
        self.typeId = typeId
    def __eq__(self, other):
        return self.tracking == other.tracking

def endIfTimeElapsed():
    if (datetime.datetime.now() - start_time).total_seconds() > end_in_x_seconds:
        logging.info('ending program')
        raise EndOfProgramException()

def drawImage(epd, is_initial, location):
    if location.name is None:
        image_name = "away.bmp"
        distance_between = distance.distance(location.tracking, home_location).km
        line = string_x_m_away if distance_between < 1 else string_x_km_away
        distance_formated = distance_between * 1000 if distance_between < 1 else distance_between
        second_line = line.format(distance = distance_formated)
    elif location.typeId == "home":
        image_name = "home.bmp"
        second_line = 'home'
    elif location.typeId == "work":
        image_name = "work.bmp"
        second_line = 'at work'

    image = Image.open(os.path.join(assets_dir, image_name))
    draw = ImageDraw.Draw(image)
    draw.text((draw_text_x, draw_text_y_first), string_user_first_line, font = font, fill = 0)

    logging.info(second_line)
    draw.text((draw_text_x, draw_text_y_second), second_line, font = font, fill = 0)

    if location.name is not None:
        draw.text((draw_text_x, draw_text_y_third), string_home_location.format(name = location.name), font = font, fill = 0)

    if is_initial:
        epd.init(epd.FULL_UPDATE)
        epd.displayPartBaseImage(epd.getbuffer(image.rotate(180)))
    else:
        epd.init(epd.PART_UPDATE)
        epd.displayPartial(epd.getbuffer(image.rotate(180)))

    return image

def getLastTracking():
    try:
        uri = "https://api.anticevic.net/tracking/lastLocation"
        response = session.get(uri, headers={"Authorization": os.environ['PROJECT_IVY_TOKEN']}, timeout = 10)

        logging.info(string_response_took.format(elapsed = response.elapsed.total_seconds()))

        if response.status_code == 401:
            logging.error("client not authorized")
            raise UnauthorizedException()

        json = response.json()

        return Location((json["tracking"]["lat"], json["tracking"]["lng"]), json["location"]["name"] if json["location"] is not None else None, json["location"]["typeId"] if json["location"] is not None else None)
    except UnauthorizedException as e:
        raise e
    except Exception:
        logging.error('api call failed', exc_info=True)
        return None

try:
    logging.info("main started")
    
    epd = epd2in13_V2.EPD()
    logging.info("init and clear")
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)

    last_location = Location((0,0), None, None)
    is_initial = True

    while True:
        location = getLastTracking()
        if location is not None and location != last_location:
            logging.info("new location received")
            img = drawImage(epd, is_initial, location)
            is_initial = False
            last_location = location
        endIfTimeElapsed()

        logging.info("waiting 10s")
        time.sleep(10)

except UnauthorizedException:
    logging.info("program ended - api token invalid")
    exit()

except EndOfProgramException:
    logging.info("program ended - time elapsed")
    exit()
        
except IOError as e:
    logging.info(e)
    exit()
    
except KeyboardInterrupt:
    logging.info("program ended - keyboard interrupt")
    epd2in13_V2.epdconfig.module_exit()
    exit()
