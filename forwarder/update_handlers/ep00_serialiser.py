import time
from typing import Dict, Optional, Tuple, Union

import p4p
from caproto import Message as CA_Message
from p4p.client.thread import Cancelled, Disconnected, Finished, RemoteError
from streaming_data_types.epics_connection_info_ep00 import serialise_ep00
from streaming_data_types.fbschemas.epics_connection_info_ep00.EventType import (
    EventType,
)

from forwarder.kafka.kafka_helpers import seconds_to_nanoseconds
from forwarder.update_handlers.schema_serialisers import CASerialiser, PVASerialiser

# to-do: delete
# def _serialise(source_name: str, conn_status: EventType, timestamp_ns: int) -> Tuple[bytes, int]:
#     return (
#         serialise_ep00(
#             timestamp_ns=timestamp_ns,
#             event_type=conn_status,
#             source_name=source_name,
#         ),
#         timestamp_ns,
#     )


class ep00_Serialiser:
    def __init__(self, source_name: str):
        self._source_name = source_name
        self._conn_status: EventType = EventType.NEVER_CONNECTED

    def _serialise(self, timestamp_ns: int) -> Tuple[bytes, int]:
        return (
            serialise_ep00(
                timestamp_ns=timestamp_ns,
                event_type=self._conn_status,
                source_name=self._source_name,
            ),
            timestamp_ns,
        )

    def start_state_serialise(self):
        return self._serialise(seconds_to_nanoseconds(time.time()))


class CA_ep00_Serialiser(ep00_Serialiser, CASerialiser):
    def serialise(
        self, update: CA_Message, **unused
    ) -> Union[Tuple[bytes, int], Tuple[None, None]]:
        return None, None

    def ca_conn_serialise(
        self, pv: str, state: str
    ) -> Tuple[Optional[bytes], Optional[int]]:
        state_str_to_enum: Dict[str, EventType] = {
            "connected": EventType.CONNECTED,
            "disconnected": EventType.DISCONNECTED,
            "destroyed": EventType.DESTROYED,
        }
        self._conn_status = state_str_to_enum.get(state, EventType.UNKNOWN)
        return self._serialise(seconds_to_nanoseconds(time.time()))


class PVA_ep00_Serialiser(ep00_Serialiser, PVASerialiser):
    def serialise(
        self, update: Union[p4p.Value, RuntimeError], **unused
    ) -> Union[Tuple[bytes, int], Tuple[None, None]]:
        if isinstance(update, p4p.Value):
            timestamp = (
                update.timeStamp.secondsPastEpoch * 1_000_000_000
                + update.timeStamp.nanoseconds
            )
            if self._conn_status == EventType.CONNECTED:
                return None, None
            elif self._conn_status == EventType.NEVER_CONNECTED:
                self._conn_status = EventType.CONNECTED
                return self._serialise(timestamp)
        conn_state_map = {
            Cancelled: EventType.DESTROYED,
            Disconnected: EventType.DISCONNECTED,
            RemoteError: EventType.DISCONNECTED,
            Finished: EventType.DESTROYED,
        }
        self._conn_status = conn_state_map.get(type(update), EventType.UNKNOWN)
        return self._serialise(seconds_to_nanoseconds(time.time()))
