# For Heroku
# import gc
import math

# import os
import re

# import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
import time

# import traceback
# import uuid
# from datetime import datetime
from bs4 import BeautifulSoup

# from urllib import parse


from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

import settings
import logging
from my_webdriver import driver_setup


from models import AirBnbRoom

MAX_PAGES = 15
MAX_HOMES_PER_PAGE = 18

PRICE_MIN = 80
PRICE_MAX = 800  # 800
INCREMENT = 10  # calibrated to make sure we can scrape all the links.

NUMBER_SEARCHES = math.ceil((PRICE_MAX - PRICE_MIN) / INCREMENT)
NE_LAT = "45.459424294233266"
NE_LNG = "12.388967004558651"
SW_LAT = "45.40491437897474"
SW_LNG = "12.300303903362362"
ZOOM = "14"
NUM_ADULTS = 2
AREA_NICKNAME = "Venice Center"
DEFAULT_LOAD_TIME_WAIT = 25


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("selenium_airbnb_active_venice_links_scraper")


def get_price_min_and_max_from_url(url):
    parsed_url = urlparse(url)
    price_min = parse_qs(parsed_url.query)["price_min"][0]
    price_max = parse_qs(parsed_url.query)["price_max"][0]
    return price_min, price_max


def get_number_of_rooms_in_page(driver):
    price_min, price_max = get_price_min_and_max_from_url(driver.current_url)
    if "No exact matches" in driver.page_source:
        logger.warning(f"no houses at price level selected.")
        return None
    num_rooms_text_exists = WebDriverWait(driver, DEFAULT_LOAD_TIME_WAIT).until(
        EC.text_to_be_present_in_element(
            (
                By.XPATH,
                """//*[@id="site-content"]/div/div[1]/div/div/div/section/h1/span""",
            ),
            "homes",
        )
    )
    num_rooms_text = (
        driver.find_element(
            By.XPATH,
            """//*[@id="site-content"]/div/div[1]/div/div/div/section/h1/span""",
        )
        .text.replace(",", "")
        .replace(".", "")
        if num_rooms_text_exists
        else None
    )
    num_rooms_text_re = re.search("[0-9]+", num_rooms_text)
    if not num_rooms_text_re:
        return None
    else:
        number_of_rooms_in_page = int(num_rooms_text_re[0])
        if number_of_rooms_in_page > (MAX_PAGES * MAX_HOMES_PER_PAGE):
            logger.warning(
                f"[{price_min} - {price_max}] there are {number_of_rooms_in_page} rooms at this price level. Airbnb shows {MAX_PAGES} pages max with {MAX_HOMES_PER_PAGE} homes per page. so you might be losing some information."
            )
        return number_of_rooms_in_page


def get_number_of_rooms_in_page_with_retry(driver, link_to_get, max_retries=2):
    price_min, price_max = get_price_min_and_max_from_url(driver.current_url)
    for i in range(max_retries):
        try:
            number_of_rooms_in_page = get_number_of_rooms_in_page(driver)
            logger.info(
                f"[{price_min} - {price_max}] success in finding number of rooms"
            )
            return number_of_rooms_in_page
        except TimeoutException:
            logger.warning(
                f"[{price_min} - {price_max}] timeout while waiting for room number. likely there are no rooms for this price level"
            )
            return 0

        except Exception as ex:
            str_to_wrn = f"[{price_min} - {price_max}] An error occurred while trying to get number of rooms in page: {type(ex).__name__}\n Retrying... {i+1}/{max_retries} \n {driver.current_url}"
            logger.warning(str_to_wrn)
            time.sleep(1)  # Adjust sleep duration as needed
    logger.error(
        f"[{price_min} - {price_max}] Failed {max_retries} times for {driver.current_url}"
    )
    return None
    # raise Exception("Failed to get number of rooms after retries")


def get_lat_long_from_page(page_text):
    p_lat = re.compile(r'"lat":([-0-9.]+),')
    p_lng = re.compile(r'"lng":([-0-9.]+),')
    lat = p_lat.findall(page_text)[0]
    lng = p_lng.findall(page_text)[0]
    return lat, lng


def generate_links_to_scrape():
    iteractions_data_links = [
        f"https://www.airbnb.com/s/Venice--Metropolitan-City-of-Venice--Italy/homes?adults={NUM_ADULTS}&min_bedrooms=1&min_beds=1&price_min={PRICE_MIN + iteration_seach * INCREMENT}&price_max={PRICE_MIN + iteration_seach * INCREMENT + INCREMENT}&room_types%5B%5D=Entire%20home%2Fapt&ne_lat={NE_LAT}&ne_lng={NE_LNG}&sw_lat={SW_LAT}&sw_lng={SW_LNG}&zoom={ZOOM}&search_by_map=true&search_type=user_map_move"
        for iteration_seach in range(NUMBER_SEARCHES)
    ]
    return iteractions_data_links


def get_number_of_room_pages(driver):
    all_buttons = WebDriverWait(driver, DEFAULT_LOAD_TIME_WAIT).until(
        EC.visibility_of_all_elements_located(
            (By.XPATH, """//*[@id="site-content"]/div/div[3]/div/div/div/nav/div/a""")
        )
    )
    page_num = [int(i.text) for i in all_buttons if i.text]
    return max(page_num)


def get_all_room_links_from_page(driver):
    price_min, price_max = get_price_min_and_max_from_url(driver.current_url)
    page_source = driver.page_source
    page_source_soup = BeautifulSoup(page_source, "html.parser")
    meta_tags_temp = page_source_soup.find_all("meta", itemprop="url")
    urls_temp = [i["content"] for i in meta_tags_temp]
    if len(urls_temp) == 0:
        current_url = driver.current_url
        logger.warning(
            f"[{price_min} - {price_max}] Page appares to not contian any link. current urk {current_url}"
        )
        return []
    return urls_temp


def get_next_button(driver):
    next_button = WebDriverWait(driver, DEFAULT_LOAD_TIME_WAIT).until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                """//*[@id="site-content"]/div/div[3]/div/div/div/nav/div/a[2]""",
            )
        )
    )
    return next_button


def get_available_rooms_at_link(link_to_get, result_queue):
    price_min, price_max = get_price_min_and_max_from_url(link_to_get)
    driver = driver_setup()
    driver.get(link_to_get)

    number_of_rooms_in_page = get_number_of_rooms_in_page_with_retry(
        driver, link_to_get
    )
    logger.info(
        f"[{price_min} - {price_max}] number of rooms: {number_of_rooms_in_page}"
    )
    if not number_of_rooms_in_page:
        logger.info(
            f"[{price_min} - {price_max}] No rooms with price between {price_min} and {price_max} in selected region."
        )
        return []
    if number_of_rooms_in_page <= MAX_HOMES_PER_PAGE:
        number_of_pages = 1
        log_temp_str = f"[{price_min} - {price_max}] only {number_of_rooms_in_page} rooms. So will only be done in 1 iteration. Max homes per page = {MAX_HOMES_PER_PAGE}"
        logger.info(log_temp_str)
    else:
        number_of_pages = get_number_of_room_pages(driver)
        logger.info(f"[{price_min} - {price_max}] number_of_pages: {number_of_pages}")

    full_list_of_room_links = []
    for i in range(number_of_pages):
        all_room_links_one_page = get_all_room_links_from_page(driver)
        full_list_of_room_links += all_room_links_one_page
        logger.info(
            f"[{price_min} - {price_max}] num link in this page: {len(all_room_links_one_page)}. tot links this price range: {len(full_list_of_room_links)}. Iteration {i+1} out of {number_of_pages}"
        )
        if (i + 1) < number_of_pages:
            logger.info(
                f"[{price_min} - {price_max}] Pushing Next button for the {i+1} time."
            )
            next_button = get_next_button(driver)
            next_button.click()

            # Wait appropriate time so that page is loaded
            _ = WebDriverWait(driver, DEFAULT_LOAD_TIME_WAIT).until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        """//*[@id="site-content"]/div/div[2]/div[1]/div/div/div/div[1]/div[1]/div/div[2]/div/div/div/div/a""",
                    )
                )
            )

    for room_url in full_list_of_room_links:
        room_ids = re.findall(r"\/rooms\/(\w+)\?", room_url)
        room_id = room_ids[0] if room_ids else None
        if room_id:
            current_room = AirBnbRoom(id=room_id, room_url=room_url)
            result_queue.put(current_room)
        else:
            logger.warning(
                f"No room_id found in url: {room_url}"
            )  # known reason for this now is "Luxe" apartments which have different links. For now we ignore those.

    return "ok"
