import os

from dotenv import load_dotenv

_environment_loaded = False


def load_environment() -> None:
    global _environment_loaded
    if _environment_loaded:
        return

    load_dotenv()
    _environment_loaded = True


def get_env(name: str, default: str | None = None) -> str | None:
    load_environment()
    return os.getenv(name, default)


def get_train_timetable_api_key() -> str | None:
    return get_env("train_timetable_api")


def get_train_arrivals_api_key() -> str | None:
    return get_env("train_arrivals_api")


def get_gemini_api_key() -> str | None:
    return get_env("GEMENI_API_KEY")
