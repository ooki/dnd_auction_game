import sys
import os
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def main():
    host = "localhost"
    port = 8000
    play_token = os.environ.get("AH_PLAY_TOKEN", "play123")

    if len(sys.argv) >= 2 and sys.argv[1]:
        play_token = sys.argv[1]
    if len(sys.argv) >= 3 and sys.argv[2]:
        host = sys.argv[2]
    if len(sys.argv) >= 4 and sys.argv[3]:
        try:
            port = int(sys.argv[3])
        except ValueError:
            print("<ERROR: port must be an integer>")
            sys.exit(1)

    url = f"http://{host}:{port}/reset/{play_token}"
    print(f"Connecting to: {url}")

    try:
        with urlopen(url, timeout=10) as resp:
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
