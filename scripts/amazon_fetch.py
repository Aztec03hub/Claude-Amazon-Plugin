#!/usr/bin/env python3
"""Fetch Amazon.com listings and search pages from the local machine, as JSON.

Why this exists: Claude Code's native WebFetch does not work on amazon.com. It
returns HTTP 500 on product pages and 503 on search URLs, consistently, and not
as a transient outage. curl from the local machine with browser headers returns
HTTP 200 and the full page.

The important property is that this runs on the *user's own machine*, so Amazon
geolocates the request to the user's own area and renders a delivery promise for
it. A cloud fetcher or a VPN egress in another city renders an equally confident
promise for wherever that host resolves to, with nothing on the page to say so.
That is why `ship_to` is reported on every listing result and why --expect-zip
exists: the delivery date is only worth reading once you know which ZIP it is for.

What this still cannot answer:
  * The Prime arrival date. Anonymous pages carry the non-Prime, free-shipping
    promise; the Prime date is faster and renders only as an intermittent
    upsell line. Treat `delivery` as the worst case.
  * Coupons, Prime-exclusive pricing, "purchased before" badges. These render
    only in a signed-in session.
Drive a real browser for those.

Usage:
    amazon_fetch.py listing B0CHHB4RHV [ASIN ...] [--expect-zip 02139]
    amazon_fetch.py search "usb c power bank" [--rh p_85:2470955011]
    amazon_fetch.py probe          # is the local route working at all?
"""

import argparse
import html
import json
import re
import subprocess
import sys

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")

# A real product page runs 400-500 KB. Anything much under that is a wall.
MIN_REAL_PAGE = 20000

SPEC_FIELDS = re.compile(
    r"^(Item Weight|Product Dimensions|Item Dimensions|Load Capacity|"
    r"Material|Brand|Manufacturer|Colour|Color|Size|Style|Capacity)", re.I)


def fetch(url):
    r = subprocess.run(
        ["curl", "-s", "--compressed", "--max-time", "45", "-A", UA,
         "-H", "Accept-Language: en-US,en;q=0.9",
         "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         url],
        capture_output=True, text=True, errors="replace")
    return r.stdout


def text(s):
    return html.unescape(re.sub("<[^>]+>", "", s)).strip()


def first(s, pattern):
    m = re.search(pattern, s, re.S)
    return text(m.group(1)) if m else None


def blocked(s):
    """Amazon's bot wall answers with HTTP 200 and a captcha body.

    The status code therefore proves nothing and must not be used as the
    success test. Check the body.
    """
    low = s.lower()
    return "captcha" in low or "not a robot" in low or len(s) < MIN_REAL_PAGE


def ship_to(s):
    """Which ZIP the page's delivery promise is actually for.

    Do NOT recover this by regexing for a bare 5-digit number. Amazon's static
    asset filenames collide with real ZIPs -- `01890+Vwk8L.css` reads as
    Winchester MA on every single product page. Match the labelled fields only.
    """
    for hit in (first(s, r'id="contextualIngressPtLink"[^>]*aria-label="Delivering to ([^"]+?) - Update location"'),
                first(s, r'id="glow-ingress-line2"[^>]*>(.*?)</span>'),
                first(s, r'"zipcode"\s*:\s*"(\d{5})"')):
        # A bare "Update location" is the unresolved placeholder, not a place.
        # Search pages frequently render only that, which is why ship_to is
        # reliable on listing pages and not on search pages.
        if hit and re.search(r"\d", hit):
            return hit
    return None


def listing(asin, expect_zip=None):
    s = fetch(f"https://www.amazon.com/dp/{asin}")
    if blocked(s):
        return {"asin": asin, "error": "blocked or empty response",
                "bytes": len(s),
                "hint": "escalate to a real browser; retrying these headers "
                        "reproduces the same wall"}

    where = ship_to(s)
    out = {
        "asin": asin,
        "title": first(s, r'id="productTitle"[^>]*>(.*?)</span>'),
        # Every price carries an a-offscreen span; the first is the buy box.
        # Grid and "similar items" prices come later in the document.
        "price": first(s, r'class="a-offscreen">(\$[\d,.]+)</span>'),
        "availability": first(s, r'id="availability".*?<span[^>]*>(.*?)</span>'),
        "rating": first(s, r'id="acrPopover"[^>]*title="([^"]+)"'),
        "reviews": first(s, r'id="acrCustomerReviewText"[^>]*>(.*?)</span>'),
        "seller": first(s, r'id="sellerProfileTriggerId"[^>]*>(.*?)</a>')
                  or first(s, r'"merchantName"\s*:\s*"([^"]+)"'),
        "ship_to": where,
        "delivery": first(s, r'id="deliveryBlockMessage"[^>]*>(.*?)</div>'),
        "delivery_prime": first(s, r'(Prime members get FREE delivery[^<]{0,60})'),
        "bullets": [text(b) for b in re.findall(
            r'id="feature-bullets".*?</ul>', s, re.S)[:1]
            for b in re.findall(r'<span class="a-list-item[^"]*">(.*?)</span>', b, re.S)],
        "specs": {text(k).rstrip(":"): text(v) for k, v in re.findall(
            r"<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", s, re.S)
            if SPEC_FIELDS.match(text(k))},
        "url": f"https://www.amazon.com/dp/{asin}",
    }

    if expect_zip:
        if not where:
            out["ship_to_warning"] = (
                f"no ship-to rendered; cannot confirm the delivery date is for "
                f"{expect_zip}. Do not quote it.")
        elif expect_zip not in where:
            out["ship_to_warning"] = (
                f"page resolved to {where!r}, not {expect_zip}. The delivery "
                f"date is for the wrong place. Do not quote it.")
    return out


def search(query, rh=None):
    url = "https://www.amazon.com/s?k=" + re.sub(r"\s+", "+", query.strip())
    if rh:
        url += "&rh=" + rh.replace(":", "%3A").replace(",", "%2C")
    s = fetch(url)
    if blocked(s):
        return {"query": query, "url": url, "error": "blocked or empty response",
                "bytes": len(s)}

    results = []
    # Each result is a div carrying data-asin; the title and first price inside
    # that block belong together. Splitting on the attribute keeps the pairing
    # structural rather than positional, which a flattened markdown dump loses.
    for block in re.split(r'(?=<div[^>]+data-asin=")', s):
        m = re.match(r'<div[^>]+data-asin="([A-Z0-9]{10})"', block)
        if not m:
            continue
        title = first(block, r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>')
        if not title:
            continue
        results.append({
            "asin": m.group(1),
            "title": title,
            "price": first(block, r'class="a-offscreen">(\$[\d,.]+)</span>'),
            "rating": first(block, r'<span[^>]*class="a-icon-alt">([\d.]+ out of 5 stars)'),
            "reviews": first(block, r'aria-label="([\d,]+) ratings?"'),
            "sponsored": "Sponsored" in block,
        })

    seen, deduped = set(), []
    for r in results:
        if r["asin"] not in seen:
            seen.add(r["asin"])
            deduped.append(r)

    return {"query": query, "url": url, "ship_to": ship_to(s),
            "count": len(deduped), "results": deduped,
            "note": "grid prices are indicative; open the listing before "
                    "recommending anything"}


def probe():
    """Is the local route working, and where does Amazon think we are?"""
    s = fetch("https://www.amazon.com/dp/B0CHHB4RHV")
    return {
        "route": "local curl",
        "bytes": len(s),
        "blocked": blocked(s),
        "ship_to": ship_to(s),
        "verdict": ("blocked - escalate to a real browser" if blocked(s)
                    else "working"),
    }


def main():
    p = argparse.ArgumentParser(add_help=True, description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["listing", "search", "probe"])
    p.add_argument("args", nargs="*")
    p.add_argument("--expect-zip", help="warn if the page resolves elsewhere")
    p.add_argument("--rh", help="Amazon filter nodes, e.g. p_85:2470955011")
    a = p.parse_args()

    if a.mode == "listing":
        if not a.args:
            sys.exit("listing needs at least one ASIN")
        out = [listing(x, a.expect_zip) for x in a.args]
    elif a.mode == "search":
        if not a.args:
            sys.exit("search needs a query")
        out = search(" ".join(a.args), a.rh)
    else:
        out = probe()

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
