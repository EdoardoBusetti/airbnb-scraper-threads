from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

db_url = 'sqlite:///data/airbnb.db'

Base = declarative_base()

class AirBnbRoom(Base):
    __tablename__ = "airbnb_room"
    id = Column(String, primary_key=True)
    create_date = Column(DateTime, default=func.now())
    last_modified = Column(DateTime, onupdate=func.now())
    number_updates = Column(Integer, default=0)
    room_url = Column(String)
    
        
def save_or_update_airbnb_room_instance(instance, session):
    existing_instance = session.query(AirBnbRoom).get(instance.id)
    if existing_instance:
        existing_instance.number_updates += 1
        session.merge(instance)
    else:
        session.add(instance)