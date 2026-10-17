
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow the exam page to call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def parse_value(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


def normalize_key(key):
    key = key.strip().lower()

    if key.startswith("app_"):
        key = key[4:]

    if key == "num_workers":
        key = "workers"

    return key


def apply_layer(config, data):
    for key, value in data.items():
        key = normalize_key(key)
        if key in config:
            config[key] = parse_value(key, value)


def load_config():
    config = DEFAULTS.copy()

    # Layer 2: config.development.yaml
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        data = yaml.safe_load(yaml_path.read_text()) or {}
        apply_layer(config, data)

    # Layer 3: .env file
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()

            if key.startswith("APP_"):
                key = key[4:]
            elif key == "NUM_WORKERS":
                key = "workers"
            else:
                continue

            apply_layer(config, {key: value.strip()})

    # Layer 4: OS environment variables with APP_ prefix
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            apply_layer(config, {key: value})

    return config


@app.get("/effective-config")
def effective_config(
    set: list[str] = Query(default=[]),
):
    config = load_config()

    # Highest precedence: repeated CLI-style query overrides.
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key in config:
            config[key] = parse_value(key, value)

    # Never expose the actual API key.
    config["api_key"] = "*****"

    return config
