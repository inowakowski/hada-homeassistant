# The HADA protocol

How [HADA](https://github.com/inowakowski/home-assistant-desktop-app), the desktop app, and this integration talk to each other. This file is the specification both sides are written against.

**Protocol version: 1.** Parts marked *(planned)* are specified here but not implemented by the integration yet; see [Status](#status).

## Transport

HADA connects to Home Assistant's WebSocket API (`/api/websocket`) and authenticates with a long-lived access token, as any API client does. Home Assistant never connects to the computer.

The integration adds commands to that API, all named `hada/…`. Everything below is an ordinary WebSocket API message: a command carries an `id` and a `type`, and is answered with a `result` message of the same `id`.

A Home Assistant without the integration answers `hada/connect` with the error `unknown_command`. That is how HADA tells that the integration is not installed or not set up.

## Connecting

The first command, sent once per connection:

```json
{
  "id": 5,
  "type": "hada/connect",
  "protocol": 1,
  "device": {
    "id": "laptop",
    "name": "Laptop",
    "app_version": "1.4.0",
    "os": "Windows",
    "os_version": "10.0.26100",
    "model": "Windows computer (Arm64)"
  },
  "entities": [ … ]
}
```

| Field | |
|---|---|
| `protocol` | The newest protocol version HADA speaks |
| `device.id` | Stable id of the computer: lowercase letters, digits and `_`, 1 to 64 characters. It is HADA's *Device ID* |
| `device.name` | What the device is called in Home Assistant. Entity ids are made from it |
| `device.app_version`, `os`, `os_version`, `model` | Optional; shown on the device page |
| `entities` | Every entity the computer has, see [Entities](#entities). At most 500 |

The result:

```json
{ "id": 5, "type": "result", "success": true,
  "result": { "protocol": 1, "integration_version": "0.1.0", "ignored": ["some_entity"] } }
```

| Field | |
|---|---|
| `protocol` | The version this connection speaks from now on: the lower of the two sides' |
| `ignored` | Ids of entities the integration left out, because it does not know their `kind` |

`hada/connect` is a subscription. Until the connection closes, or HADA sends `unsubscribe_events` for the `id` of the command, Home Assistant:

- shows the device's entities as available, and
- sends [commands](#commands-for-the-computer) for the computer as `event` messages with that `id`.

When the connection closes, however it closes, every entity of the device becomes *unavailable* at once.

A second `hada/connect` for the same device, from this or another connection, takes the place of the first.

### Errors

| Code | When |
|---|---|
| `unknown_command` | The integration is not installed |
| `not_found` | The integration is installed, but not set up (no *HADA* entry under **Devices & services**) |
| `unsupported_protocol` | HADA's `protocol` is older than the oldest the integration still speaks |
| `unauthorized` | The device id belongs to another Home Assistant user, see [Who may speak for a device](#who-may-speak-for-a-device) |
| `invalid_format` | The message does not have the shape described here |

## Entities

HADA is the source of truth about which entities a device has. The list in `hada/connect` is complete: an entity Home Assistant has for the device that is not in the list is removed, and one that is new is added. Home Assistant keeps what the user changed there (name, area, icon, whether it is enabled) for as long as the entity's `id` stays the same.

```json
{
  "id": "cpu_load",
  "kind": "sensor",
  "name": "CPU load",
  "icon": "mdi:cpu-64-bit",
  "device_class": null,
  "unit": "%",
  "state_class": "measurement",
  "enabled_by_default": true,
  "state": 12.5,
  "attributes": { "cores": 8 },
  "available": true
}
```

| Field | |
|---|---|
| `id` | Unique within the device: lowercase letters, digits and `_`, 1 to 64 characters |
| `kind` | One of the kinds below. An unknown kind is not an error: the entity is left out and named in `ignored` |
| `name` | Shown after the device name |
| `icon` | Optional, a Material Design icon such as `mdi:laptop` |
| `device_class`, `unit`, `state_class` | Optional, as Home Assistant understands them for that kind of entity. A `device_class` it does not know is dropped, not refused |
| `min`, `max`, `step` | For `number` |
| `enabled_by_default` | Optional, default `true`. `false` for entities that should start disabled in Home Assistant |
| `state` | Optional: the current state, see below |
| `attributes` | Optional: extra state attributes |
| `available` | Optional, default `true`. `false` while the source of this one entity is away |

Fields the integration does not know are ignored, so newer versions of HADA may send more.

| `kind` | Entity in Home Assistant | `state` |
|---|---|---|
| `sensor` | `sensor` | A number, a text, or `null` for unknown. With `device_class: timestamp`, a time in ISO 8601 |
| `binary_sensor` | `binary_sensor` | `true`, `false`, or `null` |
| `button` | `button` | None |
| `switch` | `switch` | `true`, `false`, or `null` |
| `number` | `number` | A number, or `null` |
| `notify` *(planned)* | `notify`, and the action `hada.notify` | None |
| `event` *(planned)* | `event` | None; see [Events](#events-from-the-computer) |

### Changing the entities

When entities are added, removed or described differently while connected, HADA sends the complete list again:

```json
{ "id": 9, "type": "hada/entities", "device_id": "laptop", "entities": [ … ] }
```

It works as the list in `hada/connect` does, and its result carries `ignored` likewise.

### Updating states

```json
{
  "id": 12,
  "type": "hada/update",
  "device_id": "laptop",
  "states": [
    { "id": "cpu_load", "state": 14.0 },
    { "id": "active_window", "state": "Inbox", "attributes": { "process": "outlook" } },
    { "id": "camera_in_use", "available": false }
  ]
}
```

Each item names an entity and carries what changed about it: `state`, `attributes`, `available`. What is left out stays as it was; `attributes`, when given, replaces all of them. An item for an entity the device does not have is skipped.

`hada/entities` and `hada/update` are only accepted from the connection that is connected as that device; otherwise the error is `not_found`.

## Commands for the computer

When an entity is used in Home Assistant, the integration sends a command on the `hada/connect` subscription:

```json
{ "id": 5, "type": "event",
  "event": { "command_id": "a1b2c3", "command": "set", "entity": "volume_level", "value": 30 } }
```

| `command` | For | Fields |
|---|---|---|
| `press` | `button` | |
| `set` | `switch`, `number` | `value`: `true` / `false`, or the number |
| `notify` *(planned)* | `notify` | `message`, and optionally `title` and `data`, shaped as Home Assistant's `notify.mobile_app_*` actions shape them |

HADA answers each command:

```json
{ "id": 14, "type": "hada/command_result", "device_id": "laptop",
  "command_id": "a1b2c3", "success": true }
```

or with `"success": false, "error": "…"`. Without an answer within 10 seconds, the action in Home Assistant fails; so it does when the computer goes away before answering. A command HADA does not know is answered with `success: false`.

`success` says that the computer took the command, not that what was wanted has happened: that shows in the states it reports.

The state of a switch or a number is never assumed: it changes in Home Assistant when HADA reports it with `hada/update`.

A picture in a notification that is a path at this Home Assistant is signed by the integration before the command is sent, so the computer can fetch it without an access token.

## Events from the computer

*(planned)*

```json
{ "id": 15, "type": "hada/event", "device_id": "laptop", "name": "quick_action", "value": "toggle_lamp" }
```

| `name` | `value` | What the integration does |
|---|---|---|
| `quick_action` | The id of the `event` entity | Triggers that entity, and fires `hada_event` |
| `notification_action` | The `action` of the pressed button | Fires `hada_event` |

`hada_event` has the data `device_id`, `name` and `value`, as the event HADA fires without the integration has.

## Who may speak for a device

The first `hada/connect` for a device id makes the Home Assistant user whose token was used its owner. Later connections under that id are accepted from that user and from administrators; anyone else gets `unauthorized`. A device is given up by deleting it in Home Assistant, which is possible while it is not connected.

No command needs an administrator's token.

## Versions

- The protocol version is a whole number. It changes only when an old peer could not work with a new one.
- Adding a field, a `kind`, a command for the computer or an event name does not change it: each side ignores, or reports, what it does not know.
- The integration says which versions it speaks in `const.py` (`PROTOCOL_VERSION`, `MIN_PROTOCOL_VERSION`).

## Status

| | Integration |
|---|---|
| `hada/connect`, `hada/entities`, `hada/update` | 0.1.0 |
| `sensor`, `binary_sensor` | 0.1.0 |
| Availability, removing entities that are gone, owner of a device | 0.1.0 |
| `button`, `switch`, `number`, the commands `press` and `set`, `hada/command_result` | 0.2.0 |
| `notify`, `event`, `hada/event` | planned |
