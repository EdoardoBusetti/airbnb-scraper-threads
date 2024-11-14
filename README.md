# AirBnb Scraper

This project aims at implementing a number of scrapers to scrape different datapoints from AirBnb and persisting them in an organised way such that they can be used for data analysis

## Models

* ```airbnb_scrapers_runs``` contains details of each scraping job run, with it's state, start time and end time.
* ```airbnb_rooms``` stores each individual room which we scraped
* ```airbnb_room_details``` stores details of each room which we scraped
* ```airbnb_room_calendar_days``` table contains the current state of an individual day in the calendar of a given listing
* ```airbnb_room_calendar_day_transitions``` table contains all recorded state transitions for a given day in the calendar of a given listing (e.g. how the **state**, **price** and other important attributes of that calendar day evolve from one scraping iteration to the next one