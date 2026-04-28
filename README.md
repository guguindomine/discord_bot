# 🤖 Paradox Bot

A multi-purpose Discord bot built with Python and discord.py.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Auto-Role** | Automatically assigns a role to new members |
| **Welcome Messages** | Sends an embed in channel + optional DM when someone joins |
| **Goodbye Messages** | Sends an embed when someone leaves |
| **!hello / !goodbye** | Custom greeting commands anyone can use |
| **Swear Word Filter** | Auto-deletes messages with banned words and warns the user |
| **Moderation** | `!kick`, `!ban`, `!purge` commands for mods |
| **Server Info** | `!serverinfo` and `!botinfo` commands |

---

## 🚀 Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it **Paradox Bot**
3. Go to **Bot** → click **Reset Token** → **Copy** the token
4. Go to **Bot** → enable these **Privileged Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Administrator` (or pick specific ones)
   - Copy the URL and open it to invite the bot to your server

### 2. Configure the Bot

Open `config.json` and fill in:

```json
{
    "TOKEN": "paste-your-bot-token-here",
    "AUTO_ROLE_NAME": "Member",
    "WELCOME_CHANNEL_ID": 123456789,
    "GOODBYE_CHANNEL_ID": 123456789
}
```

- **TOKEN** — Your bot token from step 1
- **AUTO_ROLE_NAME** — The role to auto-assign (must exist in your server)
- **WELCOME_CHANNEL_ID** — Right-click a channel → Copy ID (enable Developer Mode in Discord settings)
- **GOODBYE_CHANNEL_ID** — Same as above (can be the same channel)

### 3. Install & Run

```bash
pip install -r requirements.txt
python bot_main.py
```

---

## 📋 Commands

### Everyone
| Command | Description |
|---|---|
| `!hello` | Bot sends the custom hello message |
| `!goodbye` | Bot sends the custom goodbye message |
| `!botinfo` | Shows bot stats and features |
| `!serverinfo` | Shows server information |

### Admin Only
| Command | Description |
|---|---|
| `!sethello <message>` | Set a custom hello message |
| `!setgoodbye <message>` | Set a custom goodbye message |
| `!setrole <role name>` | Set the auto-assign role |
| `!setwelcomechannel #channel` | Set welcome/goodbye channel |
| `!addswear <word>` | Add a word to the swear filter |
| `!removeswear <word>` | Remove a word from the swear filter |
| `!togglefilter` | Turn the swear filter on/off |

### Moderator
| Command | Description |
|---|---|
| `!purge <amount>` | Bulk delete messages (1-100) |
| `!kick @user [reason]` | Kick a member |
| `!ban @user [reason]` | Ban a member |

---

## 📁 File Structure

```
├── bot_main.py        # Main bot (events + commands)
├── bot_functions.py   # Helper functions (filter, config, formatting)
├── config.json        # Bot configuration (token, settings)
├── requirements.txt   # Python dependencies
└── README.md          # This file
```
