import os


class Settings:
    APP_NAME = "Kiosk AI Server"
    APP_VERSION = "1.1.0"

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "20"))
    OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "300"))

    USER_TYPE_CONFIDENCE_THRESHOLD = float(
        os.getenv("USER_TYPE_CONFIDENCE_THRESHOLD", "0.60")
    )
    SERVICE_CONFIDENCE_THRESHOLD = float(
        os.getenv("SERVICE_CONFIDENCE_THRESHOLD", "0.60")
    )


settings = Settings()