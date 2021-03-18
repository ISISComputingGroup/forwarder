import time
from threading import Lock
from typing import Optional, Tuple

from caproto import ReadNotifyResponse
from caproto.threading.client import PV
from caproto.threading.client import Context as CAContext

from forwarder.application_logger import get_logger

from forwarder.kafka.kafka_helpers import (
    publish_connection_status_message,
    seconds_to_nanoseconds,
    _nanoseconds_to_milliseconds,
)
from forwarder.kafka.kafka_producer import KafkaProducer
from forwarder.repeat_timer import RepeatTimer, milliseconds_to_seconds
from forwarder.update_handlers.schema_serialisers import schema_serialisers


class CAUpdateHandler:
    """
    Monitors via EPICS v3 Channel Access (CA),
    serialises updates in FlatBuffers and passes them onto an Kafka Producer.
    CA support from caproto library.
    """

    def __init__(
        self,
        producer: KafkaProducer,
        context: CAContext,
        pv_name: str,
        output_topic: str,
        schema: str,
        periodic_update_ms: Optional[int] = None,
    ):
        self._logger = get_logger()
        self._producer = producer
        self._output_topic = output_topic
        self._cached_update: Optional[Tuple[ReadNotifyResponse, int]] = None
        # self._output_type: Any = None
        self._repeating_timer = None
        self._cache_lock = Lock()

        try:
            self._message_serialiser = schema_serialisers[schema](pv_name)
        except KeyError:
            raise ValueError(
                f"{schema} is not a recognised supported schema, use one of {list(schema_serialisers.keys())}"
            )

        (self._pv,) = context.get_pvs(
            pv_name, connection_state_callback=self._connection_state_callback
        )
        # Subscribe with "data_type='time'" to get timestamp and alarm fields
        sub = self._pv.subscribe(data_type="time")
        sub.add_callback(self._monitor_callback)

        if periodic_update_ms is not None:
            self._repeating_timer = RepeatTimer(
                milliseconds_to_seconds(periodic_update_ms), self.publish_cached_update
            )
            self._repeating_timer.start()

    def _monitor_callback(self, sub, response: ReadNotifyResponse):
        # Skip PV updates with empty values
        try:
            if response.data.size == 0:
                return
        except AttributeError:
            # Enum values for example don't have .size, just continue
            pass

        with self._cache_lock:
            timestamp = seconds_to_nanoseconds(response.metadata.timestamp)
            # If this is the first update or the alarm status has changed, then
            # include alarm status in message
            if (
                self._cached_update is None
                or response.metadata.status != self._cached_update[0].metadata.status
            ):
                self._publish_message(
                    self._message_serialiser.serialise(response, serialise_alarm=True),
                    timestamp,
                )
            else:
                self._publish_message(
                    self._message_serialiser.serialise(response, serialise_alarm=False),
                    timestamp,
                )
            self._cached_update = (response, timestamp)
            if self._repeating_timer is not None:
                self._repeating_timer.reset()

    def _connection_state_callback(self, pv: PV, state: str):
        publish_connection_status_message(
            self._producer,
            self._output_topic,
            self._pv.name,
            seconds_to_nanoseconds(time.time()),
            state,
        )

    def publish_cached_update(self):
        with self._cache_lock:
            if self._cached_update is not None:
                # Always include current alarm status in periodic update messages
                self._publish_message(
                    self._message_serialiser.serialise(
                        self._cached_update[0], serialise_alarm=True
                    ),
                    self._cached_update[1],
                )

    def _publish_message(self, message: bytes, timestamp_ns: int):
        self._producer.produce(
            self._output_topic, message, _nanoseconds_to_milliseconds(timestamp_ns)
        )

    def stop(self):
        """
        Stop periodic updates and unsubscribe from PV
        """
        if self._repeating_timer is not None:
            self._repeating_timer.cancel()
        self._pv.unsubscribe_all()
