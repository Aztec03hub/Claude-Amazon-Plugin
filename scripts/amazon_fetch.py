#!/usr/bin/env python3
"""Fetch Amazon listings and search pages from the local machine, as JSON.

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

Delivery is reported as `delivery_options`, a list, not a single date. A
listing offers up to two, and they differ in *cost* as well as speed: the
cheapest option is frequently the slowest and the fastest one frequently
carries a basket minimum. Collapsing them to one string loses the trade-off
that decides the purchase. See reference/delivery.md.

Anonymous pages DO carry the Prime date -- in the second option, verified
identical to a signed-in session on five Amazon-fulfilled ASINs (2026-08-19).
What a signed-in session adds is the same-day/overnight upgrade, its lower
basket minimum, and the order-within cutoff.

What this still cannot answer:
  * Same-day and overnight availability, and the Prime basket minimum. On
    2026-08-19 the anonymous page offered "FREE Monday Aug 24 on orders over
    $35" where the signed-in session offered "FREE Overnight 4 AM - 8 AM on
    qualifying orders over $25" for the same ASIN.
  * Coupons, Prime-exclusive pricing, "purchased before" badges. These render
    only in a signed-in session.
  * Whether the user's Prime membership is still live on the delivery date.
    Ask amazon-account-import; a trial expiring next week invalidates every
    Prime promise quoted past it.
Drive a real browser for those.

Usage:
    amazon_fetch.py listing B0CHHB4RHV [ASIN ...] [--expect-zip 02139]
    amazon_fetch.py search "usb c power bank" [--rh p_85:2470955011]
    amazon_fetch.py probe          # is the local route working at all?

    ... and -m/--marketplace on any of them to reach a storefront other than the
    default. Storefronts are separate catalogues, so an ASIN is only meaningful
    together with the marketplace it came from, and the --rh facet IDs are
    marketplace-local: the US Prime node means nothing on amazon.de. Run
    user_config.py resolve <address> to get the marketplace for a destination.
"""

import argparse
import atexit
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")

# Set from --marketplace. Amazon runs one storefront per country and they are
# separate catalogues: an ASIN that exists on one routinely does not exist on
# another, and the facet grammar is marketplace-local. Nothing here should
# assume the US.
MARKETPLACES = json.loads(
    (Path(__file__).resolve().parent.parent / "profiles" / "amazon-marketplaces.json")
    .read_text())
DOMAIN = MARKETPLACES["marketplaces"][MARKETPLACES["default"]]["domain"]

# A real product page runs 400-500 KB. Anything much under that is a wall.
MIN_REAL_PAGE = 20000

SPEC_FIELDS = re.compile(
    r"^(Item Weight|Product Dimensions|Item Dimensions|Load Capacity|"
    r"Material|Brand|Manufacturer|Colour|Color|Size|Style|Capacity)", re.I)


# Set by --zip. When present every request carries the same cookie jar, which
# is what makes a delivery location stick across the handshake and the fetches
# that follow it.
COOKIE_JAR = None


def _curl(args):
    base = ["curl", "-s", "--compressed", "--max-time", "45", "-A", UA,
            "-H", "Accept-Language: en-US,en;q=0.9"]
    if COOKIE_JAR:
        base += ["-b", COOKIE_JAR, "-c", COOKIE_JAR]
    r = subprocess.run(base + args, capture_output=True, text=True,
                       errors="replace")
    return r.stdout


def fetch(url):
    return _curl(
        ["-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         url])


def set_delivery_zip(postcode):
    """Run Amazon's own delivery-address handshake so every later fetch renders
    for `postcode` rather than for whatever this host's IP implies.

    This is the difference between a usable result and a confidently wrong one.
    A request from a datacenter, a VPN exit or a colleague's machine reports
    that location's prices, Prime badges, stock and delivery dates, and nothing
    on the page says so - the output is still perfectly well-formed. --expect-zip
    can only detect that after the fact; this fixes it.

    Returns the address Amazon confirms. Raises rather than returning quietly:
    unlocalised data presented as localised is worse than no data.
    """
    global COOKIE_JAR
    fd, path = tempfile.mkstemp(prefix="amzn-cookies-", suffix=".txt")
    os.close(fd)
    atexit.register(lambda: os.path.exists(path) and os.unlink(path))
    COOKIE_JAR = path

    # Seed the session, then read the glow modal for a CSRF token. The token is
    # not always rendered and the endpoint currently accepts the POST without
    # one, so treat a miss as non-fatal and send it only when present.
    _curl(["-o", os.devnull, "https://%s/" % DOMAIN])
    glow = _curl(["https://%s/gp/glow/get-address-selections.html"
                  "?deviceType=desktop&pageType=Gateway"
                  "&storeContext=NoStoreName&actionSource=desktop-modal" % DOMAIN])
    token = re.search(r'CSRF_TOKEN\s*:\s*"([^"]+)"', glow)

    args = ["-X", "POST", "-H",
            "Content-Type: application/x-www-form-urlencoded;charset=UTF-8"]
    if token:
        args += ["-H", "anti-csrftoken-a2z: " + token.group(1)]
    for k, v in (("locationType", "LOCATION_INPUT"), ("zipCode", postcode),
                 ("storeContext", "generic"), ("deviceType", "web"),
                 ("pageType", "Gateway"), ("actionSource", "glow")):
        args += ["--data-urlencode", "%s=%s" % (k, v)]
    args.append("https://%s/portal-migration/hz/glow/address-change" % DOMAIN)

    body = _curl(args)
    try:
        r = json.loads(body)
    except ValueError:
        raise RuntimeError(
            "address-change did not return JSON (%d bytes) - the endpoint may "
            "have moved again" % len(body))
    if not (r.get("successful") and r.get("isAddressUpdated")):
        raise RuntimeError("Amazon rejected postcode %r on %s: %s"
                           % (postcode, DOMAIN, body[:200]))
    return r.get("address", {})


def text(s):
    return html.unescape(re.sub("<[^>]+>", "", s)).strip()


def first(s, pattern):
    m = re.search(pattern, s, re.S)
    return text(m.group(1)) if m else None


# Amazon renders each buy-box row as a <div id="<name>_feature_div">. The rows
# have no closing marker of their own, and several of them end with an inline
# <style> block, so read to the next feature div or the first tag that is not
# content. The visible value is also duplicated for the responsive layouts,
# which is why repeated words get collapsed.
SELLER_LABELS = ("Shipper / Seller", "Sold and shipped by", "Sold by", "Ships from")


def feature(s, name):
    """Text of one buy-box row, deduplicated.

    Amazon renders each row as <div id="<name>_feature_div">, or sometimes as a
    bare <div id="<name>">. The rows carry no closing marker of their own and
    several end in an inline <style> block, so read to the next feature div or
    the first tag that is not content.

    The visible value is then repeated -- once for the screen-reader copy and
    once per responsive breakpoint -- giving strings like
    "Sold by waveshare waveshare Sold by waveshare". Collapse those: the
    duplicate is an artefact of the layout, not a second seller.
    """
    # The outer <div id="<name>_feature_div"> is sometimes an empty wrapper
    # around <div id="<name>">, so take the first pattern that yields text
    # rather than the first that matches.
    v = ""
    for pat in (r'id="%s_feature_div"[^>]*>(.*?)(?=<div id="\w+_feature_div"|<style|<script)',
                r'id="%s"[^>]*>(.*?)(?=<div id="\w+_feature_div"|<style|<script)'):
        m = re.search(pat % re.escape(name), s, re.S)
        if m:
            v = re.sub(r"\s+", " ", text(m.group(1))).strip()
            if v:
                break
    if not v:
        return None

    label = next((x for x in SELLER_LABELS if v.startswith(x)), None)
    body = re.sub(r"\s+", " ", v.replace(label, " ")).strip() if label else v

    # If what is left is one value repeated, keep one copy.
    words = body.split(" ")
    for n in range(1, len(words) // 2 + 1):
        if len(words) % n == 0 and all(
                words[i:i + n] == words[:n] for i in range(0, len(words), n)):
            body = " ".join(words[:n])
            break

    return ("%s %s" % (label, body)).strip() if label else body


def blocked(s):
    """Amazon's bot wall answers with HTTP 200 and a captcha body.

    The status code therefore proves nothing and must not be used as the
    success test. Check the body.
    """
    low = s.lower()
    return "captcha" in low or "not a robot" in low or len(s) < MIN_REAL_PAGE


# `a-offscreen` is Amazon's screen-reader span and it is not price-specific -
# "4.5 out of 5 stars" uses it too. The original regex here was `\$[\d,.]+`,
# which was safe by accident: it only ever matched USD, so on amazon.co.uk or
# amazon.de it returned null, and it returned null on amazon.com too whenever
# the request egressed from Israel and the page rendered ILS. Widening it to
# any short string fixes the currency and breaks the safety, so the symbol
# check has to move here.
CURRENCY = re.compile(r"[$£€₹¥￥₺₪]|R\$|\bkr\b|\bz\u0142|\b(?:AED|SAR|EGP|USD|EUR|GBP|ILS)\b")
NOT_A_PRICE = re.compile(r"out of 5|stars?\b|%", re.I)

# The struck-through "List Price" is rendered BEFORE the price you would pay,
# in the same markup, with its own a-offscreen span. Taking the first price in
# the document therefore returns the list price on anything discounted:
# measured 2026-08-19, ASIN 0140449132 reported $16.00 against a real $12.91,
# a 24% overstatement with nothing to flag it. The list price is the one whose
# enclosing <span class="a-price ..."> is marked struck or basis.
LIST_PRICE = re.compile(r'a-text-price|data-a-strike="true"|basisprice', re.I)


def price(s):
    """First a-offscreen span that is a price you could actually pay.

    Skips the struck-through list price; see LIST_PRICE above.
    """
    for m in re.finditer(r'<span class="a-offscreen">([^<]{1,24})</span>', s):
        v = html.unescape(m.group(1)).strip()
        if not (any(c.isdigit() for c in v) and CURRENCY.search(v)):
            continue
        if NOT_A_PRICE.search(v):
            continue
        # The enclosing a-price span opens immediately before this one.
        j = s.rfind("<span", 0, m.start())
        if j != -1 and LIST_PRICE.search(s[j:m.start()]):
            continue
        return v
    return None


# Amazon publishes each delivery option as machine-readable attributes on the
# message span, alongside the English sentence. Reading the attributes instead
# of the prose gets the fee, the date, the basket minimum and the cutoff as
# separate fields, and does it identically on storefronts that render the
# sentence in another language. Verified 2026-08-19; see reference/delivery.md.
DEX_SLOT = {"DEXUnifiedCXPDM": "primary", "DEXUnifiedCXSDM": "secondary"}
DEX_SPAN = re.compile(
    r'<span[^>]*data-csa-c-content-id="(DEXUnifiedCX[PS]DM)"[^>]*>')
DEX_ATTR = re.compile(r'data-csa-c-([a-z-]+)="([^"]*)"')


def delivery_options(s):
    """Every delivery option the listing offers, cheapest-first as rendered.

    Returns [] when the listing carries no structured block -- which happens,
    so callers must fall back to the `delivery` prose rather than concluding
    there is no delivery.
    """
    out, seen = [], set()
    for m in DEX_SPAN.finditer(s):
        a = {k: html.unescape(v) for k, v in DEX_ATTR.findall(m.group(0))}
        opt = {"slot": DEX_SLOT[m.group(1)]}
        for src, dst in (("delivery-price", "cost"),
                         ("delivery-time", "when"),
                         ("delivery-condition", "condition"),
                         ("delivery-cutoff", "cutoff"),
                         ("delivery-type", "kind"),
                         ("pickup-location", "pickup_location"),
                         ("delivery-origin-country", "ships_from_country"),
                         ("delivery-destination", "destination"),
                         ("delivery-benefit-program-id", "program"),
                         ("mir-sub-type", "sub_type")):
            if a.get(src):
                opt[dst] = a[src]
        # The block is re-rendered per breakpoint, so the same option appears
        # up to four times.
        key = json.dumps(opt, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(opt)
    return out


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
    s = fetch(f"https://{DOMAIN}/dp/{asin}")
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
        "price": price(s),
        # Read the whole block, not its first span: the stock line frequently
        # carries a second sentence that changes the answer ("In stock. Usually
        # ships within 4 to 5 days"), and the block trails into a <style> tag.
        "availability": feature(s, "availability"),
        "buyable": 'id="add-to-cart-button"' in s or 'id="buy-now-button"' in s,
        "rating": first(s, r'id="acrPopover"[^>]*title="([^"]+)"'),
        "reviews": first(s, r'id="acrCustomerReviewText"[^>]*>(.*?)</span>'),
        # sellerProfileTriggerId and the merchantName JSON key are both gone
        # from the page as of 2026-08-19; these two divs are what render today.
        # Their labels differ meaningfully: "Sold by X" appears when Amazon
        # fulfils (fulfiller div populated, "Ships from Amazon"), while
        # "Shipper / Seller X" means the merchant does both.
        "seller": feature(s, "merchantInfoFeature"),
        "ships_from": feature(s, "fulfillerInfoFeature"),
        "ship_to": where,
        # Prose, first option only -- kept because delivery_options is empty on
        # some listings. Never quote this without checking delivery_options: it
        # stops at the first </div>, which is the slowest option.
        "delivery": first(s, r'id="deliveryBlockMessage"[^>]*>(.*?)</div>'),
        "delivery_options": delivery_options(s),
        "bullets": [text(b) for b in re.findall(
            r'id="feature-bullets".*?</ul>', s, re.S)[:1]
            for b in re.findall(r'<span class="a-list-item[^"]*">(.*?)</span>', b, re.S)],
        "specs": {text(k).rstrip(":"): text(v) for k, v in re.findall(
            r"<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", s, re.S)
            if SPEC_FIELDS.match(text(k))},
        "url": f"https://{DOMAIN}/dp/{asin}",
    }

    if not out["buyable"]:
        # A variant parent with no featured offer renders no buy box, no
        # delivery block and no seller -- but still carries prices belonging to
        # OTHER variants, which price() will happily return. Measured
        # 2026-08-19 on B003J9LZE4, which reported $108.99 for a size nobody
        # can buy on that URL.
        out["no_offer_warning"] = (
            "no buy box on this URL: nothing is purchasable here, and any "
            "price above belongs to a different variant or seller. Pin a "
            "variant with ?th=1&psc=1, or treat this as unavailable.")

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
    url = f"https://{DOMAIN}/s?k=" + re.sub(r"\s+", "+", query.strip())
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
            "price": price(block),
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


def probe(marketplace, asin=None):
    """Is the local route working, and where does Amazon think we are?

    Needs a real listing, because the ship-to line renders on product pages and
    usually not on search pages. The known-good ASIN is per marketplace and only
    exists for the ones that have been used: an ASIN from another storefront
    404s, and a 404 page is small enough that blocked() calls it a bot wall.
    That would report a working route as blocked, so ask instead of guessing.
    """
    m = MARKETPLACES["marketplaces"][marketplace]
    asin = asin or m["probe_asin"]
    if not asin:
        return {"marketplace": marketplace, "domain": m["domain"],
                "error": f"no known-good probe ASIN for {marketplace}",
                "fix": f"pass one: amazon_fetch.py probe <ASIN> -m {marketplace}. "
                       f"Any listing that is live on {m['domain']} will do. Add it to "
                       f"profiles/amazon-marketplaces.json as probe_asin once it works."}
    s = fetch(f"https://{m['domain']}/dp/{asin}")
    return {
        "route": "local curl",
        "marketplace": marketplace,
        "domain": m["domain"],
        "probe_asin": asin,
        "bytes": len(s),
        "blocked": blocked(s),
        "ship_to": ship_to(s),
        "price_seen": price(s),
        "verdict": ("blocked - escalate to a real browser" if blocked(s)
                    else "working"),
        "note": ("A small page can be a 404 rather than a wall - if this ASIN is not "
                 "live on this marketplace the verdict is wrong. Check bytes."),
    }


def main():
    p = argparse.ArgumentParser(add_help=True, description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["listing", "search", "probe"])
    p.add_argument("args", nargs="*")
    p.add_argument("--expect-zip", "--expect-postcode", dest="expect_zip",
                   help="warn if the page resolves elsewhere; ZIP in the US, "
                        "postcode elsewhere")
    p.add_argument("-m", "--marketplace", default=MARKETPLACES["default"],
                   choices=sorted(MARKETPLACES["marketplaces"]),
                   help="which Amazon storefront (default: %(default)s)")
    p.add_argument("--rh", help="Amazon filter nodes, e.g. p_85:2470955011")
    p.add_argument("--zip", "--postcode", dest="zip",
                   help="render every page for this delivery postcode instead "
                        "of whatever this host's IP implies. Required whenever "
                        "the script runs somewhere other than where the user "
                        "actually is: a datacenter, a VPN, a remote sandbox. "
                        "Implies --expect-zip unless that is set explicitly.")
    a = p.parse_args()

    global DOMAIN
    DOMAIN = MARKETPLACES["marketplaces"][a.marketplace]["domain"]

    applied = None
    if a.zip:
        try:
            applied = set_delivery_zip(a.zip)
        except RuntimeError as exc:
            sys.exit(json.dumps({
                "error": str(exc),
                "requested_zip": a.zip,
                "note": "Refusing to continue. Results would silently be for "
                        "this host's location rather than the one requested.",
            }, indent=2))
        # Asking for a location and verifying it landed are the same intent.
        if not a.expect_zip:
            a.expect_zip = a.zip

    if a.mode == "listing":
        if not a.args:
            sys.exit("listing needs at least one ASIN")
        out = [listing(x, a.expect_zip) for x in a.args]
    elif a.mode == "search":
        if not a.args:
            sys.exit("search needs a query")
        out = search(" ".join(a.args), a.rh)
    else:
        out = probe(a.marketplace, a.args[0] if a.args else None)

    if applied is not None:
        out = {
            "delivery_location": {
                "requested": a.zip,
                "zip": applied.get("zipCode"),
                "city": applied.get("city"),
                "state": applied.get("state"),
                "country": applied.get("countryCode"),
                "applied": True,
            },
            "results": out,
        }

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
