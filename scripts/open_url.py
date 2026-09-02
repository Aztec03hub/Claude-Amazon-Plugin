#!/usr/bin/env python3
"""Hand one or more URLs to the user's own default browser, on any platform.

`xdg-open` exists only on Linux and BSD desktops. The equivalent is `open` on
macOS and `start` on Windows, and a skill that hardcodes any one of them is
broken on the other two. `webbrowser` resolves the right handler per platform,
is in the standard library, and needs no Bash grant beyond the `python3` this
plugin already uses.

The caveat that applied to `xdg-open` applies here unchanged: handing a URL to
an already-running browser returns as soon as the browser accepts it, long
before any response comes back. A successful open is not evidence that the page
exists, and a retired or wrong-storefront ASIN opens Amazon's not-found page
with exactly the same result as a live product.

Usage:
    open_url.py <url> [<url> ...]
"""

import json
import sys
import webbrowser


def main():
    urls = sys.argv[1:]
    if not urls:
        sys.exit(json.dumps(
            {"error": "no URL given", "usage": "open_url.py <url> [<url> ...]"}))

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
            results.append({"url": url, "opened": bool(webbrowser.open(url, new=2))})
        except webbrowser.Error as exc:
            results.append({"url": url, "opened": False, "error": str(exc)})

    print(json.dumps({
        "platform": sys.platform,
        "results": results,
        "note": "A browser accepting a URL is not evidence the page exists.",
    }, indent=2))


if __name__ == "__main__":
    main()
