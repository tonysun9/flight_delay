import itertools
import pathlib
import random
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from functools import partial
from typing import Callable, Optional

import certifi
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from dataclasses_avroschema.avrodantic import AvroBaseModel
from pydantic import Field


class DefaultKey(AvroBaseModel):
    """
    Produces a random key.
    Kafka's SerializingProducer requires a key schema.
    """

    id: int = Field(default_factory=partial(random.randint, 0, sys.maxsize))


class Ingester(ABC):
    """An ingester sends data to a transport."""

    @abstractmethod
    def ingest_message(self, key, value):
        """Ingest a message."""
        ...


class KafkaUtils:
    """Utility class for Kafka-related operations"""

    @staticmethod
    def load_kafka_conf(path: str) -> dict:
        """Read Confluent Cloud configuration for librdkafka clients"""
        kafka_conf = dict(
            line.split("=")
            for line in (pathlib.Path(path).read_text(encoding="utf8").splitlines())
            if line and not line.startswith("#")
        )
        kafka_conf["ssl.ca.location"] = certifi.where()
        return kafka_conf

    @staticmethod
    def load_schema(path: str):
        """
        Reads an Avro schema from a filepath.
        Assumes the file is encoded in UTF-8.
        """
        with open(path, encoding="utf-8") as f:
            return f.read()


class KafkaMessageSerde:
    """KafkaMessageSerde class"""

    def __init__(
        self,
        key_schema: str,
        value_schema: str,
        schema_registry_conf: dict,
        kafka_conf: dict,
    ):
        self.key_schema = key_schema
        self.value_schema = value_schema

        # set up serializing producer configuration
        producer_conf = {
            k: v
            for k, v in kafka_conf.items()
            if k
            not in {
                "schema.registry.url",
                "basic.auth.user.info",
                "basic.auth.credentials.source",
            }
        }
        schema_registry_client = SchemaRegistryClient(schema_registry_conf)
        self.key_serializer = AvroSerializer(
            schema_registry_client=schema_registry_client,
            schema_str=key_schema,
            to_dict=lambda key, ctx: key.dict(),
        )
        producer_conf["key.serializer"] = self.key_serializer
        self.value_serializer = AvroSerializer(
            schema_registry_client=schema_registry_client,
            schema_str=value_schema,
            to_dict=lambda message, ctx: message.dict(),
        )
        producer_conf["value.serializer"] = self.value_serializer

        self.producer = SerializingProducer(producer_conf)


class KafkaIngester(Ingester):
    """Kafka Ingester"""

    def __init__(
        self,
        topic: str,
        key_schema: str,
        value_schema: str,
        conf: dict,
    ):
        schema_registry_conf = {"url": conf["schema.registry.url"]} | (
            {"basic.auth.user.info": conf["basic.auth.user.info"]}
            if "basic.auth.user.info" in conf
            else {}
        )

        self.topic = topic
        self.key_schema = key_schema
        self.value_schema = value_schema
        self.serde = KafkaMessageSerde(
            key_schema=key_schema,
            value_schema=value_schema,
            schema_registry_conf=schema_registry_conf,
            kafka_conf=conf,
        )
        self.producer: SerializingProducer = self.serde.producer

    def ingest_message(
        self,
        key,
        value,
        num_processed_events: Optional[int] = None,
        total_events: Optional[int] = None,
    ):
        """Ingest a message to Kafka."""
        # for data in some_data_source:
        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)

        acked = self.acked
        if num_processed_events and total_events:
            acked = partial(
                self.acked,
                num_processed_events=num_processed_events,
                total_events=total_events,
            )

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        self.producer.produce(
            topic=self.topic,
            key=key,
            value=value,
            on_delivery=acked,
        )

    def ingest_dataset(
        self,
        events: list,
        num_events: int,
        processing_func: Optional[Callable] = None,
    ) -> None:
        """
        Ingest each event in a dataset to Kafka.

        Parameters
        ----------
        dataset
            Generator over the dataset.
        num_events
            Number of events to process in the dataset.
        dataset_size (Optional)
            Size of the dataset. Used when ingesting infinite events.
        processing_func (Optional)
            Function to process each event in the dataset.
        """
        num_processed_events = 0
        KafkaIngester.progressbar(0, num_events, "processed events: ")

        for event in events[:num_events]:
            # Events wait to be processed (rather than dropped)
            #   if ingestion is exceeding rate limit

            if processing_func:
                processed_event = processing_func(event=event)

            num_processed_events += 1

            # generate a random key for every message ingested.
            # the random key will be used for evenly distributing across Kafka
            # partitions (key % partition_count -> partition #)
            key = DefaultKey()
            self.ingest_message(
                key,
                processed_event,
                num_processed_events=num_processed_events,
                total_events=num_events,
            )

        # Wait for any outstanding messages to be delivered and delivery report
        #   callbacks to be triggered.
        self.producer.flush()

    def acked(
        self,
        err,
        msg,
        num_processed_events: Optional[int] = None,
        total_events: Optional[int] = None,
    ):
        """
        Delivery report handler called on
        successful or failed delivery of message
        """
        if err is not None:
            print(f"Failed to deliver message: {err}")
        else:
            if num_processed_events and total_events:
                KafkaIngester.progressbar(
                    current_count=num_processed_events,
                    total=total_events,
                    prefix="processed events: ",
                )

            # Can uncomment below for more fine-grained detail on which topic and
            #   partition that message is being printed to.
            # print(
            #     f"Produced record to topic {msg.topic()} partition "
            #     f"[{msg.partition()}] @ offset {msg.offset()}"
            # )

    @staticmethod
    def progressbar(current_count: int, total: int, prefix: str = "", size=30):
        """Show a progress bar as Kafka is ingesting a dataset."""
        progress = int(size * current_count / total)
        print(
            f"{prefix}[{u'█'*progress}{('.'*(size-progress))}] {current_count}/{total}",
            end="\r" if current_count < total else "\n",
            flush=True,
        )
