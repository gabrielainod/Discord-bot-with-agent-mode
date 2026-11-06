"""Universal entry point.

Hosting panels (Pterodactyl, Replit, Bot-Hosting style, Heroku-like, Docker, VPS)
all look for a single file to run. This is it: `python main.py`.

It simply boots TripleTBot; everything else lives in the `tripletbot` package.
"""
from tripletbot.discordbot.bot import run

if __name__ == "__main__":
    run()
