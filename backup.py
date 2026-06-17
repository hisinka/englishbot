import asyncio
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("TG_ADMIN_ID")
POSTGRES_USER = os.getenv("POSTGRES_USER", "englishbot")
POSTGRES_DB = os.getenv("POSTGRES_DB", "englishbot")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


async def send_backup():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    with tempfile.TemporaryDirectory() as tmp:
        dump_path = os.path.join(tmp, f"backup_{timestamp}.sql")

        env = os.environ.copy()
        env["PGPASSWORD"] = POSTGRES_PASSWORD

        result = subprocess.run(
            [
                "pg_dump",
                "-h", POSTGRES_HOST,
                "-p", POSTGRES_PORT,
                "-U", POSTGRES_USER,
                "-d", POSTGRES_DB,
                "-f", dump_path,
                "--no-owner",
                "--no-acl",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        bot = Bot(token=TOKEN)
        async with bot:
            with open(dump_path, "rb") as f:
                await bot.send_document(
                    chat_id=int(ADMIN_ID),
                    document=f,
                    filename=os.path.basename(dump_path),
                    caption=f"backup englishbot · {timestamp} UTC",
                )


if __name__ == "__main__":
    asyncio.run(send_backup())
