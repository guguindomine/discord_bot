# 🤖 Paradox Bot

A multi-purpose, high-performance Discord bot built with Python, `discord.py`, and MongoDB. Specially designed for large gaming communities with built-in support for carry services, helper applications, advanced moderation, and automated boosting rewards.

---

## ✨ Features

### 🎟️ Ticket & Helper Systems
| Feature | Description |
|---|---|
| **Carry Service** | Interactive menus for members to request carries in multiple games (ALS, AV, ASTD, etc). |
| **Helper Applications** | Automated application forms for players to apply for helper/booster roles. |
| **Vouch System** | Allow users to vouch for helpers/staff. Tracks vouch count and auto-calculates Vouch Levels. |
| **Macro Support** | Dedicated tickets for purchasing or setting up gaming macros. |

### 🛡️ Security & Moderation
| Feature | Description |
|---|---|
| **Swear Word Filter** | Auto-deletes messages with banned words, warns the user, and manages a punishment system (mutes/quarantines). |
| **Anti-Scam / Phishing** | Detects malicious links, deletes them instantly, and tracks strikes. Auto-bans/quarantines repeat offenders. |
| **Quarantine System** | Temporarily strips users of all their roles and traps them in a `#quarantine` channel until a mod reviews them. |
| **Log Whitelist** | Advanced whitelist to allow specific users/admins to bypass the swear filter and logging. |

### 💎 Server & Community
| Feature | Description |
|---|---|
| **Server Boosting Rewards** | Sends custom, beautiful embed messages when someone boosts the server. |
| **Interactive Boost Roles** | Allows boosters to select their own custom colored role from a dropdown menu! |
| **Auto-Role** | Automatically assigns a base role to all new members. |
| **Greetings** | Highly customizable Welcome/Goodbye embeds with banner images. |
| **Interactive Polls** | Create quick community polls with upvote/downvote buttons. |

### 🗄️ Database
| Feature | Description |
|---|---|
| **MongoDB Atlas** | Fully asynchronous cloud database backend using `motor`. Ensures vouches, strikes, and quarantines survive bot restarts on ephemeral hosts like Railway. |

---

## 🚀 Setup & Installation

### 1. Create a Discord Bot
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it **Paradox Bot**
3. Go to **Bot** → click **Reset Token** → **Copy** the token
4. Go to **Bot** → enable these **Privileged Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Administrator` (or pick specific ones)
   - Copy the URL and open it to invite the bot to your server

### 2. Configure Local Settings
Open `config.json` and fill in the basics (most settings can be configured via Discord commands later!):

```json
{
    "TOKEN": "paste-your-bot-token-here",
    "PREFIX": "!",
    "AUTO_ROLE_NAME": "Member",
    "WELCOME_CHANNEL_ID": 123456789,
    "GOODBYE_CHANNEL_ID": 123456789
}
```

### 3. Database Setup (MongoDB)
This bot uses MongoDB to safely store user data on ephemeral hosts like Railway.
1. Add `MONGO_URI` as an environment variable in your host (set it to your MongoDB Atlas connection string).
2. Start the bot.
3. Run `!migrate db` inside Discord to transfer any old legacy data from `config.json` into MongoDB.

### 4. Install & Run
```bash
pip install -r requirements.txt
python bot_main.py
```

---

## 📋 Essential Commands

Type `!help paradox` in Discord for a fully interactive menu!

### ⚙️ Setup & Config (Admin)
| Command | Description |
|---|---|
| `!setrole <role>` | Set the auto-join role |
| `!setwelcomechannel <#ch>` | Set where greetings go |
| `!setlogchannel <#ch>` | Set where logs go |
| `!setwelcome <msg>` | Set the join message |
| `!setimg <welcome/goodbye> <url>` | Set banners |

### 🎟️ Tickets & Apps (Admin)
| Command | Description |
|---|---|
| `!setupticket <support/macro/carry/helper>`| Spawns interactive ticket buttons |
| `!addgame <ID> <Emoji> <Name>` | Add new game to carry/helper menus |
| `!togglegame <ID>` | Toggle a game active/inactive |
| `!sethelpertext <id> <questions>` | Configure helper application forms |
| `!setvouchchannel <#ch>` | Set where vouches go |

### 💎 Server Boost (Admin)
| Command | Description |
|---|---|
| `!setboostchannel <#ch>` | Set the boost log |
| `!setboostrole <role>` | Set the auto-given role |
| `!addboostselectrole <role>` | Add role to booster selector |
| `!testboost` | Simulate a boost event |

### 🛡️ Security & Moderation (Mod/Admin)
| Command | Description |
|---|---|
| `!togglefilter` | Toggle swear detection |
| `!addscam <link>` | Add to phishing blacklist |
| `!quarantine <@user>` | Send to quarantine manually |
| `!unquarantine <@user>` | Release user from prison |
| `!purge <num>` | Delete bulk messages (1-100) |
| `!mute <@user> <min>` | Timeout a member |
| `!softban <@user>` | Kick & clear messages |

### 📊 General
| Command | Description |
|---|---|
| `!poll "Question" <time>` | Create interactive poll |
| `!vouches [@user]` | Check your vouch level |
| `!swearlog [@user]` | View infraction history/top |
| `!botinfo` / `!serverinfo` | See stats & features |

---

## 📁 File Structure

```
├── bot_main.py        # Main bot entry point (events + commands)
├── bot_functions.py   # Helper functions (filter logic, formatting)
├── bot_database.py    # Asynchronous MongoDB wrapper
├── config.json        # Bot configuration (menus, token, settings)
├── requirements.txt   # Python dependencies
└── README.md          # This file
```
