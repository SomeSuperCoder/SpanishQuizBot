from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    bot_token: str
    whitelist_usernames: List[str] = []
    database_path: str = "bot.db"
    proxy_url: str = "http://127.0.0.1:10809"
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()

# Populated at startup by main._async_main if proxy is reachable.
# AI service uses this to route httpx calls through the SOCKS/HTTP proxy.
# None means no proxy — direct connection.
active_proxy_url: str | None = None