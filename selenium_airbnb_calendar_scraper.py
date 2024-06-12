from datetime import datetime

from toardolandia.models import AirBnbCalendar


def get_or_increase_room_id(session, airbnb_room_calendar_data):
    """
    Args:
        session (_type_): _description_
        airbnb_room_calendar (_type_): _description_

    Returns:
        an instance of AirBnbCalendar object ready to be committed to DB.
        if this already existed in DB it updates the values.
        if did not exist, then it just created the object from the passed on values
    """
    previous_room_calendar_date = (
        session.query(AirBnbCalendar)
        .filter_by(
            room_id=airbnb_room_calendar_data["room_id"],
            date=airbnb_room_calendar_data["date"],
        )
        .first()
    )
    if not previous_room_calendar_date:
        room_calendar_date = AirBnbCalendar(**airbnb_room_calendar_data)
        return room_calendar_date
    else:
        if (
            previous_room_calendar_date.is_available
            != airbnb_room_calendar_data["is_available"]
        ):
            print(
                f"changed availability for room_id='{airbnb_room_calendar_data['room_id']}'. from {previous_room_calendar_date.is_available} to {airbnb_room_calendar_data['is_available']}"
            )
            previous_room_calendar_date.is_available = airbnb_room_calendar_data[
                "is_available"
            ]
            previous_room_calendar_date.availability_info = airbnb_room_calendar_data[
                "availability_info"
            ]
            previous_room_calendar_date.availability_change_fetch_id = (
                airbnb_room_calendar_data["last_fetch_id"]
            )
            previous_room_calendar_date.availability_change_fetch_id_previous = (
                previous_room_calendar_date.last_fetch_id
            )
        if (
            previous_room_calendar_date.batch_start_date
            != airbnb_room_calendar_data["batch_start_date"]
        ) | (
            previous_room_calendar_date.batch_end_date
            != airbnb_room_calendar_data["batch_end_date"]
        ):
            print(
                f"changed batch for room_id='{airbnb_room_calendar_data['room_id']}'. from {previous_room_calendar_date.batch_start_date}|{previous_room_calendar_date.batch_end_date} to {airbnb_room_calendar_data['batch_start_date']}|{airbnb_room_calendar_data['batch_end_date']}"
            )
            previous_room_calendar_date.previous_batch_start_date = (
                previous_room_calendar_date.batch_start_date
            )
            previous_room_calendar_date.previous_batch_end_date = (
                previous_room_calendar_date.batch_end_date
            )
            previous_room_calendar_date.batch_start_date = airbnb_room_calendar_data[
                "batch_start_date"
            ]
            previous_room_calendar_date.batch_end_date = airbnb_room_calendar_data[
                "batch_end_date"
            ]
            previous_room_calendar_date.batch_change_fetch_id = (
                airbnb_room_calendar_data["last_fetch_id"]
            )
            previous_room_calendar_date.batch_change_fetch_id_previous = (
                previous_room_calendar_date.last_fetch_id
            )

        if (
            previous_room_calendar_date.price_breakdown
            != airbnb_room_calendar_data["price_breakdown"]
        ):
            print(
                f"changed price_breakdown for room_id='{airbnb_room_calendar_data['room_id']}'. from {previous_room_calendar_date.price_breakdown} to {airbnb_room_calendar_data['price_breakdown']}"
            )
            previous_room_calendar_date.price_change_fetch_id = (
                airbnb_room_calendar_data["last_fetch_id"]
            )
            previous_room_calendar_date.price_change_fetch_id_previous = (
                previous_room_calendar_date.last_fetch_id
            )
            previous_room_calendar_date.price_breakdown = airbnb_room_calendar_data[
                "price_breakdown"
            ]
        previous_room_calendar_date.last_fetch_id = airbnb_room_calendar_data[
            "last_fetch_id"
        ]
        previous_room_calendar_date.updated_date = datetime.utcnow()
        previous_room_calendar_date.version_id += 1
        return previous_room_calendar_date
