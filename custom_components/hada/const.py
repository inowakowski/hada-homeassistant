"""Constants of the HADA integration."""

from typing import Final

DOMAIN: Final = "hada"

# The protocol is described in PROTOCOL.md at the root of the repository.
PROTOCOL_VERSION: Final = 1
MIN_PROTOCOL_VERSION: Final = 1

MAX_ENTITIES: Final = 500

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1
SAVE_DELAY: Final = 10

MANUFACTURER: Final = "HADA"

KIND_SENSOR: Final = "sensor"
KIND_BINARY_SENSOR: Final = "binary_sensor"
KIND_BUTTON: Final = "button"
KIND_SWITCH: Final = "switch"
KIND_NUMBER: Final = "number"

COMMAND_PRESS: Final = "press"
COMMAND_SET: Final = "set"

# How long a computer has to answer a command before the action in Home Assistant fails.
COMMAND_TIMEOUT: Final = 10

ERR_UNSUPPORTED_PROTOCOL: Final = "unsupported_protocol"
