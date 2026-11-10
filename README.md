# HADA for Home Assistant

The Home Assistant side of [HADA](https://github.com/inowakowski/home-assistant-desktop-app), the Home Assistant Desktop App: computers running HADA show up in Home Assistant as devices, with their own entities, without an MQTT broker.

It needs HADA 1.4.0 or newer on the computer, and Home Assistant 2024.8 or newer; the media player needs HADA 1.5.0. HADA can also work without this integration, through MQTT or with Home Assistant alone; [Which connection to choose](https://github.com/inowakowski/home-assistant-desktop-app/blob/main/docs/home-assistant/choosing.md) compares the three.

## What it does

- A computer connects to Home Assistant by itself and describes its entities; there is nothing to set up per computer.
- The entities have unique ids: they can be renamed, put in an area and switched off in Home Assistant, and are kept when it restarts.
- An entity the computer no longer has is removed.
- When a computer goes away, for whatever reason, its entities are *unavailable* at once.
- Buttons, switches and numbers are real ones: lock the screen, set the volume, mute, from a dashboard or an automation.
- The computer as a media player: what is playing, play, pause, next and previous, volume and mute in one entity.
- Notifications with all a phone's may carry, through the action `hada.notify`: a picture (a camera's too), buttons, a tag to replace or take one back, an address to open.
- Quick actions chosen on the computer are `event` entities, and fire the event `hada_event`.

It needs no broker and opens no port on the computer: HADA connects to Home Assistant, with a long-lived access token, as it does without the integration. The token of any user will do.

## Installing

HADA is in the catalog of the Marketplace, which Home Assistant has built in since 2026.11, so there is no repository to add. In two clicks:

1. Open HADA in the Marketplace of your Home Assistant and choose **Install**.

   [![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=inowakowski&repository=hada-homeassistant&category=integration)

2. Home Assistant loads it at once, without a restart, and opens its setup: confirm. There is nothing to enter. If the setup does not open, start it with this button:

   [![Open your Home Assistant instance and start setting up the HADA integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hada)

The buttons ask for the address of your Home Assistant the first time they are used, and remember it in the browser.

By hand, the same two steps:

1. Go to **Settings → Marketplace**, search for **HADA**, open it and choose **Install**.
2. If its setup does not open, go to **Settings → Devices & services → Add integration**, choose **HADA** and confirm.

**Add from link** is not needed and does not work for HADA: it is for repositories the catalog does not list, and the Marketplace turns down one that it already has.

Before Home Assistant 2026.11, with [HACS](https://hacs.xyz): HADA is in HACS's default list too. Find **HADA** in HACS (or open it with [this link](https://my.home-assistant.io/redirect/hacs_repository/?owner=inowakowski&repository=hada-homeassistant&category=integration)), choose **Download**, restart Home Assistant, and add the integration as in step 2.

Without the Marketplace or HACS: copy `custom_components/hada` into the `custom_components` folder of your Home Assistant configuration, restart, and add the integration as in step 2.

## Updating

When a new version is out, **HADA** shows under **Settings → Updates** (**Settings → System → Updates** before 2026.11), with what changed. Install it there and restart Home Assistant; a repair under **Settings → System → Repairs** reminds you and can restart it for you.

- The Marketplace, and HACS before it, look for new versions in the catalog every 6 hours.
- An installation made from the `main` branch, before there were versions, follows that branch instead. Install a version once, and updates follow the versions from then on: in the Marketplace, **Install another version** in the menu of HADA's page; in HACS, **Redownload**.
- HADA on the computer also says so, on its Overview page, when the integration here is older than it needs.

## Connecting a computer

In HADA, on the **Connections** page, add this Home Assistant under **Home Assistant (WebSocket)**, with its address and a long-lived access token, and set **Entities** to **Through the HADA integration**. The computer then appears under **Settings → Devices & services → HADA**.

While the integration is missing or not added yet, the card of that Home Assistant on HADA's **Overview** page says so, and HADA tries again every minute.

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

A pressed button fires `hada_event` with `name: notification_action`, the button's `action` as `value`, and the computer's Device ID as `device_id`:

```yaml
triggers:
  - trigger: event
    event_type: hada_event
    event_data:
      device_id: laptop
      name: notification_action
      value: open_door
```

Name the computer, as `device_id` does here, in every automation that starts from `hada_event`. Any user of Home Assistant may connect a computer of their own, and its events carry the same names and values; without `device_id`, theirs would open the door too. Through the integration a computer fires events only under its own Device ID.

For an action that matters, such as opening a door, also check *who* fired the event. Home Assistant lets the companion app of any of its users fire any event with any data, `hada_event` and `device_id: laptop` included; what it cannot make up is the user the event comes from, which is the user whose token the computer connected with:

```yaml
conditions:
  - condition: template
    value_template: "{{ trigger.event.context.user_id == '0123456789abcdef0123456789abcdef' }}"
```

The id is that user's, shown under **Settings → People → Users** with advanced mode on.

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
