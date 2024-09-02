from selenium import webdriver
from settings import driver_settings
from selenium.webdriver.chrome.options import Options


def driver_setup(settings=driver_settings):
    if settings["headless"]:
        options = Options()
        options.add_argument("--headless")
    else:
        options = None

    driver = webdriver.Chrome(options=options)
    return driver
