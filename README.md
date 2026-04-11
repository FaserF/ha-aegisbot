# AegisBot (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-aegisbot.svg?style=flat-square)](https://github.com/FaserF/ha-aegisbot/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-aegisbot.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![CI Orchestrator](https://github.com/FaserF/ha-aegisbot/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-aegisbot/actions/workflows/ci-orchestrator.yml)

A professional, modern Home Assistant integration for **AegisBot** — the advanced Telegram (and Messenger) group defender. Monitor group health, track moderation stats, and manage security protocols directly from your Home Assistant dashboard.

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🛡️ Security](SECURITY.md) |
| [🛠️ Options](#️-options-flow) | [🧱 Entities](#-entities) | [📖 Automations](#-automation-examples) | [❓ FAQ](#-troubleshooting--faq) |
| [🧑‍💻 Development](#-development) | [💖 Credits](#-credits--acknowledgements) | [📄 License](#-license) | |

### Why use this integration?
AegisBot is a powerful orchestrator for group management. This integration allows you to bridge the gap between your community management and your smart home/dashboard. You can trigger security lockdowns, monitor threat levels, and get alerted to critical moderation events natively in Home Assistant.

## ✨ Features

- **Real-time Monitoring**:
  - **Global Stats**: Total protected groups, active warnings, and malicious links detected across your entire fleet.
  - **Group Health**: Per-group health scores based on recent activity and threat ratios.
  - **AI Intelligence**: Monitor the usage and performance of your Gemini-powered FAQ system.
- **Security Controls**:
  - **Content Locks**: Toggles for individual group security settings like Media, Links, RTL, Buttons, and Stickers.
  - **System Status**: Monitor the connectivity and latency of your AegisBot instance and its database.
- **Administrative Actions**:
  - **Filter Sync**: Manually trigger a synchronization of your global blocklists and filters.
  - **Federation Sync**: Propagate security settings across your federation in real-time.
  - **Group Moderation & Actions**: Perform Telegram actions directly via HA Services (`send_message`, `ban_user`, `mute_user`, `warn_user`, etc.).
- **Optimized for Reliability**:
  - **DataUpdateCoordinator**: Efficient state polling that respects your server resources.
  - **Diagnostics**: Full support for Home Assistant diagnostic exports to help with troubleshooting.

## 📦 Installation

### HACS (Recommended)

This integration is fully compatible with [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=FaserF/ha-aegisbot&category=integration)

1. Open HACS in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `FaserF/ha-aegisbot` with category **Integration**.
4. Search for "AegisBot".
5. Install and restart Home Assistant.

## ⚙️ Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow.svg)](https://my.home-assistant.io/redirect/config_flow/?domain=aegisbot)

1. Navigate to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **AegisBot**.
3. Enter your AegisBot details:
   - **URL**: Your AegisBot instance URL (e.g., `https://aegis.yourdomain.com`).
   - **API Key**: A secure API token generated via the AegisBot dashboard or CLI.

## 🧱 Entities

The integration provides sensors and controls categorized by group and system status.

| Platform | Category | Entities |
| :--- | :--- | :--- |
| **Sensor** | Global | Protected Groups, Active Warnings, AI FAQ Count, Malicious Links |
| **Sensor** | Per Group | Health Score, 7d Events, Warning Count |
| **Binary Sensor** | System | AegisBot Status, Database Status |
| **Binary Sensor** | Per Group | Group Active State |
| **Switch** | Per Group | Lock Media, Lock Links, Lock RTL, Lock Buttons, Lock Stickers, etc. |
| **Button** | System | Sync Global Filters |

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, new features, testing on real hardware. Test devices cost money, and every donation helps me stay independent and free up more time for open-source work.

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
