import numpy as np

from firewood import schema


@schema(timestamp_field="actual_takeoff_time")
class FlightTakeoffEvent:
    """Schema definition for a Flight Takeoff Event."""

    flight_name: str
    expected_takeoff_time: np.int64
    actual_takeoff_time: np.int64
    delay: np.int32
    airline: str
    departure_airport: str
    arrival_airport: str
