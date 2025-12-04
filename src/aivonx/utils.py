import os
from dotenv import load_dotenv
load_dotenv()

def _split_env_list(name: str, default: str = ""):
    """Return a list of non-empty, stripped values from a comma-separated env var.

    If the env var is empty or not set, return an empty list (avoids [''] entries).
    """
    val = os.getenv(name, default).strip()
    if not val:
        return []
    return [v.strip() for v in val.split(",") if v.strip()]


def _ensure_http_scheme(origins):
    """Ensure each origin starts with a scheme (http:// or https://).

    If a value has no scheme, prepend http://. This helps avoid the
    Django 4.0+ requirement that CSRF_TRUSTED_ORIGINS entries include a scheme.
    """
    fixed = []
    for o in origins:
        if o and not o.startswith(("http://", "https://")):
            fixed.append("http://" + o)
        else:
            fixed.append(o)
    return fixed