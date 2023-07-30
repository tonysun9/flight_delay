import argparse
import csv
import logging
import os
import random
import time
from collections.abc import Generator
from functools import partial
from typing import Optional, Tuple, Optional, List
from kafka import KafkaIngester, KafkaUtils
from schemas.flight_takeoff import FlightTakeoffEvent

# Ingest events from this file in S3
FNAME = "flight_takeoff_data_next.csv"


def prepare_transaction_dataset(csv_file: str) -> list:
    with open(csv_file, "r") as file:
        reader = csv.reader(file)
        next(reader)
        rows = list(reader)

    return rows


def process_transaction(
    r,
    col_names: list[str],
    event: list,
) -> FlightTakeoffEvent:
    """
    Convert a row of the transaction dataset to be a TransactionEvent
    """
    event_dict = {
        event_col: event_value for event_col, event_value in zip(col_names, event)
    }

    transaction_event = FlightTakeoffEvent.parse_obj(event_dict)

    r.set(
        event_dict["flight_name"],
        ",".join(
            [
                event_dict["flight_time"],
                event_dict["expected_takeoff_time"],
                event_dict["actual_takeoff_time"],
                event_dict["departure_airport"],
                event_dict["arrival_airport"],
                event_dict["next_flight"],
            ]
        ),
    )

    return transaction_event


def main(num_events: int, kafka_conf_path: str = None, topic: str = None, redis=None):
    """
    Ingest events from transaction dataset to Kafka.
    """
    col_names = list(FlightTakeoffEvent.__annotations__.keys())
    events = prepare_transaction_dataset(csv_file=FNAME)
    # path_prefix = os.path.abspath(os.path.dirname(__file__))

    key_schema = KafkaUtils.load_schema(path="schemas/key.avsc")
    value_schema = KafkaUtils.load_schema(path="schemas/flight_takeoff.avsc")
    kakfa_conf = KafkaUtils.load_kafka_conf(kafka_conf_path)

    ingester = KafkaIngester(
        topic=topic,
        key_schema=key_schema,
        value_schema=value_schema,
        conf=kakfa_conf,
    )

    import redis

    r = redis.Redis(port=6379)
    processing_func = partial(
        process_transaction,
        col_names=col_names,
        r=r,
    )
    ingester.ingest_dataset(
        events=events,
        processing_func=processing_func,
        num_events=num_events,
    )


if __name__ == "__main__":
    main(num_events=6000, kafka_conf_path="kafka.config", topic="features")
