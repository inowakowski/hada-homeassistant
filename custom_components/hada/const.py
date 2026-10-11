"""Constants of the HADA integration."""

from typing import Final

DOMAIN: Final = "hada"

# The protocol is described in PROTOCOL.md at the root of the repository.
PROTOCOL_VERSION: Final = 1
MIN_PROTOCOL_VERSION: Final = 1

MAX_ENTITIES: Final = 500

# Any user of Home Assistant may connect a computer; this keeps one of them from filling it with devices.
MAX_DEVICES: Final = 250

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1
SAVE_DELAY: Final = 10

MANUFACTURER: Final = "HADA"

KIND_SENSOR: Final = "sensor"
KIND_BINARY_SENSOR: Final = "binary_sensor"
KIND_BUTTON: Final = "button"
KIND_SWITCH: Final = "switch"
KIND_NUMBER: Final = "number"
KIND_NOTIFY: Final = "notify"
KIND_EVENT: Final = "event"
KIND_MEDIA_PLAYER: Final = "media_player"

COMMAND_PRESS: Final = "press"
COMMAND_SET: Final = "set"
COMMAND_NOTIFY: Final = "notify"
COMMAND_MEDIA: Final = "media"

# What happens on a computer is fired as this event, with device_id, name and value; HADA fires the
# same event itself when it is connected without the integration.
EVENT_HADA: Final = "hada_event"
EVENT_NAME_QUICK_ACTION: Final = "quick_action"

# The one type of event an event entity has: the quick action it stands for was chosen.
EVENT_TYPE_PRESSED: Final = "pressed"

SERVICE_NOTIFY: Final = "notify"

# How long the address of a picture stays good for after it was signed; the computer fetches it at once.
SIGNED_PATH_SECONDS: Final = 60

# How long a computer has to answer a command before the action in Home Assistant fails.
COMMAND_TIMEOUT: Final = 10

ERR_UNSUPPORTED_PROTOCOL: Final = "unsupported_protocol"
ERR_TOO_MANY_DEVICES: Final = "too_many_devices"
