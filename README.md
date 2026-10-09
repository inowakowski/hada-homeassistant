# HADA for Home Assistant

The Home Assistant side of [HADA](https://github.com/inowakowski/home-assistant-desktop-app), the Home Assistant Desktop App: computers running HADA show up in Home Assistant as devices, with their own entities, without an MQTT broker.

> **Early version.** Everything in [PROTOCOL.md](PROTOCOL.md) is built, but HADA itself cannot use this integration before its next version.

## What it does

- A computer connects to Home Assistant by itself and describes its entities; there is nothing to set up per computer.
- The entities have unique ids: they can be renamed, put in an area and switched off in Home Assistant, and are kept when it restarts.
- An entity the computer no longer has is removed.
- When a computer goes away, for whatever reason, its entities are *unavailable* at once.
- Buttons, switches and numbers are real ones: lock the screen, set the volume, mute, from a dashboard or an automation.
- Notifications with all a phone's may carry, through the action `hada.notify`: a picture (a camera's too), buttons, a tag to replace or take one back, an address to open.
- Quick actions chosen on the computer are `event` entities, and fire the event `hada_event`.

It needs no broker and opens no port on the computer: HADA connects to Home Assistant, with a long-lived access token, as it does without the integration. The token of any user will do.

## Installing

With [HACS](https://hacs.xyz):

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/inowakowski/hada-homeassistant` with the type **Integration**.
3. Find **HADA** in HACS, download it, and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, choose **HADA** and confirm. There is nothing to enter.

Without HACS: copy `custom_components/hada` into the `custom_components` folder of your Home Assistant configuration, restart, and continue with step 4.

## Connecting a computer

In HADA, on the **Connections** page, add this Home Assistant under **Home Assistant (WebSocket)** and choose the HADA integration for its entities. The computer then appears under **Settings → Devices & services → HADA**.

To remove a computer, delete its device there while the computer is not connected.

## Notifications

`notify.send_message` shows a text and a title. For more, use `hada.notify` with the same entity:

```yaml
action: hada.notify
target:
  entity_id: notify.laptop_notification
data:
  title: Front door
  message: Someone is at the door.
  data:
    image: /api/camera_proxy/camera.front_door
    tag: door
    actions:
      - action: open_door
        title: Open
```

A pressed button fires `hada_event` with `name: notification_action` and the button's `action` as `value`:

```yaml
triggers:
  - trigger: event
    event_type: hada_event
    event_data:
      name: notification_action
      value: open_door
```

What `data` may carry is described in [HADA's documentation](https://github.com/inowakowski/home-assistant-desktop-app/blob/main/docs/features/notifications.md).

## How it works

See [PROTOCOL.md](PROTOCOL.md): the commands a computer sends over Home Assistant's WebSocket API, and what the integration does with them.

## Developing

```bash
python -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

The tests run a Home Assistant in the process, which Home Assistant supports on Linux and macOS, not on Windows; there they run in CI.
