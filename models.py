from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    JSON,
    Float,
    Date,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import StrEnum

db_url = "sqlite:///data/airbnb.db"

Base = declarative_base()


class CalendarDayState(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    CHECKOUT_ONLY = "CHECKOUT_ONLY"


class AirBnbRoom(Base):
    """
    Represents an Airbnb room in the database.

    This class is mapped to the 'airbnb_room' table in the database and stores
    information about each room, including its unique identifier, creation and
    update timestamps, number of updates, and the URL used to find this room listing.
    """

    __tablename__ = "airbnb_rooms"
    id = Column(String, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room entry was created",
    )
    updated_at = Column(
        DateTime,
        onupdate=func.now(),
        comment="Timestamp when the room entry was last updated",
    )
    number_updates = Column(
        Integer, default=0, comment="Number of times the room entry has been updated"
    )
    room_url = Column(
        String,
        comment="URL of the Airbnb room listing that was used to find the room in the next run in which this room was found",
    )


class AirBnbRoomDetails(Base):
    """Represents the details for an AirBnbRoom. Is updated periodically."""

    __tablename__ = "airbnb_room_details"
    room_id = Column(String, primary_key=True)
    version = Column(Integer, primary_key=True, default=0)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room entry was created",
    )
    updated_at = Column(
        DateTime,
        onupdate=func.now(),
        comment="Timestamp when the room entry was last updated",
    )
    number_updates = Column(
        Integer,
        default=0,
        comment="Number of times the roomDetails entry has been updated -> Only counted if something changed in the details",
    )


class AirBnbRoomDetailsUpdate(Base):
    """Stores time at which each room was updated"""

    __tablename__ = "airbnb_room_details_updates"
    room_id = Column(String, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room update was created",
    )
    finished_at = Column(
        DateTime,
        onupdate=func.now(),
    )
    any_changes = Column(
        Boolean, comment="True if there were any changes compared to previous version"
    )


class AirBnbRoomCalendarDay(Base):
    __tablename__ = "airbnb_room_calendar_days"
    room_id = Column(String, ForeignKey(AirBnbRoom.id), primary_key=True)
    calendar_day = Column(Date, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    previous_state = Column(String)
    current_state = Column(String)
    price = Column(Float)
    cleaning_fee = Column(Float)
    service_fee_pct = Column(Float)
    currency = Column(String)


class AirBnbRoomCalendarUpdate(Base):
    """Stores time at which each room calendar was updated"""

    __tablename__ = "airbnb_room_calendar_updates"
    room_id = Column(String, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room calendar update was created",
    )
    finished_at = Column(
        DateTime,
        onupdate=func.now(),
    )
    any_changes = Column(
        Boolean, comment="True if there were any changes compared to previous version"
    )


class AirBnbRoomCalendarDayTransition(Base):
    """Stores any change in state for a room calendar day"""

    __tablename__ = "airbnb_room_calendar_day_transitions"
    room_id = Column(String, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room calendar update was created",
    )
    any_changes = Column(
        Boolean, comment="True if there were any changes compared to previous version"
    )



# def save_or_update_airbnb_calendar_date(instance, session):
#     existing_instance_latest_version = (
#         session.query(AirBnbRoomCalendarDay)
#         .filter_by(room_id=instance.room_id, date=instance.date)
#         .order_by(AirBnbRoomCalendarDay.version.desc())
#         .first()
#     )
#     if existing_instance_latest_version:
#         instance.version = existing_instance_latest_version.version + 1
#         session.add(instance)
#     else:
#         session.add(instance)


def save_or_update_airbnb_room_instance(instance, session):
    existing_instance = session.query(AirBnbRoom).get(instance.id)
    if existing_instance:
        existing_instance.number_updates += 1
        session.merge(existing_instance)  # the new details will override the old  ones
    else:
        session.add(instance)
