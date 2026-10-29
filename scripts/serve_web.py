"""Serves build/site to try the web page without deploying it, and with --tunnel from other devices too.

Usage: python scripts/serve_web.py [--build] [--tunnel] [--port PORT]
--build runs scripts/build_web.py first. --tunnel needs ssh and publishes the site at a public https:// address from
localhost.run: anyone with the address can open it until the script stops (Ctrl-C). Nothing is installed or pushed.
"""

import argparse
import re
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "build" / "site"
TUNNEL_URL = re.compile(r"https://[\w.-]+\.lhr\.life")


def tunnel(port: int) -> None:
    """Prints the public address, then returns when the tunnel closes."""
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ServerAliveInterval=30",
        "-R",
        f"80:localhost:{port}",
        "nokey@localhost.run",
    ]
    with subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ) as ssh:
        try:
            announced = False
            for line in ssh.stdout or []:
                if match := TUNNEL_URL.search(line):
                    if not announced:
                        print(f"Public address: {match[0]}", flush=True)
                    announced = True
        finally:
            ssh.terminate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--build", action="store_true", help="build the site first")
    parser.add_argument("--tunnel", action="store_true", help="also publish it at a public address")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    if arguments.build:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_web.py")], check=True)
    if not (SITE / "index.html").exists():
        sys.exit(f"{SITE} isn't built: run with --build")

    # only this machine can connect directly, the tunnel connects from here too
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), partial(SimpleHTTPRequestHandler, directory=SITE))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving {SITE} at http://localhost:{arguments.port}/ (Ctrl-C to stop)", flush=True)

    try:
        if arguments.tunnel:
            tunnel(arguments.port)
            print("The tunnel closed.")
        else:
            threading.Event().wait()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
