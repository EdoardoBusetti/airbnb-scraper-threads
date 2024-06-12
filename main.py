from selenium_airbnb_active_venice_links_scraper import generate_links_to_scrape, get_available_rooms_at_link
import threading
from datetime import datetime
import logging
import sqlalchemy
from models import Base, db_url, save_or_update_airbnb_room_instance
from sqlalchemy.orm import Session
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('main_logger')

result_queue = queue.Queue()

# db loading and creating all tables
engine = sqlalchemy.create_engine(db_url,echo=False) # We have also specified a parameter create_engine.echo, which will instruct the Engine to log all of the SQL it emits to a Python logger that will write to standard out. 
Base.metadata.create_all(engine)

session = Session(engine)

links_to_scrape = generate_links_to_scrape()
logger.info(f"number of links to scrape: {len(links_to_scrape)}")

MAX_BATCH_SIZE = 10
links_to_scrape_batches = [links_to_scrape[i:i + MAX_BATCH_SIZE] for i in range(0, len(links_to_scrape), MAX_BATCH_SIZE)] 


def run_threads():
    threads = []
    all_drivers = []
    for links_to_scrape_batch in links_to_scrape_batches:
        for link_to_scrape in links_to_scrape_batch:
            t = threading.Thread(target=get_available_rooms_at_link,kwargs = {'link_to_get':link_to_scrape, 'result_queue':result_queue})
            t.start()
            threads.append(t)

        drivers = [t.join() for t in threads]
        all_drivers+=drivers
        
        
        
    all_objects_to_write = []
    while not result_queue.empty():
        record_to_insert = result_queue.get()
        all_objects_to_write.append(record_to_insert)
    return all_objects_to_write

t0 = datetime.now()
logger.info("start to run threads")
all_objects_to_write = run_threads()
t1 = datetime.now()
logger.info(f"threads run over. time it took: {t1-t0}")

logger.info("start to add new objects")
for object_to_write in all_objects_to_write:
    save_or_update_airbnb_room_instance(session=session,instance=object_to_write)

t2 = datetime.now()
logger.info(f"end to add new objects. time it took: {t2-t1}")

logger.info("start to commit")
session.commit()
t3 = datetime.now()
logger.info(f"end to commit. time it took: {t3-t2}")