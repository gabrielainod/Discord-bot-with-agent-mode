# Hosting TripleTBot without GitHub

You do **not** need GitHub, git, or a computer. Pick one of the three routes below;
all of them use the same package, the same `requirements.txt` and the same start command:

```
python main.py
```

Only one thing is mandatory in every route: an environment variable called
`DISCORD_TOKEN` holding your bot token. **Never paste the token in this chat or in a
Discord message** — put it in the host's "environment variables / secrets" screen.

---

## Route 1 — Panel host with ZIP upload (easiest from a phone)

This is the classic "Discord bot hosting" panel (Pterodactyl-based: Sillydev, Bloom,
Sparked, Pebble, Bot-Hosting and friends). Free tiers exist; uptime varies, so keep a
cheap paid panel in mind if the bot matters to you.

1. Sign in to the panel **with Discord** (no GitHub involved).
2. Create a server → choose the **Python** egg / "Python Generic" / "Discord.py" runtime.
3. Open the **File Manager** → open the `triplettbot.zip` file attached to this project
   (it is in the `dist/` folder) → **Upload** → then right-click it → **Unarchive**.
   (If the panel has no unzip button, use its "Upload folder" / SFTP instead.)
4. Go to **Startup** (or *Environment*) and add a variable:
   `DISCORD_TOKEN = your token here`
   Leave the startup command as `python main.py` (some panels want `python3 main.py`).
5. Press **Start**. Watch the console: you want
   `[TripleTBot] online as TripleTBot#1234 · 24 games ready`.
6. In Discord type `/play`. If the commands don't appear in an hour, add
   `GUILD_ID = <your server id>` to the variables and restart (instant sync).

The panel installs `requirements.txt` automatically on first boot (that is where
`discord.py`, `Pillow` and `python-chess` come from).

---

## Route 2 — Any VPS or shell you can reach from the phone

If you have a box (Hetzner/Contabo/Oracle free tier/whatever) or a panel that gives you a
terminal, paste this — it is self-contained:

```bash
curl -L -o tt.zip <link to triplettbot.zip>     # or upload the zip however you like
unzip tt.zip -d tripletbott && cd tripletbott
echo "DISCORD_TOKEN=your_token_here" > .env
bash start.sh
```

To keep it alive after you close the terminal:

```bash
nohup python3 main.py > bot.log 2>&1 &
# or, properly:
sudo apt install -y tmux && tmux new -d -s tt 'python3 main.py'
```

Docker instead (the repo ships a `Dockerfile`):

```bash
docker build -t tripletbott . && docker run -d --restart=always -e DISCORD_TOKEN=xxx -v $PWD/data:/app/data tripletbott
```

---

## Route 3 — Run it on an old Android phone (free, no accounts)

Perfect if you have a spare phone and a charger. This is the only completely free route
that is truly 24/7 and 100% yours.

1. Install **Termux** (from F-Droid, not the Play Store version).
2. `pkg update && pkg install python python-pillow unzip`
3. Get the ZIP onto the phone (download it from this workspace / USB / Drive), then:
   ```bash
   cd ~ && unzip tt.zip -d tripletbott && cd tripletbott
   pip install -r requirements.txt
   echo "DISCORD_TOKEN=your_token_here" > .env
   python main.py
   ```
4. Keep it running in the background: `termux-wake-lock` then
   `nohup python main.py > bot.log 2>&1 &`
5. Disable battery optimisation for Termux, leave it charging and on Wi-Fi.

If `pip install Pillow` fails, use the distro package: `pkg install python-pillow`.

---

## Route 4 — "Deploy from folder" hosts (no git)

Some platforms accept a **local folder upload / CLI push** instead of a Git repo:

- **Railway**: `npm i -g @railway/cli && railway login && railway up` inside the project
  folder (works from Termux too).
- **Fly.io**: `fly launch --no-deploy` then `fly deploy` (CLI, no repo needed).
- **Docker Hub + any container host**: build the image, push it, point the host at it.

All of them only need the same two things: `DISCORD_TOKEN` and the start command.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Console: `DISCORD_TOKEN is missing` | The variable is not set, or the file is `.env` in the wrong folder |
| `ModuleNotFoundError: discord` | Run `pip install -r requirements.txt` (some panels need it manually) |
| Bot online but `/play` doesn't show | Set `GUILD_ID`, restart; global commands take up to 1h |
| `4014 / Privileged intent` | Turn **Message Content Intent** OFF in the dev portal (TripleTBot doesn't need it) |
| Bot goes offline after a while | Free panels sleep; use a paid tier, a VPS, or the old-phone route |
| Buttons stopped working after a restart | Old messages keep their buttons but sessions live in memory — start a new `/play` |
| `data/stats.json` resets | Mount/persist the `data/` folder |

---

## What runs where

```
python main.py            → the Discord bot (needs DISCORD_TOKEN)
python tools/sim_server.py→ browser simulator, no token needed (great for testing)
python tools/selftest.py  → autoplays all 24 games and checks everything
```

The simulator on a host is handy: open `http://<host>:8000` and play all 24 games from the
phone browser before you even create the bot token.
