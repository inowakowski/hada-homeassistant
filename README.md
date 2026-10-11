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

With [HACS](https://hacs.xyz), in two clicks:

1. Open this repository in the HACS of your Home Assistant, choose **Download**, and restart Home Assistant.

   [![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=inowakowski&repository=hada-homeassistant&category=integration)

2. Add the integration and confirm. There is nothing to enter.

   [![Open your Home Assistant instance and start setting up the HADA integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hada)

The buttons ask for the address of your Home Assistant the first time they are used, and remember it in the browser.

By hand, the same two steps:

1. In HACS, open the menu, choose **Custom repositories**, and add `https://github.com/inowakowski/hada-homeassistant` with the type **Integration**. Find **HADA** in HACS, download it, and restart Home Assistant.
2. Go to **Settings → Devices & services → Add integration**, choose **HADA** and confirm.

Without HACS: copy `custom_components/hada` into the `custom_components` folder of your Home Assistant configuration, restart, and continue with step 2.

## Updating

HACS tells you when a new version is out: **HADA** then shows under **Settings → System → Updates** in Home Assistant, and in HACS itself, with what changed. Download it there and restart Home Assistant.

- HACS looks for new versions of a repository added by hand when Home Assistant starts, and every two days after that. To look right now, open **HADA** in HACS and choose **Update information** from the menu.
- An installation made from the `main` branch, before there were versions, follows that branch instead. Choose **Redownload** once and pick a version, and HACS follows the versions from then on.
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
