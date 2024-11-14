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



class AirBnbScraperRun(Base):
    """Stores details about each airbnb scraper run"""

    __tablename__ = "airbnb_scrapers_runs"
    scraper_name = Column(String, primary_key=True)
    room_id = Column(String, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the scraping job was started",
        primary_key=True
    )
    updated_at = Column(
        DateTime,
        onupdate=func.now(),
        comment="Timestamp when the scraping job was ended"
    )
    is_success = Column(
        Boolean, 
        default=False,
        comment="indicates if the scraping job terminated successfully"
    )
    comment = Column(String, comment = "comment on the execution of the scraping job")

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
    """Represents the details for an AirBnbRoom. It is updated periodically."""

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


# class AirBnbRoomDetailsUpdate(Base):
#     """Stores time at which each room was updated"""

#     __tablename__ = "airbnb_room_details_updates"
#     room_id = Column(String, primary_key=True)
#     created_at = Column(
#         DateTime,
#         default=func.now(),
#         comment="Timestamp when the room update was created",
#     )
#     finished_at = Column(
#         DateTime,
#         onupdate=func.now(),
#     )
#     any_changes = Column(
#         Boolean, comment="True if there were any changes compared to previous version"
#     )


class AirBnbRoomCalendarDay(Base):
    __tablename__ = "airbnb_room_calendar_days"
    room_id = Column(String, ForeignKey(AirBnbRoom.id), primary_key=True)
    calendar_day = Column(Date, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    state = Column(String)
    price = Column(
        Float,
        comment="It is the average price for the prices which this day has on the latest evaluation run. [one day can be in multiple stays intervals. this will be avg price for that room in those stay intervals]",
    )
    latest_prices_array = Column(
        JSON,
        comment="Array with the prices from current run. with their checking and checkout dates. [{'check_in':XXX,'check_out':YYY, 'price':price1},{'check_in':ZZZ,'check_out':KKK, 'price':price2}]",
    )
    minimum_stay_nights = Column(Integer)
    cleaning_fee = Column(Float)
    currency = Column(String)
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
    )


# class AirBnbRoomCalendarUpdate(Base):
#     """Stores time at which each room calendar was updated"""

#     __tablename__ = "airbnb_room_calendar_updates"
#     room_id = Column(String, primary_key=True)
#     created_at = Column(
#         DateTime,
#         default=func.now(),
#         comment="Timestamp when the room calendar update was created",
#     )
#     finished_at = Column(
#         DateTime,
#         onupdate=func.now(),
#     )
#     any_changes = Column(
#         Boolean, comment="True if there were any changes compared to previous version"
#     )


class AirBnbRoomCalendarDayTransition(Base):
    """Stores any change in state for a room calendar day"""

    __tablename__ = "airbnb_room_calendar_day_transitions"
    room_id = Column(String, primary_key=True)
    calendar_day = Column(Date, primary_key=True)
    created_at = Column(
        DateTime,
        default=func.now(),
        comment="Timestamp when the room calendar transition was recorded",
    )
    transition_type = Column(String)
    state = Column(String)
    price = Column(Float)
    latest_prices_array = Column(
        JSON,
        comment="Array with the prices from current run. with their checking and checkout dates. [{'check_in':XXX,'check_out':YYY, 'price':price1},{'check_in':ZZZ,'check_out':KKK, 'price':price2}]",
    )
    minimum_stay_nights = Column(Integer)
    cleaning_fee = Column(Float)
    currency = Column(String)
    extra_attributes = Column(
        JSON,
        comment="Json with extra attributes",
    )


def check_calendar_day_changes(
    existing_instance, new_instance, price_change_tolerance_pct
):
    state_change = existing_instance.state != new_instance.state
    min_nights_change = (
        existing_instance.minimum_stay_nights != new_instance.minimum_stay_nights
    )
    price_change = (
        abs(existing_instance.price - new_instance.price) / existing_instance.price
    ) >= price_change_tolerance_pct
    cleaning_fee_change = existing_instance.cleaning_fee != new_instance.cleaning_fee
    currency_change = (
        existing_instance.currency != new_instance.currency
    )  # should not be unless IP location changes
    any_change = any(
        [
            state_change,
            min_nights_change,
            price_change,
            cleaning_fee_change,
            currency_change,
        ]
    )
    return any_change, state_change


def save_or_update_airbnb_room_instance(instance, session):
    existing_instance = session.query(AirBnbRoom).get(instance.id)
    if existing_instance:
        existing_instance.number_updates += 1
        session.merge(existing_instance)  # the new details will override the old  ones
    else:
        session.add(instance)


def save_or_update_airbnb_date(
    new_instance: AirBnbRoomCalendarDay,
    session,
    price_change_tolerance_pct: float = 0.1,
):
    """when passed a new_instance of a calendar day, it checks if this was already stored in db previously.
    if not, stores it and creates NEW_DATE_RECORDED transition.
    if yes, will check if there was any change for that day compared to previous record.
    if there is no change, stores the new information.
    if there is a change, will update the record

    Args:
        new_instance (AirBnbRoomCalendarDay): the newly created instance of AirBnbRoomCalendarDay from current job run
        session (Any): the db session
        price_change_tolerance_pct (float, optional): the tolerance for the price change (given that price change might just be due to rounding or to different days being included in the price array). Defaults to 0.1 [10%].

    """
    existing_instance: AirBnbRoomCalendarDay = (
        session.query(AirBnbRoomCalendarDay)
        .filter_by(room_id=new_instance.room_id, calendar_day=new_instance.calendar_day)
        .first()
    )
    if existing_instance:
        any_change, state_change = check_calendar_day_changes(
            existing_instance, new_instance, price_change_tolerance_pct
        )
        if (
            any_change
        ):  # change. store changes and generate AirBnbRoomCalendarDayTransition
            transition_type = (
                existing_instance.state + " - " + new_instance.state
                if state_change
                else "ATTRIBUTES_ONLY_CHANGE"
            )

            # some attributes might not longer be present in new state (will be nulls) in that case, we just keep previous atributes.
            new_instance.price = (
                new_instance.price if new_instance.price else existing_instance.price
            )
            new_instance.currency = (
                new_instance.currency
                if new_instance.currency
                else existing_instance.currency
            )
            new_instance.cleaning_fee = (
                new_instance.cleaning_fee
                if new_instance.cleaning_fee
                else existing_instance.cleaning_fee
            )
            new_instance.minimum_stay_nights = (
                new_instance.minimum_stay_nights
                if new_instance.minimum_stay_nights
                else existing_instance.minimum_stay_nights
            )
            new_instance.latest_prices_array = (
                new_instance.latest_prices_array
                if new_instance.latest_prices_array
                else existing_instance.latest_prices_array
            )

        else:  # no change in considered attributes (extra attributes might have changed. we will store new version if key collision.)
            transition_type = None

        new_instance.extra_attributes = {  # Merge dictionaries, with new_instance's values prevailing in case of conflict
            **existing_instance.extra_attributes,
            **new_instance.extra_attributes,
        }
        session.merge(new_instance)  # the new details will override the old  ones
    else:  # we do not have any record yet for this day
        transition_type = "NEW_DATE_RECORDED"
        session.add(new_instance)
    if transition_type:
        calendar_day_transition = AirBnbRoomCalendarDayTransition(
            room_id=new_instance.room_id,
            calendar_day=new_instance.calendar_day,
            transition_type=transition_type,
            state=new_instance.state,
            price=new_instance.price,
            latest_prices_array=new_instance.latest_prices_array,
            minimum_stay_nights=new_instance.minimum_stay_nights,
            cleaning_fee=new_instance.cleaning_fee,
            currency=new_instance.currency,
            extra_attributes=new_instance.extra_attributes,
        )
        session.add(calendar_day_transition)
