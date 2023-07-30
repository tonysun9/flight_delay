from datetime import timedelta
from typing import Union

from firewood_project.schemas.flight_takeoff import FlightTakeoffEvent

from firewood import transformation


@transformation
def average_delay_airport(takeoff: FlightTakeoffEvent, window: Union[timedelta, str]):
    """Compute the average delay at each airport."""
    return takeoff.groupby(["departure_airport"])["delay"].rolling(window).mean()


@transformation
def max_delay_airport(takeoff: FlightTakeoffEvent, window: Union[timedelta, str]):
    """Compute the max delay at each airport."""
    return takeoff.groupby(["departure_airport"])["delay"].rolling(window).max()


@transformation
def min_delay_airport_airline(
    takeoff: FlightTakeoffEvent, window: Union[timedelta, str]
):
    """Compute the min delay at each airport by airline."""
    return (
        takeoff.groupby(["departure_airport", "airline"])["delay"].rolling(window).min()
    )


@transformation
def average_delay_airport_airline(
    takeoff: FlightTakeoffEvent, window: Union[timedelta, str]
):
    """Compute the average delay at each airport by airline."""
    return (
        takeoff.groupby(["departure_airport", "airline"])["delay"]
        .rolling(window)
        .mean()
    )


@transformation
def max_delay_airport_airline(
    takeoff: FlightTakeoffEvent, window: Union[timedelta, str]
):
    """Compute the max delay at each airport by airline."""
    return (
        takeoff.groupby(["departure_airport", "airline"])["delay"].rolling(window).max()
    )
