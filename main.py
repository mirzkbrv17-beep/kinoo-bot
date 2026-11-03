"""Kirish nuqtasi (Render: python main.py). Asosiy mantiq bot.py ichida."""
import asyncio

from bot import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
