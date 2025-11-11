import os
from pathlib import Path

# ---------- Carga .env robusta ----------
env_loaded_from = None
try:
    from dotenv import load_dotenv, find_dotenv  # pip install python-dotenv

    # 1) Intenta encontrar .env empezando por el CWD (donde ejecutas python)
    env_path = find_dotenv(usecwd=True)

    # 2) Si no lo encontró, busca en el repo: .../fuvexbn/config/settings.py -> repo_root/.env
    if not env_path:
        repo_root = Path(__file__).resolve().parents[2]  # .../fuvexbn_project
        candidate = repo_root / ".env"
        if candidate.exists():
            env_path = str(candidate)

    if env_path:
        load_dotenv(env_path, override=False)
        env_loaded_from = env_path
    else:
        # Último intento: carga “silenciosa” del CWD
        load_dotenv()
except Exception:
    pass


def _get_any(keys, default: str) -> str:
    """
    Lee la primera variable NO vacía encontrada en 'keys' (lista de alias).
    Si no hay ninguna, devuelve 'default'.
    """
    if isinstance(keys, (list, tuple)):
        for k in keys:
            v = os.getenv(k)
            if v is not None and str(v).strip() != "":
                return v
        return default
    return os.getenv(keys, default)

APP_ENV: str = _get_any(["APP_ENV", "ENVIRONMENT"], "production").strip().lower()

def getenv(key: str, default: str = "") -> str:
    return _get_any([key], default)


def getint(key: str, default: int) -> int:
    return int(getenv(key, str(default)))


def getbool(key: str, default: bool = False) -> bool:
    val = getenv(key, str(default))
    return str(val).strip().lower() in {"1", "true", "yes", "on"}
# ================== BASE ==================
CDP_ENDPOINT: str = _get_any(["CDP_ENDPOINT"], "http://127.0.0.1:9222")

BASE: str = _get_any(["BASE"], "https://web.whatsapp.com/").strip().rstrip("/")
