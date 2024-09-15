import time
import numpy as np
import math
import re
import copy
import pandas as pd
from datetime import datetime, timedelta
from models import CalendarDayState, AirBnbRoomCalendarDay
import logging

from my_webdriver import driver_setup
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


MAX_WAIT_FOR_TRANSLATION_ON_POPUP_SEC = 5
MAX_WAIT_FOR_COOKIES_POPUP_SEC = 5
NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK = 6
MONTHS_PRESENT_IN_ONE_ELEMENT = 4
TIME_SLEEP_AFTER_CAL_NEXT_CLICK_SEC = 0.2
NUMBER_CAL_FETCHES_NEEDED = math.ceil(
    NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK / MONTHS_PRESENT_IN_ONE_ELEMENT
)
CALENDAR_DAYS_DETAILS_EMPTY_TEMPLATE = {
    "current_date_state": None,
    "minimum_stay_nights": None,
    "latest_prices_array": [],
    "cleaning_fee": None,
    "currency": None,
    "extra_attributes": {},
    "price": None,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


def close_translation_popup_if_exists(driver, room_id):
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
        logger.info("[%s] No 'Transaction on' form was found", room_id)


def close_cookie_banner_if_exists(driver, room_id):
    try:
        # Wait for the element to be present
        element = WebDriverWait(driver, MAX_WAIT_FOR_TRANSLATION_ON_POPUP_SEC).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="main-cookies-banner-container"]')
            )
        )
        element.find_element(By.CSS_SELECTOR, '[type="button"]').click()
    except:
        logger.info("[%s] No 'cookies banner' form was found", room_id)


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
    parsed_date = datetime.strptime(date_string, date_format).date()

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


def clear_dates(driver):
    clear_dates_button = driver.find_element(By.XPATH, "//button[text()='Clear dates']")
    clear_dates_button.click()


def get_two_visible_tables(driver, old_visible_table_one_string, room_id):
    visible_table_names = []
    visible_table_index = 0
    tables_divs = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "._ytfarf"))
    )
    first_visible_table = None
    second_visible_table = None
    visible_table_one_string = None
    for table_div in tables_divs:
        month_string = (
            table_div.find_element(By.CLASS_NAME, "_1qlawxx")
            .find_element(By.TAG_NAME, "h3")
            .text
        )
        if month_string == old_visible_table_one_string:
            logger.info(
                "[%s] found again as same table one the old table one. likely did not sleep enough before NEXT table button was pressed and this tables check was made",
                room_id,
            )
            month_string = None
        visible_table_names.append(month_string)
        if not month_string:
            logger.info("[%s] table is not visible. Will will go to next one", room_id)
        else:
            visible_table_index += 1
            logger.info(
                "[%s] visible table number %s is for month %s",
                room_id,
                visible_table_index,
                month_string,
            )
            table = table_div.find_element(By.TAG_NAME, "table")
            if visible_table_index == 1:
                first_visible_table = table
                visible_table_one_string = month_string
            elif visible_table_index == 2:
                second_visible_table = table
            else:
                raise ValueError(
                    "[%s] There are more than 2 visible tables: %s",
                    room_id,
                    visible_table_names,
                )
    return visible_table_one_string, first_visible_table, second_visible_table


def parse_from_day_button_aria_label_to_state(date_button_aria_label):
    patterns = {
        CalendarDayState.UNAVAILABLE: [re.compile(r"\bunavailable\b", re.IGNORECASE)],
        CalendarDayState.AVAILABLE: [
            re.compile(
                r"\bavailable\b.*?(\d+)\s*-?\s*night.*?\bminimum\b", re.IGNORECASE
            ),
            re.compile(r"\bavailable\b.*?\bselect\b.*?\bdate\b", re.IGNORECASE),
        ],
        CalendarDayState.AVAILABLE_NO_CHECKOUT_DATE: [
            re.compile(
                r"\bavailable\b.*?\bno\b.*?\beligible\b.*?\bcheckout\b.*?(\d+)\s*-?\s*night\b",
                re.IGNORECASE,
            )
        ],
        CalendarDayState.CHECKOUT_ONLY: [
            re.compile(
                r"\bthis\s+day\s+is\s+only\s+available\s+for\s+checkout\b",
                re.IGNORECASE,
            )
        ],
        CalendarDayState.UNAVAILABLE_DUE_TO_PAST_DATE: [
            re.compile(r"\bpast\s+dates?\s+can’t\s+be\s+selected\b", re.IGNORECASE)
        ],
    }

    for current_date_state, patterns in patterns.items():
        for pattern in patterns:
            match = pattern.search(date_button_aria_label)
            if match:
                num_nights = (
                    int(match.group(1))
                    if match.lastindex
                    else (1 if CalendarDayState.AVAILABLE else None)
                )
                return current_date_state, num_nights

    logger.error(
        f"Input string does not match any known patterns: {date_button_aria_label}"
    )
    raise ValueError(
        f"Input string does not match any known patterns: {date_button_aria_label}"
    )


def first_day_of_month(date):
    # Create a new datetime object with the first day of the month
    return datetime(date.year, date.month, 1).date()


def get_all_cells_from_table(table):
    all_cells = []
    for row in table.find_elements(By.TAG_NAME, "tr"):
        cells = row.find_elements(By.TAG_NAME, "td")
        all_cells += [cell for cell in cells if cell.get_attribute("aria-label")]
    return all_cells


import re


def parse_pricing_from_pricing_form(input_string, num_nights):
    # Define extended currency symbols
    currency_symbols = r"[\€\$\£\¥\₹\₩\₽\₺\₴\฿\₵\₦\₫\₪\₱\₲\₡\₣\₭\₮]"

    # Initialize default return values
    result = {
        "description": "other",
        "amount": None,
        "currency": None,
        "extra": input_string.strip(),
    }

    # Convert to lowercase for case-insensitive matching
    lower_input = input_string.lower()

    # Check for early_bird_discount pattern
    if (
        ("early" in lower_input)
        and ("bird" in lower_input)
        and ("discount" in lower_input)
    ):
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "early_bird_discount",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for last_minute_discount pattern
    if (
        ("last" in lower_input)
        and ("minute" in lower_input)
        and ("discount" in lower_input)
    ):
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "last_minute_discount",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for accommodation_nightly pattern
    if "accommodation" in lower_input:
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "accommodation_nightly",
                    "amount": amount / num_nights,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for night_price pattern
    if "night" in lower_input:
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "night_price",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for weekly_discount pattern
    if ("weekly" in lower_input) and ("discount" in lower_input):
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "weekly_discount",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for monthly_discount pattern
    if ("monthly" in lower_input) and ("discount" in lower_input):
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "monthly_discount",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for cleaning_fee pattern
    if "cleaning" in lower_input:
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "cleaning_fee",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # Check for taxes pattern
    if "taxes" in lower_input:
        # Extract currency symbol if present
        currency_match = re.search(currency_symbols, input_string)
        currency = currency_match.group(0) if currency_match else None

        # Extract amount
        amount_match = re.search(r"(\d+[\d,]*)", input_string)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        if amount is not None:
            result.update(
                {
                    "description": "taxes",
                    "amount": amount,
                    "currency": currency,
                    "extra": "",
                }
            )
            return result

    # If no match, return 'other'
    logger.warning(
        "We did not find any matching pattern in the input string: %s", input_string
    )
    return result


def from_pricing_elements_to_pricing_dict(pricing_parsed_elements):
    pricing_dictionary_clean = {}
    others_count = 0
    currencies_set = set()
    for pricing_element in pricing_parsed_elements:
        if pricing_element["description"] in {"night_price", "accommodation_nightly"}:
            pricing_dictionary_clean["price"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] in {"early_bird_discount"}:
            pricing_dictionary_clean["early_bird_discount"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] in {"weekly_discount"}:
            pricing_dictionary_clean["weekly_discount"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] in {"monthly_discount"}:
            pricing_dictionary_clean["monthly_discount"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] in {"last_minute_discount"}:
            pricing_dictionary_clean["last_minute_discount"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] in {"cleaning_fee"}:
            pricing_dictionary_clean["cleaning_fee"] = pricing_element["amount"]
            currencies_set.add(pricing_element["currency"])
        elif pricing_element["description"] == "other":
            others_count_str = "" if others_count == 0 else str(others_count)
            pricing_dictionary_clean[others_count_str] = pricing_element["extra"]
        else:
            raise ValueError(
                f"no specification found for pricing_element['description'] == {pricing_element['description']}"
            )
        assert (
            len(currencies_set) == 1
        ), f"No currency found or multiple ccys found: {currencies_set}"
    pricing_dictionary_clean["currency"] = list(currencies_set)[0]

    return pricing_dictionary_clean


def calculate_mean(prices):
    # Convert list to numpy array for handling nan values
    prices_array = np.array(prices, dtype=float)

    # Filter out None and nan values
    valid_prices = prices_array[~np.isnan(prices_array)]

    # Check if there are valid prices
    if len(valid_prices) == 0:
        return None

    # Return the mean of valid prices
    return np.mean(valid_prices)


def get_two_visible_tables_with_retry(
    driver,
    old_visible_table_one_string,
    room_id,
    sleep_after_retry_sec=1,
    max_retries=3,
):
    """
    Retries to get two visible tables with sleep in between.
    """
    retries = 0
    while retries < max_retries:
        visible_table_one_string, first_visible_table, second_visible_table = (
            get_two_visible_tables(driver, old_visible_table_one_string, room_id)
        )

        if first_visible_table and second_visible_table:
            return visible_table_one_string, first_visible_table, second_visible_table

        logger.info(
            "[%s] Not found visible tables on iteration %d", room_id, retries + 1
        )
        time.sleep(sleep_after_retry_sec)
        retries += 1

    # Final attempt
    visible_table_one_string, first_visible_table, second_visible_table = (
        get_two_visible_tables(driver, old_visible_table_one_string, room_id)
    )
    return visible_table_one_string, first_visible_table, second_visible_table


def next_month(driver):
    next_month_button = driver.find_element(
        By.XPATH, '//button[contains(@aria-label, "forward to")]'
    )
    next_month_button.click()


def get_state_and_num_min_nights_of_given_date(
    date_button_aria_label,
    first_table_cell,
    first_visible_table,
    driver,
    room_id,
    verbose=False,
):
    is_check_in_date = "Select as check-in date" in date_button_aria_label
    if is_check_in_date:
        first_table_cell.click()
        try:
            current_date_button = first_visible_table.find_element(
                By.XPATH, ".//td[contains(@aria-label, 'Selected check-in date')]"
            )
        except:
            current_date_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, ".//td[contains(@aria-label, 'Selected check-in date')]")
                )
            )
        clear_dates(driver)
        current_date_button_aria_label = current_date_button.get_attribute("aria-label")
        aria_label_to_use_for_check = current_date_button_aria_label
    else:
        aria_label_to_use_for_check = date_button_aria_label
    if verbose:
        logger.info(
            "[%s] is_check_in_date: %s. aria_label_to_use_for_check: %s",
            room_id,
            is_check_in_date,
            aria_label_to_use_for_check,
        )
    current_date_state, num_nights = parse_from_day_button_aria_label_to_state(
        aria_label_to_use_for_check
    )
    return current_date_state, num_nights


def get_smallest_stay_interval_and_pricing_dict(
    current_date_state,
    num_nights,
    date_button_date,
    second_visible_table,
    second_visible_table_cells,
    first_visible_table_cells,
    first_table_cell,
    first_table_cell_index,
    driver,
    room_id,
    verbose=True,
):
    if current_date_state == CalendarDayState.AVAILABLE:
        min_checkout_date = date_button_date + timedelta(days=num_nights)
        if min_checkout_date.month != date_button_date.month:
            new_month_checkout_date_index = (
                min_checkout_date - first_day_of_month(min_checkout_date)
            ).days
            if verbose:
                logger.info(
                    "[%s] %s checkout will be M+1 : %s. new_month_checkout_date_index: %s",
                    room_id,
                    date_button_date,
                    min_checkout_date,
                    new_month_checkout_date_index,
                )
            if not second_visible_table_cells:
                second_visible_table_cells = get_all_cells_from_table(
                    second_visible_table
                )
                if verbose:
                    logger.info(
                        "[%s] len(second_visible_table_cells): %s",
                        room_id,
                        len(second_visible_table_cells),
                    )

            checkout_date_button_to_click = second_visible_table_cells[
                new_month_checkout_date_index
            ]
            logger.info(
                '[%s] checkout_date_button_to_click.get_attribute("aria-label"): %s',
                room_id,
                checkout_date_button_to_click.get_attribute("aria-label"),
            )

        else:
            checkout_date_button_to_click = first_visible_table_cells[
                first_table_cell_index + num_nights
            ]

        ### click on the check-in and check-out dates. Then get pricing info
        first_table_cell.click()
        checkout_date_button_to_click.click()
        pricing_form_divs = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "._1n7cvm7"))
        )
        pricing_elements = pricing_form_divs.find_elements(By.CLASS_NAME, "_14omvfj")
        pricing_parsed_elements = []
        for pricing_element in pricing_elements:
            pricing_parsed_elements.append(
                parse_pricing_from_pricing_form(
                    pricing_element.text, num_nights=num_nights
                )
            )
        if verbose:
            logger.info(
                "[%s] pricing_parsed_elements: %s", room_id, pricing_parsed_elements
            )
        assert (
            len(
                [
                    i
                    for i in pricing_parsed_elements
                    if i["description"] in {"night_price", "accommodation_nightly"}
                ]
            )
            == 1
        ), "There is no night price for this listing????"
        clear_dates(driver)
        pricing_dict = from_pricing_elements_to_pricing_dict(pricing_parsed_elements)

    else:
        pricing_dict = {}
        pass  # DATE NOT AVIALABEL
    return pricing_dict, second_visible_table_cells


def enrich_calendar_days_details_if_data_is_available(
    calendar_days_details_empty_template,
    current_date_state,
    pricing_dict,
    calendar_days_details,
    date_button_date,
    num_nights,
):
    if current_date_state == CalendarDayState.AVAILABLE:
        current_price = pricing_dict.get("price")
        pricing_dict.pop("price", None)
        calendar_days_details[date_button_date]["cleaning_fee"] = pricing_dict.get(
            "cleaning_fee"
        )
        pricing_dict.pop("cleaning_fee", None)
        calendar_days_details[date_button_date]["currency"] = pricing_dict.get(
            "currency"
        )
        pricing_dict.pop("currency", None)
        calendar_days_details[date_button_date]["extra_attributes"] = pricing_dict
        for next_day_index in range(0, num_nights):
            list_to_append = [
                {
                    "check_in": date_button_date,
                    "check_out": (date_button_date + timedelta(days=num_nights)),
                    "price": current_price,
                }
            ]
            future_day_date = date_button_date + timedelta(days=next_day_index)
            if future_day_date not in calendar_days_details:
                calendar_days_details[future_day_date] = copy.deepcopy(
                    calendar_days_details_empty_template
                )
            calendar_days_details[future_day_date][
                "latest_prices_array"
            ] += list_to_append
    return calendar_days_details, pricing_dict


def generate_airbnb_calendar_day_list(calendar_days_details, ROOM_ID):
    def make_json_serializable_prices_array(prices_array):
        serializable = []
        for price_details in prices_array:
            price_details["check_in"] = price_details["check_in"].strftime("%Y-%m-%d")
            price_details["check_out"] = price_details["check_out"].strftime("%Y-%m-%d")
            serializable.append(price_details)
        return serializable

    calendar_days_details_models = []
    for date, date_details in calendar_days_details.items():
        airbnb_calendar_day = AirBnbRoomCalendarDay(
            room_id=ROOM_ID,
            calendar_day=date,
            state=date_details["current_date_state"],
            previous_state=None,
            minimum_stay_nights=date_details["minimum_stay_nights"],
            price=calculate_mean(
                [i["price"] for i in date_details["latest_prices_array"]]
            ),
            latest_prices_array=make_json_serializable_prices_array(
                date_details["latest_prices_array"]
            ),
            cleaning_fee=date_details["cleaning_fee"],
            currency=date_details["currency"],
            extra_attributes=date_details["extra_attributes"],
        )
        calendar_days_details_models.append(airbnb_calendar_day)
    return calendar_days_details_models


def get_calendar_days_for_provided_room(room_id, result_queue, headless=True):
    driver = driver_setup(headless=headless)
    logger.info("[%s] getting room", room_id)
    driver.get(f"https://www.airbnb.com/rooms/{room_id}?adults=2")
    logger.info("[%s] room gotten", room_id)
    close_translation_popup_if_exists(driver, room_id)
    logger.info("[%s] close_translation_popup_if_exists over", room_id)
    close_cookie_banner_if_exists(driver, room_id)
    logger.info("[%s] close_cookie_banner_if_exists over", room_id)

    calendar_days_details = {}
    old_visible_table_one_string = None
    for num_nexts_to_click in range(NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK):
        old_visible_table_one_string, first_visible_table, second_visible_table = (
            get_two_visible_tables_with_retry(
                driver,
                old_visible_table_one_string,
                room_id,
                sleep_after_retry_sec=1,
                max_retries=3,
            )
        )
        logger.info(
            "[%s] old_visible_table_one_string: %s, first_visible_table: %s, second_visible_table: %s",
            room_id,
            old_visible_table_one_string,
            first_visible_table,
            second_visible_table,
        )
        second_visible_table_cells = None
        first_visible_table_cells = get_all_cells_from_table(first_visible_table)
        for first_table_cell_index, first_table_cell in enumerate(
            first_visible_table_cells
        ):
            date_button_aria_label = first_table_cell.get_attribute("aria-label")
            date_button_date = parse_date(date_button_aria_label.split(".", 1)[0])
            current_date_state, num_nights = get_state_and_num_min_nights_of_given_date(
                date_button_aria_label,
                first_table_cell,
                first_visible_table,
                driver,
                room_id,
            )
            logger.info(
                "[%s] date_button_date: %s. current_date_state: %s. num_nights: %s.",
                room_id,
                date_button_date,
                current_date_state,
                num_nights,
            )
            pricing_dict, second_visible_table_cells = (
                get_smallest_stay_interval_and_pricing_dict(
                    current_date_state,
                    num_nights,
                    date_button_date,
                    second_visible_table,
                    second_visible_table_cells,
                    first_visible_table_cells,
                    first_table_cell,
                    first_table_cell_index,
                    driver,
                    room_id,
                )
            )
            calendar_days_details.setdefault(
                date_button_date, copy.deepcopy(CALENDAR_DAYS_DETAILS_EMPTY_TEMPLATE)
            )
            calendar_days_details[date_button_date][
                "current_date_state"
            ] = current_date_state
            calendar_days_details[date_button_date]["minimum_stay_nights"] = num_nights
            calendar_days_details, pricing_dict = (
                enrich_calendar_days_details_if_data_is_available(
                    CALENDAR_DAYS_DETAILS_EMPTY_TEMPLATE,
                    current_date_state,
                    pricing_dict,
                    calendar_days_details,
                    date_button_date,
                    num_nights,
                )
            )
        if (num_nexts_to_click + 1) < NUMBER_ON_MONTHS_IN_FUTURE_TO_CHECK:
            next_month(driver)
        time.sleep(1)

    calendar_days_details_models = generate_airbnb_calendar_day_list(
        calendar_days_details, room_id
    )
    for calendar_day in calendar_days_details_models:
        result_queue.put(calendar_day)


# if __name__ == 'main':
#     get_calendar_days_for_provided_room(room_id=34281543) #TEST
