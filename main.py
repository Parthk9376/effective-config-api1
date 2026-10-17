
import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
        return value.strip().lower() in ("true", "1", "yes", "on")
    return str(value)

def load_config():
    config = DEFAULTS.copy()

    # Layer 2: config.development.yaml
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        try:
            import yaml
            data = yaml.safe_load(yaml_path.read_text()) or {}
            config.update(data)
        except Exception:
            pass

    # Layer 3: .env file
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "NUM_WORKERS":
                    key = "workers"
                elif key.startswith("APP_"):
                    key = key[4:].lower()
                else:
                    continue
                config[key] = parse_value(key, value)

    # Layer 4: OS environment variables with APP_ prefix
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            name = key[4:].lower()
            if name == "num_workers":
                name = "workers"
            config[name] = parse_value(name, value)

    return config

@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = load_config()

    # Highest precedence: CLI-style query overrides
    for item in set:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key == "num_workers":
            key = "workers"
        if key in config:
            config[key] = parse_value(key, value)

    # Always mask the API key
    config["api_key"] = "*****"

    return config
