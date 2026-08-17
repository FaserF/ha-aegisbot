# AegisBot (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-aegisbot.svg?style=flat-square)](https://github.com/FaserF/ha-aegisbot/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-aegisbot.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![CI Orchestrator](https://github.com/FaserF/ha-aegisbot/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-aegisbot/actions/workflows/ci-orchestrator.yml)
[![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-aegisbot/latest/aegisbot.zip?label=Downloads%20(Current%20release)&style=flat-square)](https://github.com/FaserF/ha-aegisbot/releases)

A professional, modern Home Assistant integration for [**AegisBot**](https://github.com/FaserF/AegisBot) — the advanced Telegram (and Messenger) group defender. Monitor group health, track moderation stats, manage security protocols, and use AegisBot as a **full 1:1 Telegram Bot replacement** with smart polls, inline keyboard actions, and bidirectional real-time webhook event sync!

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [🤖 1:1 Telegram Parity](#-11-telegram-bot-parity--replacement) | [🗳️ Smart Polls](#️-smart-polls-for-meetings--food-planning) | [📦 Installation](#-installation) |
| [⚙️ Configuration](#️-configuration) | [🛠️ Options](#️-options-flow--allowed-chat-ids-sync) | [🧱 Entities](#-entities) | [📖 Automations](#-automation-examples) |
| [🧑‍💻 Development](#-development) | [💖 Credits](#-credits--acknowledgements) | [📄 License](#-license) | |

---

### Why use this integration?
Running both the official Home Assistant `telegram_bot` integration and AegisBot on the same Telegram Bot token causes polling conflicts (getUpdates collisions). 
This integration solves that completely: **AegisBot handles all Telegram polling and group defense**, while proxying every single Telegram action and event into Home Assistant in real time via Webhooks!

## ✨ Features

- **Full 1:1 Telegram Bot Parity**:
  - `notify.aegisbot` drop-in notification platform supporting HTML/Markdown, photos, videos, documents, audio, locations, inline keyboards, and polls.
  - Native services for all Telegram actions: `send_message`, `send_photo`, `send_video`, `send_document`, `send_animation`, `send_voice`, `send_location`, `send_poll`, `stop_poll`, `edit_message`, `edit_caption`, `edit_replymarkup`, `delete_message`, `answer_callback_query`, `leave_chat`.
- **Smart Polls (Meeting Coordination & Meal Planning)**:
  - Create native Telegram polls from Home Assistant automations.
  - AegisBot automatically tracks voter choices, computes real-time consensus, and fires `aegisbot_poll_result` events back to Home Assistant when consensus or majority is reached!
- **Real-Time Push Events via Webhooks**:
  - Receive real-time Telegram events in Home Assistant: `aegisbot_command`, `aegisbot_text`, `aegisbot_callback`, `aegisbot_poll_update`, `aegisbot_poll_answer`, `aegisbot_poll_result`.
  - Automatic bidirectional sync of `allowed_chat_ids` between Home Assistant and AegisBot.
- **Real-time Monitoring & Moderation**:
  - **Global Stats**: Protected groups, active warnings, and blocked spam links across all groups.
  - **Group Health**: Per-group health scores and warning counters.
  - **Content Locks**: Switches for Media, Links, RTL, Buttons, Stickers, and more.
  - **Moderation Actions**: `ban_user`, `unban_user`, `mute_user`, `warn_user`, `broadcast`, `adjust_reputation`, `apply_preset`.

---

## 🤖 1:1 Telegram Bot Parity & Replacement

### Notification Service (`notify.aegisbot`)
```yaml
action: notify.aegisbot
data:
  message: "🚨 Front door movement detected!"
  title: "Home Security"
  target: -100123456789
  data:
    photo: "https://example.com/snapshot.jpg"
    inline_keyboard:
      - ["Turn On Lights:light_on", "Siren Alarm:sound_alarm"]
```

### Direct Service Calls (`aegisbot.send_message`, `aegisbot.send_photo`, etc.)
```yaml
action: aegisbot.send_message
data:
  target: -100123456789
  message: "<b>System Update:</b> All backups completed successfully."
  parse_mode: html
  inline_keyboard:
    - ["View Status:view_status", "Dismiss:dismiss"]
```

---

## 🗳️ Smart Polls for Meetings & Food Planning

Send interactive polls and let AegisBot automatically compute the winning option:

```yaml
action: aegisbot.send_poll
data:
  target: -100123456789
  question: "Wann wollen wir uns zum Essen treffen?"
  options:
    - "Freitag 18:00 Uhr"
    - "Freitag 19:30 Uhr"
    - "Samstag 18:00 Uhr"
  category: "meeting"
  allows_multiple_answers: true
  is_anonymous: false
```

### Automation on Poll Result / Consensus:
```yaml
alias: "AegisBot Meeting Poll Consensus Handler"
trigger:
  - platform: event
    event_type: aegisbot_poll_result
condition:
  - condition: template
    value_template: "{{ trigger.event.data.status == 'consensus' }}"
action:
  - action: notify.aegisbot
    data:
      target: "{{ trigger.event.data.chat_id }}"
      message: "🎉 Treffen steht fest: <b>{{ trigger.event.data.winning_options[0].text }}</b>!"
```

---

## 📦 Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-aegisbot&category=integration)

1. Open HACS in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `FaserF/ha-aegisbot` with category **Integration**.
4. Search for "AegisBot".
5. Install and restart Home Assistant.

## ⚙️ Configuration

### 🔍 Auto-Discovery (Zeroconf / mDNS & Supervisor)
- **Automatic Detection**: Home Assistant discovers AegisBot automatically via Zeroconf (`_ha-aegisbot._tcp.local.`).
- **Supervisor Integration**: When using the official Add-on, internal URL and authentication token are prefilled automatically.

### 🛠️ Options Flow & Allowed Chat IDs Sync
In **Settings > Devices & Services > AegisBot > Configure**:
- Set **Scan Interval** (seconds).
- Configure **Allowed Telegram Chat IDs** (comma-separated). Changes are immediately synchronized with your AegisBot server.

---

## 🧱 Entities

| Platform | Category | Entities |
| :--- | :--- | :--- |
| **Sensor** | Global | Protected Groups, Active Warnings, AI FAQ Count, Malicious Links |
| **Sensor** | Per Group | Health Score, 7d Events, Warning Count |
| **Binary Sensor** | System | AegisBot Status, Database Status |
| **Binary Sensor** | Per Group | Group Active State |
| **Switch** | Per Group | Lock Media, Lock Links, Lock RTL, Lock Buttons, Lock Stickers, etc. |
| **Button** | System | Sync Global Filters, Vacuum Database, Run Maintenance Test |
| **Notify** | Communication | `notify.aegisbot` |

---

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, new features, testing on real hardware. Test devices cost money, and every donation helps me stay independent and free up more time for open-source work.

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
