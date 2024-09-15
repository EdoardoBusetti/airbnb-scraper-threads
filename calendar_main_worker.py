from selenium_airbnb_calendar_scraper import (
    get_calendar_days_for_provided_room,
)
import threading
from datetime import datetime
import logging
import sqlalchemy
from models import Base, db_url, save_or_update_airbnb_date
from sqlalchemy.orm import Session
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_logger")

result_queue = queue.Queue()

# db loading and creating all tables
engine = sqlalchemy.create_engine(
    db_url, echo=False
)  # We have also specified a parameter create_engine.echo, which will instruct the Engine to log all of the SQL it emits to a Python logger that will write to standard out.
Base.metadata.create_all(engine)

session = Session(engine)

rooms_ids_to_scrape = [14132224]  # 34281543,818914306204706609,
logger.info(f"number of calendars to scrape: {len(rooms_ids_to_scrape)}")

MAX_BATCH_SIZE = 5
rooms_to_scrape_batches = [
    rooms_ids_to_scrape[i : i + MAX_BATCH_SIZE]
    for i in range(0, len(rooms_ids_to_scrape), MAX_BATCH_SIZE)
]


def run_threads():
    threads = []
    all_drivers = []
    for rooms_to_scrape_batch in rooms_to_scrape_batches:
        for rooms_id_to_scrape in rooms_to_scrape_batch:
            t = threading.Thread(
                target=get_calendar_days_for_provided_room,
                kwargs={
                    "room_id": rooms_id_to_scrape,
                    "result_queue": result_queue,
                    "headless": False,
                },
            )
            t.start()
            threads.append(t)

        drivers = [t.join() for t in threads]
        all_drivers += drivers

    all_objects_to_write = []
    while not result_queue.empty():
        record_to_insert = result_queue.get()
        all_objects_to_write.append(record_to_insert)
    return all_objects_to_write


t0 = datetime.now()
logger.info("start to run threads")
all_objects_to_write = run_threads()
t1 = datetime.now()
logger.info(
    f"threads run over. time it took: {t1-t0}. num objects: {len(all_objects_to_write)}"
)

logger.info("start to add new objects")
for object_to_write in all_objects_to_write:
    save_or_update_airbnb_date(session=session, new_instance=object_to_write)

t2 = datetime.now()
logger.info(f"end to add new objects. time it took: {t2-t1}")

logger.info("start to commit")
session.commit()
t3 = datetime.now()
logger.info(f"end to commit. time it took: {t3-t2}")
