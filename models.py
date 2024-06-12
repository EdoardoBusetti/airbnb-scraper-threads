from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import StrEnum

db_url = "sqlite:///data/airbnb.db"

Base = declarative_base()


class CalendarDayState(StrEnum):
    BUSY = "BUSY"
    FREE = "FREE"
    HOST_UNAVAILABLE = "HOST_UNAVAILABLE"


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
        session.merge(existing_instance)
    else:
        session.add(instance)


class AirBnbCalendar(Base):
    __tablename__ = "airbnb_calendar"
    room_id = Column(String, ForeignKey(AirBnbRoom.id), primary_key=True)
    date = Column(Date, primary_key=True)
    version = Column(Integer, primary_key=True, default=0)
    create_date = Column(DateTime, default=func.now())
    state = Column(String)
    price = Column(Float)
    cleaning_fee = Column(Float)
    service_fee_pct = Column(Float)
    currency = Column(String)


def save_or_update_airbnb_calendar_date(instance, session):
    existing_instance_latest_version = (
        session.query(AirBnbCalendar)
        .filter_by(room_id=instance.room_id, date=instance.date)
        .order_by(AirBnbCalendar.version.desc())
        .first()
    )
    if existing_instance_latest_version:
        instance.version = existing_instance_latest_version.version + 1
        session.add(instance)
    else:
        session.add(instance)
