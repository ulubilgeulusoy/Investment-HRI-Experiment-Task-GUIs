import os
from pathlib import Path


DEFAULT_DATA_ROOT = Path("/home/parc/csv")
DATA_ROOT_ENV_VAR = "INVESTMENT_HRI_DATA_ROOT"


def get_data_root() -> Path:
    """Return the local participant data directory used by the Ubuntu-side GUIs."""
    raw_value = os.environ.get(DATA_ROOT_ENV_VAR, "").strip()
    if raw_value:
        return Path(raw_value).expanduser().resolve()
    return DEFAULT_DATA_ROOT


def get_participant_dir(participant_id: str) -> Path:
    return get_data_root() / f"participant_{participant_id}"
