---
name: amazon-fetch-route
description: Choose the right route for an Amazon.com fetch and prove it actually worked. Use before the first Amazon fetch in a session, when an Amazon page returns an error or an empty-looking result, when a delivery date needs to be trusted, or when a previous Amazon answer looked plausible but wrong. Amazon blocks the default fetch tool and every fallback fails in a way that resembles success.
allowed-tools: Bash(python3 *), Bash(*/amazon_fetch.py *), Read, WebSearch
---

# Amazon fetch route

Amazon is the case where "the fetch returned something" and "the fetch worked"
come apart. Read [reference/fetch-routes.md](../../reference/fetch-routes.md)
before the first fetch of a session.

## The short version

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" probe
```

Answers all three questions at once: is the local route working, is it being
walled, and which ZIP will delivery dates be for.

## Which storefront, before which route

Route selection assumes you already know *which Amazon* you are fetching. Amazon
runs a separate storefront per country with a separate catalogue, and this
plugin's verified knowledge — facet IDs, page sizes, the English delivery
wording — is `amazon-us` knowledge unless it says otherwise. Resolve the
storefront first with `amazon-marketplace-config`, and pass `-m/--marketplace` to
`amazon_fetch.py`. See [reference/marketplaces.md](../../reference/marketplaces.md).

The currency you get back is a property of the route, not of the listing:
amazon.com renders ILS from an Israeli IP and USD from a US one, HTTP 200 both
times. Know the egress country before quoting a price.

## Route selection

| The question is | Use |
| --- | --- |
| What products exist, what do reviewers say | `WebSearch` |
| Price, stock, rating, seller, specs for an ASIN | `amazon_fetch.py listing` |
| Shortlist candidates for a need | `amazon_fetch.py search` |
| **Prime arrival date, coupons, Prime-exclusive price** | a real signed-in browser |
| Anything after the local route is walled | a real signed-in browser |

`WebFetch` is not on this list for amazon.com. It returns HTTP 500 on `/dp/`
pages and 503 on `/s?k=` searches, reliably. Do not spend a call confirming
this; do not report it as an outage.

## Three failures that look like successes

**1. HTTP 200 with a captcha body.** The status code is not the success test.
`amazon_fetch.py` checks the body — captcha markers, or a response under 20 KB
against a real page's 400–500 KB. If it reports `blocked`, escalate to a real
browser. Do not retry: the same headers reproduce the same wall.

**2. A delivery date for the wrong place.** Amazon geolocates anonymous requests
by IP and renders a confident promise for wherever that IP lands. A cloud
fetcher or a VPN exit in another city produces a date that is well-formed,
plausible, and about somewhere else. Nothing on the page flags it.

Always read `ship_to` before quoting `delivery`. When the user's ZIP is known,
pass it and let the script do the check:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing B0XXXXXXXX --expect-zip 02139
```

A `ship_to_warning` in the output means the date is unusable. Say so rather than
quoting it with a caveat.

**3. One delivery option presented as the delivery.** A listing offers up to two
options that differ in cost as well as speed, and `#deliveryBlockMessage` returns
only the first. Read `delivery_options`, which the script now returns from
Amazon's own `data-csa-c-*` attributes: cost, date, basket minimum and cutoff as
separate fields.

Corrected 2026-08-19: this route is **not** blind to the Prime date. The Prime
date is the second option, and it matched a signed-in session exactly on five
Amazon-fulfilled ASINs. What the anonymous route genuinely cannot see is
same-day/overnight availability, the lower Prime basket minimum ($25 against
$35), the order-within cutoff, and coupons. On merchant-fulfilled items it sees
everything the session does. See
[reference/delivery.md](../../reference/delivery.md).

## Ask before assuming a ZIP

This plugin ships no address. If a delivery question matters and the user's ZIP
has not been established in this session, ask for it once rather than quoting a
date for wherever the machine happens to resolve. If they decline, report the
`ship_to` the page returned alongside the date so the answer carries its own
scope.

## Escalating

A blocked route is not a dead end, but escalating is not the same as retrying.
Two attempts on one route, then change route. When you do run out, say
specifically what you tried and how each failed, so the next attempt starts
where you stopped.

## Related

- [reference/fetch-routes.md](../../reference/fetch-routes.md) — full routing detail, batch technique
- [reference/verification-traps.md](../../reference/verification-traps.md) — fields that lie
- `amazon-delivery-check` — the signed-in browser workflow
