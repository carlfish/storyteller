import time
import threading


class IDGenerator:
    """
    Twitter Snowflake-style ID generator that creates unique 64-bit identifiers.

    The 64-bit ID format:
    - 41 bits: timestamp (milliseconds since epoch)
    - 10 bits: server ID (0-1023)
    - 12 bits: counter (0-4095)

    Features:
    - Thread-safe generation using locks
    - Clock drift protection
    - Epoch starting from January 2024
    - Up to 4096 IDs per millisecond per server
    """

    def __init__(self, server_id: int = 0):
        if not (0 <= server_id <= 1023):
            raise ValueError("server_id must be between 0 and 1023")

        self.server_id = server_id
        self.counter = 0
        self.last_timestamp = 0
        self.lock = threading.Lock()

        self.epoch = 1704067200000

        self.timestamp_bits = 41
        self.server_id_bits = 10
        self.counter_bits = 12

        self.max_counter = (1 << self.counter_bits) - 1

        self.server_id_shift = self.counter_bits
        self.timestamp_shift = self.counter_bits + self.server_id_bits

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)

    def generate(self) -> int:
        with self.lock:
            timestamp = self._get_timestamp()

            if timestamp < self.last_timestamp:
                raise RuntimeError("Clock moved backwards")

            if timestamp == self.last_timestamp:
                self.counter = (self.counter + 1) & self.max_counter
                if self.counter == 0:
                    while timestamp <= self.last_timestamp:
                        timestamp = self._get_timestamp()
            else:
                self.counter = 0

            self.last_timestamp = timestamp

            timestamp_part = (timestamp - self.epoch) << self.timestamp_shift
            server_part = self.server_id << self.server_id_shift
            counter_part = self.counter

            return timestamp_part | server_part | counter_part


_default_generator = IDGenerator(0)


def generate_id() -> int:
    return _default_generator.generate()


def new_generator(server_id: int = 0) -> IDGenerator:
    if server_id == 0:
        raise ValueError("Server ID must be greater than 0")

    return IDGenerator(server_id)
