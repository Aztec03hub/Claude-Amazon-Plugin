#!/usr/bin/env python3
"""Read the user's delivery addresses and per-marketplace preferences, as JSON.

This plugin ships no address, no account and no ZIP. Everything personal lives
in a user directory outside any repo, and this script is the only thing that
knows where that is.

Why it searches rather than picking a path: the `procurement-tools` plugin
already owns `addresses.yaml` and `marketplaces.yaml`, and that config is
marketplace-agnostic by design - it describes places things get delivered to and
shops they get bought from, which is not Amazon-specific knowledge. Defaulting
to a fresh directory of our own would create a second store holding the same
facts, and the two would drift. So: adopt the first store that exists, never
migrate one silently, and write only where we read.

Search order for the store, first hit wins:
    $AMAZON_PLUGIN_CONFIG                       explicit override, any path
    <user-data-root>/marketplaces/              shared, the preferred home
    <user-data-root>/procurement-tools/         what exists today

and for <user-data-root>, again first hit wins:
    $CLAUDE_USER_DATA
    ~/.claude-user-data                         if it already exists
    ${XDG_DATA_HOME:-~/.local/share}/claude-plugins
    ~/.claude-user-data                         as the create-me default

Usage:
    user_config.py path                 where the store is, and what is in it
    user_config.py show                 addresses and marketplaces, redacted
    user_config.py resolve [address]    which marketplace/postcode/egress to use
    user_config.py show --raw           full values, including street lines
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(json.dumps({"error": "PyYAML not installed", "fix": "uv pip install pyyaml"}))

STORE_DIRS = ["marketplaces", "procurement-tools"]
MARKETPLACES_JSON = Path(__file__).resolve().parent.parent / "profiles" / "amazon-marketplaces.json"


def user_data_root():
    if os.environ.get("CLAUDE_USER_DATA"):
        return Path(os.environ["CLAUDE_USER_DATA"]).expanduser()
    candidates = [
        Path.home() / ".claude-user-data",
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "claude-plugins",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def store_dir():
    """The directory holding addresses.yaml. May not exist yet."""
    if os.environ.get("AMAZON_PLUGIN_CONFIG"):
        return Path(os.environ["AMAZON_PLUGIN_CONFIG"]).expanduser(), "AMAZON_PLUGIN_CONFIG"
    root = user_data_root()
    for name in STORE_DIRS:
        if (root / name / "addresses.yaml").is_file():
            return root / name, f"adopted existing {name}/"
    return root / STORE_DIRS[0], "default (does not exist yet)"


def load():
    d, how = store_dir()
    out = {"store": str(d), "resolved_by": how, "addresses": [], "marketplaces": [],
           "default_address": None, "missing": []}
    for fname, key in (("addresses.yaml", "addresses"), ("marketplaces.yaml", "marketplaces")):
        p = d / fname
        if not p.is_file():
            out["missing"].append(fname)
            continue
        data = yaml.safe_load(p.read_text()) or {}
        out[key] = data.get(key, [])
        if key == "marketplaces":
            out["default_address"] = data.get("default_address")
    return out


def amazon_marketplaces():
    return json.loads(MARKETPLACES_JSON.read_text())


def redact(cfg):
    """Enough to reason with, not enough to paste into a transcript."""
    for a in cfg["addresses"]:
        if "lines" in a:
            a["lines"] = f"<{len(a['lines'])} lines withheld - pass --raw>"
        for k in ("contacts", "coords", "dropoff"):
            a.pop(k, None)
    return cfg


def postcode_for(addr, country):
    """Never guess this by grabbing the last number on a line.

    An earlier version took the trailing token of the last address line, which
    on "Yaffo 105" returns the house number 105 and looks exactly like a real
    postcode in the output. A wrong postcode does not fail - it silently
    renders a delivery promise for somewhere else, which is the failure this
    whole plugin exists to prevent. So: an explicit field, or a shape that
    matches the country, or nothing.
    """
    for key in ("postcode", "zip", "zipcode"):
        if addr.get(key):
            return str(addr[key]), key
    patterns = {
        "US": r"\b\d{5}(?:-\d{4})?\b",
        "CA": r"\b[A-Z]\d[A-Z] ?\d[A-Z]\d\b",
        "GB": r"\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b",
        "DE": r"\b\d{5}\b",
        "IL": r"\b\d{7}\b",
    }
    pat = patterns.get(country)
    if pat:
        import re
        for line in addr.get("lines", []):
            m = re.search(pat, str(line), re.I)
            if m:
                return m.group(0), "matched against the country's postcode shape"
    return None, ("no postcode stored and none matched the country's shape - "
                  "add a `postcode:` key to this address rather than letting a "
                  "skill infer one")


def resolve(address_id=None):
    """Which Amazon marketplace serves this address, in which currency, via which egress."""
    cfg = load()
    mk = amazon_marketplaces()
    want = address_id or cfg["default_address"]

    if not cfg["addresses"]:
        return {"error": "no addresses configured", "store": cfg["store"],
                "missing": cfg["missing"],
                "fix": "run /procurement-tools:shop-setup to interview, or "
                       "amazon-account-import to pull them from a signed-in session"}

    addr = next((a for a in cfg["addresses"] if a.get("id") == want), None)
    if addr is None:
        return {"error": f"no address with id {want!r}", "store": cfg["store"],
                "known": [a.get("id") for a in cfg["addresses"]]}

    country = addr.get("country")
    local = next((mid for mid, m in mk["marketplaces"].items() if m["country"] == country), None)
    export = mk["no_local_marketplace"].get(country)

    if local:
        mid, notes = local, []
    elif export:
        mid, notes = export["served_by"], list(export["notes"])
    else:
        return {"error": f"no Amazon marketplace known for country {country!r}",
                "address": want,
                "hint": "add it to profiles/amazon-marketplaces.json, under "
                        "marketplaces if it has its own storefront or "
                        "no_local_marketplace if it is served as an export destination"}

    m = mk["marketplaces"][mid]
    postcode, postcode_source = postcode_for(addr, country)
    prefs = next((x for x in cfg["marketplaces"] if x.get("id") == mid), None)

    out = {
        "address": want,
        "country": country,
        "marketplace": mid,
        "domain": m["domain"],
        "listing_currency": m["currency"],
        "postcode_label": m["postcode_label"],
        "postcode": postcode,
        "postcode_source": postcode_source,
        "egress": {
            "for_marketplace_currency": m["country"],
            "for_destination_view": country,
            "note": ("Fetching the same ASIN from different countries returns different "
                     "currencies and different delivery promises, both HTTP 200. Egress "
                     "from the marketplace's own country to read the listing as the "
                     "marketplace prices it; egress from the destination to see what a "
                     "buyer there is shown. Say which one the answer came from."),
        },
        "facet_profile": m["facet_profile"],
        "notes": notes,
        "preferences": prefs or None,
    }
    if not local:
        out["landed_cost_warning"] = (
            f"{country} has no Amazon storefront. Buying from {m['domain']} is an "
            f"export order: the listed price is not the landed price.")
    if m["facet_profile"] is None:
        out["facet_warning"] = (
            f"No verified search grammar for {mid}. The amazon-us facet IDs are "
            f"marketplace-local and will not work here. Derive them per "
            f"profiles/README.md before filtering, or search unfiltered and say so.")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["path", "show", "resolve"])
    p.add_argument("args", nargs="*")
    p.add_argument("--raw", action="store_true", help="include street lines and contacts")
    a = p.parse_args()

    if a.mode == "path":
        d, how = store_dir()
        out = {"store": str(d), "resolved_by": how, "exists": d.is_dir(),
               "user_data_root": str(user_data_root()),
               "files": sorted(x.name for x in d.glob("*.yaml")) if d.is_dir() else []}
    elif a.mode == "show":
        out = load()
        if not a.raw:
            out = redact(out)
    else:
        out = resolve(a.args[0] if a.args else None)

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
