import requests


def hello_world() -> str:
    """Fetch hello from external API.

    Returns:
        A message with the HTTP status code.
    """
    resp = requests.get("https://httpbin.org/get")
    return f"Hello from bakelib! Status: {resp.status_code}"
