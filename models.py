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
    AVAILABLE_NO_CHECKOUT_DATE = "AVAILABLE_NO_CHECKOUT_DATE"
    CHECKOUT_ONLY = "CHECKOUT_ONLY"
    UNAVAILABLE = "UNAVAILABLE"
    UNAVAILABLE_DUE_TO_PAST_DATE = "UNAVAILABLE_DUE_TO_PAST_DATE"


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
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
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
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
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
    state = Column(String)
    previous_state = Column(String)
    minimum_stay_nights = Column(Integer)
    price = Column(
        Float,
        comment="It is the average price for the prices which this day has on the latest evaluation run. [one day can be in multiple stays intervals. this will be avg price for that room in those stay intervals]",
    )
    previous_price = Column(
        Float,
        comment="previous price",
    )
    latest_prices_array = Column(
        JSON,
        comment="Array with the prices from current run. with their checking and checkout dates. [{'check_in':XXX,'check_out':YYY, 'price':price1},{'check_in':ZZZ,'check_out':KKK, 'price':price2}]",
    )
    cleaning_fee = Column(Float)
    currency = Column(String)
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
    )


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
    previous_state = Column(String)
    current_state = Column(String)
    previous_price = Column(Float)
    current_price = Column(Float)
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
    )


def save_or_update_airbnb_room_instance(instance, session):
    existing_instance = session.query(AirBnbRoom).get(instance.id)
    if existing_instance:
        existing_instance.number_updates += 1
        session.merge(existing_instance)  # the new details will override the old  ones
    else:
        session.add(instance)


def save_or_update_airbnb_date(new_instance: AirBnbRoomCalendarDay, session):
    existing_instance: AirBnbRoomCalendarDay = (
        session.query(AirBnbRoomCalendarDay)
        .filter_by(room_id=new_instance.room_id, calendar_day=new_instance.calendar_day)
        .first()
    )
    if existing_instance:
        if existing_instance.state == new_instance.state:
            existing_instance.previous_state = new_instance.state
            existing_instance.minimum_stay_nights = (
                new_instance.minimum_stay_nights
                if new_instance.minimum_stay_nights
                else existing_instance.minimum_stay_nights
            )
            existing_instance.previous_price = existing_instance.price
            existing_instance.price = (
                new_instance.price if new_instance.price else existing_instance.price
            )
            existing_instance.latest_prices_array = (
                new_instance.latest_prices_array
                if new_instance.latest_prices_array
                else existing_instance.latest_prices_array
            )
            existing_instance.cleaning_fee = (
                new_instance.cleaning_fee
                if new_instance.cleaning_fee
                else existing_instance.cleaning_fee
            )
            existing_instance.currency = (
                new_instance.currency
                if new_instance.currency
                else existing_instance.currency
            )
            existing_instance.extra_attributes = {
                **existing_instance.extra_attributes,
                **new_instance.extra_attributes,
            }  # Merge dictionaries, with new_instance's values prevailing in case of conflict
            session.merge(
                existing_instance
            )  # the new details will override the old  ones
        elif (
            existing_instance.state != new_instance.state
        ):  # TODO. Map each individual possible state transition and generate different AirBnbRoomCalendarDayTransition for each of those. (e. from AVAILABLE to UNAVAILABLE_DUE_TO_PAST_DATE. it is unbooked date)
            existing_instance.previous_state = new_instance.state
            existing_instance.minimum_stay_nights = (
                new_instance.minimum_stay_nights
                if new_instance.minimum_stay_nights
                else existing_instance.minimum_stay_nights
            )
            existing_instance.previous_price = existing_instance.price
            existing_instance.price = (
                new_instance.price if new_instance.price else existing_instance.price
            )
            existing_instance.latest_prices_array = (
                new_instance.latest_prices_array
                if new_instance.latest_prices_array
                else existing_instance.latest_prices_array
            )
            existing_instance.cleaning_fee = (
                new_instance.cleaning_fee
                if new_instance.cleaning_fee
                else existing_instance.cleaning_fee
            )
            existing_instance.currency = (
                new_instance.currency
                if new_instance.currency
                else existing_instance.currency
            )
            existing_instance.extra_attributes = {
                **existing_instance.extra_attributes,
                **new_instance.extra_attributes,
            }  # Merge dictionaries, with new_instance's values prevailing in case of conflict
            session.merge(
                existing_instance
            )  # the new details will override the old  ones
        else:
            raise ValueError("not predicted state change transition")
    else:  # we do not have any record yet for this day
        session.add(new_instance)
