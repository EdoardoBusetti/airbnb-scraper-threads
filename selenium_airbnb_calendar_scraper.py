import time
import math
import pandas as pd
from datetime import datetime
# from models import AirBnbCalendar
import logging
from my_webdriver import driver_setup
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


MAX_WAIT_FOR_TRANSLATION_ON_POPUP_SEC = 5
NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK = 6
MONTHS_PRESENT_IN_ONE_ELEMENT = 4
TIME_SLEEP_AFTER_CAL_NEXT_CLICK_SEC = 0.2
NUMBER_CAL_FETCHES_NEEDED = math.ceil(
    NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK / MONTHS_PRESENT_IN_ONE_ELEMENT
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def close_translation_popup_if_exists(driver):
    try:
        # Wait for the element to be present
        element = WebDriverWait(driver, MAX_WAIT_FOR_TRANSLATION_ON_POPUP_SEC).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".p1psejvv.atm_9s_1bgihbq.dir.dir-ltr")
            )
        )
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.ESCAPE)
    except:
        print("No 'Transaction on' form was found")


def open_the_calendar_form(driver):
    try:
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "._16l1qv1")
            )  # check-in date form button
        )
        # Click the button
        button.click()
        print("'Transaction on' esc button clicked successfully.")
    except Exception as e:
        # If the button is not found or another exception occurs, print an error message
        print(f"Exception occurred: {e}")


def parse_date(date_string):
    # Define the format of the input string
    # %d: Day of the month as a zero-padded decimal number.
    # %A: Full weekday name.
    # %B: Full month name.
    # %Y: Year with century as a decimal number.
    date_format = "%d, %A, %B %Y"
    if "Today" in date_string:
        date_string = date_string.rsplit(",", 1)[0]
    # Parse the date string into a datetime object
    parsed_date = datetime.strptime(date_string, date_format)

    return parsed_date


def get_calendar_table_from_driver(driver):
    tables = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "._cvkwaj"))
    )
    all_tables_data = []  # Initialize list to store all data

    # Iterate through each table
    for table in tables:
        # Extract rows from the current table
        rows = table.find_elements(By.TAG_NAME, "tr")

        # Initialize list to store data for the current table

        # Iterate through rows and extract cell data
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            for cell in cells:
                # Extract desired attributes
                cell_data = {
                    "aria-disabled": cell.get_attribute("aria-disabled"),
                    "aria-label": cell.get_attribute("aria-label"),
                    # "class": cell.get_attribute("class")
                }
                all_tables_data.append(cell_data)
    return all_tables_data


def is_day_disabled(day_disabled):
    if type(day_disabled) == bool:
        return day_disabled
    else:
        if day_disabled.lower() == "true":
            return True
        else:
            return False


def get_dates_availability(driver):
    t0 = datetime.now()
    try:
        all_tables_data = get_calendar_table_from_driver(driver)
    except Exception as e:
        print(e)
        time.sleep(2)
        print("sleeping 2s and trying Again...")
        all_tables_data = get_calendar_table_from_driver(driver)

    all_tables_data_clean = []
    for cell_attributes in all_tables_data:
        if cell_attributes.get(
            "aria-disabled"
        ):  # only if this is true, then it is a calendar day
            date_string, reason_string = cell_attributes["aria-label"].split(".", 1)
            all_tables_data_clean.append(
                {
                    "day_disabled": is_day_disabled(cell_attributes["aria-disabled"]),
                    "day_label":cell_attributes["aria-label"],
                    "date": parse_date(date_string),
                    "reason_string": reason_string.strip(),
                }
            )

    t1 = datetime.now()
    logger.info(
        "found %s elements. time for calendar fetch %s. last elem %s",
        len(all_tables_data_clean),
        t1 - t0,
        all_tables_data_clean[-1]["date"],
    )
    return all_tables_data_clean

def clear_dates():
    clear_dates_button = driver.find_element(By.XPATH, "//button[text()='Clear dates']")
    clear_dates_button.click()


def get_all_dates_availability(
    driver,
    number_cal_fetches_needed,
    months_present_in_one_element,
    time_sleep_after_cal_next_click_sec,
):
    all_table_data_clean_all_months = []
    for cal_fetch_iter_counter in range(number_cal_fetches_needed):
        all_tables_data_clean = get_dates_availability(driver)
        all_table_data_clean_all_months += all_tables_data_clean
        if (cal_fetch_iter_counter + 1) < number_cal_fetches_needed:
            for next_button_press_iter_count in range(months_present_in_one_element):
                next_button = driver.find_element(By.CLASS_NAME, "_qz9x4fc")
                logger.info(
                    "clicking next button. cal iteration %s. button click %s",
                    cal_fetch_iter_counter,
                    next_button_press_iter_count,
                )
                next_button.click()
                if (next_button_press_iter_count + 1) < months_present_in_one_element:
                    time.sleep(time_sleep_after_cal_next_click_sec)
            time.sleep(1)
    return all_table_data_clean_all_months


driver = driver_setup(settings={"headless": False})
ROOM_URL_FOR_TEST=  "https://www.airbnb.com/rooms/34281543?adults=2" # "https://www.airbnb.com/rooms/634438216271572667?adults=2"
driver.get(ROOM_URL_FOR_TEST)



close_translation_popup_if_exists(driver)
# open_the_calendar_form(driver) # not needed as there is a table with dates in the main page, without even clicking on the calendar popup


all_table_data_clean_all_months = get_all_dates_availability(
    driver,
    number_cal_fetches_needed=NUMBER_CAL_FETCHES_NEEDED,
    months_present_in_one_element=MONTHS_PRESENT_IN_ONE_ELEMENT,
    time_sleep_after_cal_next_click_sec=TIME_SLEEP_AFTER_CAL_NEXT_CLICK_SEC,
)
temp_df = pd.DataFrame(all_table_data_clean_all_months)
print(temp_df)
temp_df.to_csv("temp_df.csv", index=False)

time.sleep(100000)

# all_buttons = WebDriverWait(driver, 10).until(
#         EC.visibility_of_all_elements_located(
#             (By.XPATH, """p1psejvv atm_9s_1bgihbq dir dir-ltr""")
#         )
#     )
# print(all_buttons)
