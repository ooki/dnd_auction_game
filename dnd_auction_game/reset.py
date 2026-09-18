import sys
import os
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from dnd_auction_game.net import resolve_ssl, http_scheme


def main():
    # usage: python -m dnd_auction_game.reset [PLAY_TOKEN] [HOST] [PORT] [--ssl|--no-ssl]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    use_ssl = True if "--ssl" in flags else False if "--no-ssl" in flags else None

    host = "localhost"
    port = 8000
    play_token = os.environ.get("AH_PLAY_TOKEN", "play123")

    if len(args) >= 1 and args[0]:
        play_token = args[0]
    if len(args) >= 2 and args[1]:
        host = args[1]
    if len(args) >= 3 and args[2]:
        try:
            port = int(args[2])
        except ValueError:
            print("<ERROR: port must be an integer>")
            sys.exit(1)

    scheme = http_scheme(resolve_ssl(host, use_ssl))
    url = f"{scheme}://{host}:{port}/reset/{play_token}"
    print(f"Connecting to: {scheme}://{host}:{port}/reset/<play_token>")

    try:
        with urlopen(Request(url, method="POST"), timeout=10) as resp:
            data = resp.read().decode("utf-8")
            try:
                payload = json.loads(data)
            except Exception:
                payload = {"raw": data}
            print("<reset response:", payload, ">")
    except HTTPError as e:
        print(f"<HTTP ERROR {e.code}: {e.reason}>")
        sys.exit(1)
    except URLError as e:
        print(f"<URL ERROR: {e.reason}>")
        sys.exit(1)


if __name__ == "__main__":
    main()
