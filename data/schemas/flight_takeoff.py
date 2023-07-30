from pydantic import BaseModel


class FlightTakeoffEvent(BaseModel):
    """Schema definition for a Flight Takeoff Event."""

    flight_name: str
    expected_takeoff_time: int
    actual_takeoff_time: int
    delay: int
    flight_time: int
    airline: str
    departure_airport: str
    arrival_airport: str
    next_flight: str
