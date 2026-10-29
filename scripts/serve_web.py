"""Serves build/site to try the web page without deploying it, and with --tunnel from other devices too.

Usage: python scripts/serve_web.py [--build] [--tunnel] [--port PORT]
--build runs scripts/build_web.py first. --tunnel needs ssh and publishes the site at a public https:// address from
localhost.run: anyone with the address can open it until the script stops (Ctrl-C). Nothing is installed or pushed.
The address changes when the tunnel stops answering, which the script checks every 20 s, and a new one is printed.
"""

import argparse
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "build" / "site"
TUNNEL_URL = re.compile(r"https://[\w.-]+\.lhr\.life")
PROBE_AGENT = "serve_web-probe"
ADDRESS_TIMEOUT = 30  # seconds to wait for ssh to report the address
CHECK_SECONDS = 20  # between fetching the page at the public address
FAILURES_BEFORE_RECONNECT = 2
RETRY_SECONDS = 5


def reachable(address: str) -> bool:
    """Whether the page can be fetched at the public address. A tunnel can stay open while it answers 502."""
    request = urllib.request.Request(address, headers={"User-Agent": PROBE_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except OSError:  # includes the HTTP errors, and timeouts
        return False


def announce(ssh: subprocess.Popen[str], addresses: queue.Queue[str]) -> None:
    """Passes on the public address ssh reports, and keeps reading so that ssh never blocks on a full pipe."""
    for line in ssh.stdout or []:
        if match := TUNNEL_URL.search(line):
            addresses.put(match[0])


def open_tunnel(port: int) -> None:
    """Prints the public address and returns when the tunnel closes, or has stopped answering."""
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
            addresses: queue.Queue[str] = queue.Queue()
            threading.Thread(target=announce, args=(ssh, addresses), daemon=True).start()
            try:
                address = addresses.get(timeout=ADDRESS_TIMEOUT)
            except queue.Empty:
                print("No public address was given.", flush=True)
                return

            print(f"Public address: {address}", flush=True)
            failures = 0
            while ssh.poll() is None and failures < FAILURES_BEFORE_RECONNECT:
                time.sleep(CHECK_SECONDS)
                failures = 0 if reachable(address) else failures + 1
        finally:
            ssh.terminate()


def tunnel(port: int) -> None:
    """Keeps the page public, opening a new tunnel, with a new address, whenever the last one stops working."""
    while True:
        open_tunnel(port)
        print(f"The tunnel stopped working. Reconnecting in {RETRY_SECONDS} s…", flush=True)
        time.sleep(RETRY_SECONDS)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        # the checks of the tunnel would fill the log
        if self.headers.get("User-Agent") != PROBE_AGENT:
            super().log_message(format, *args)


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
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), partial(Handler, directory=SITE))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving {SITE} at http://localhost:{arguments.port}/ (Ctrl-C to stop)", flush=True)

    # stopping it with kill closes the tunnel too, like Ctrl-C
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    try:
        if arguments.tunnel:
            tunnel(arguments.port)
        else:
            threading.Event().wait()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
