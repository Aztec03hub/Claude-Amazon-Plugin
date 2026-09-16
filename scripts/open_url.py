#!/usr/bin/env python3
"""Hand one or more URLs to the user's own default browser, on any platform.

`xdg-open` exists only on Linux and BSD desktops. The equivalent is `open` on
macOS and `start` on Windows, and a skill that hardcodes any one of them is
broken on the other two. `webbrowser` resolves the right handler per platform,
is in the standard library, and needs no Bash grant beyond the `python3` this
plugin already uses.

WSL is the exception that `webbrowser` does not handle. Under WSL `sys.platform`
is "linux", so `webbrowser` looks for a Linux desktop browser; with no DISPLAY
there usually isn't one, and the call either raises or returns a truthy value
having opened nothing at all. Since the user's real browser is on the Windows
side, WSL is routed through `wslview` (wslu) or `explorer.exe`, both of which
hand the URL to Windows.

The caveat that applied to `xdg-open` applies to every route here unchanged:
handing a URL to an already-running browser returns as soon as the browser
accepts it, long before any response comes back. A successful open is not
evidence that the page exists, and a retired or wrong-storefront ASIN opens
Amazon's not-found page with exactly the same result as a live product.

Usage:
    open_url.py <url> [<url> ...]
"""

import json
import os
import shutil
import subprocess
import sys
import webbrowser


def in_wsl():
    """True when running inside Windows Subsystem for Linux."""
    if sys.platform != "linux":
        return False
    if "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ:
        return True
    try:
        with open("/proc/version", "r") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return False


def open_via_windows(url):
    """Open a URL on the Windows host from inside WSL.

    wslview (from the wslu package) is the correct tool and respects the
    Windows default browser. explorer.exe is the fallback that is always
    present. explorer.exe returns a non-zero exit code even on success, so its
    return value is deliberately ignored.
    """
    tool = shutil.which("wslview")
    if tool:
        return subprocess.run([tool, url]).returncode == 0, "wslview"
    tool = shutil.which("explorer.exe") or "/mnt/c/Windows/explorer.exe"
    if os.path.exists(tool) or shutil.which(tool):
        subprocess.run([tool, url], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return True, "explorer.exe"
    return False, "no WSL->Windows opener found (install wslu for wslview)"


def main():
    urls = sys.argv[1:]
    if not urls:
        sys.exit(json.dumps(
            {"error": "no URL given", "usage": "open_url.py <url> [<url> ...]"}))

    wsl = in_wsl()
    results = []
    for url in urls:
        # Only ever hand a browser an http(s) URL. Anything else reaching a
        # platform opener is a local path or a scheme handler, which is not
        # what any caller here means.
        if not url.startswith(("http://", "https://")):
            results.append(
                {"url": url, "opened": False, "error": "not an http(s) URL"})
            continue
        try:
            if wsl:
                ok, via = open_via_windows(url)
                results.append({"url": url, "opened": ok, "via": via}
                               if ok else
                               {"url": url, "opened": False, "error": via})
            else:
                results.append({"url": url,
                                "opened": bool(webbrowser.open(url, new=2)),
                                "via": "webbrowser"})
        except (webbrowser.Error, OSError) as exc:
            results.append({"url": url, "opened": False, "error": str(exc)})

    print(json.dumps({
        "platform": sys.platform,
        "wsl": wsl,
        "results": results,
        "note": "A browser accepting a URL is not evidence the page exists.",
    }, indent=2))


if __name__ == "__main__":
    main()
