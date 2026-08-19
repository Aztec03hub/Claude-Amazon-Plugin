---
description: Get same-day/overnight availability, the Prime basket minimum, cut-offs, coupons and Prime-exclusive pricing for Amazon ASINs from your signed-in browser session
argument-hint: <ASIN or amazon.com URL> [more ASINs...]
---

Get the real delivery dates for: $ARGUMENTS

Use the `amazon-delivery-check` skill.

Why this needs the browser: same-day and overnight availability, the lower Prime
basket minimum ($25 against $35), the order-within cut-off, and coupons and
Prime-exclusive prices render only in a signed-in session. Also check the Prime
membership state itself, which nothing else can see.

What it does **not** need the browser for: the standard Prime arrival date. That
is the second delivery option on the anonymous page and matched the signed-in
session exactly on five Amazon-fulfilled ASINs (2026-08-19). If that is all the
user wants, `amazon-listing-check` is enough. Merchant-fulfilled items gain
nothing at all from the session.

1. `tabs_context_mcp` first, then a **new** tab — do not reuse the user's tabs.
2. Navigate once to any amazon.com page.
3. Price the whole list in a single same-origin `fetch` loop via
   `javascript_tool`. Do not navigate per ASIN.
4. Confirm the ship-to ZIP before quoting anything. It renders truncated, so
   check the ZIP specifically. If it is not the user's address, stop and say so.
5. Close the tab.

Report **each** delivery option with its cost, its date, and the condition
attached to it (basket minimum, order-within cut-off), plus the ZIP it is for. A
date without its condition is not an answer. Treat a `<date> - <date>` range as an
estimate, not a promise, and `cost: "fastest"` as an upgrade whose fee the
listing does not state.

**Do not click anything.** If a navigation lands somewhere unexpected — this has
landed on an order-cancellation page — open a fresh tab rather than interacting
with it.
