---
description: Get real Prime delivery dates, coupons and Prime-exclusive pricing for Amazon ASINs from your signed-in browser session
argument-hint: <ASIN or amazon.com URL> [more ASINs...]
---

Get the real delivery dates for: $ARGUMENTS

Use the `amazon-delivery-check` skill.

Why this needs the browser: the anonymous route returns the non-Prime,
free-shipping-over-$35 promise. On one measured shortlist that was four days
later than the Prime date the signed-in session showed for the same ASINs.
Coupons and Prime-exclusive prices do not render anonymously at all.

1. `tabs_context_mcp` first, then a **new** tab — do not reuse the user's tabs.
2. Navigate once to any amazon.com page.
3. Price the whole list in a single same-origin `fetch` loop via
   `javascript_tool`. Do not navigate per ASIN.
4. Confirm the ship-to ZIP before quoting anything. It renders truncated, so
   check the ZIP specifically. If it is not the user's address, stop and say so.
5. Close the tab.

Report the date, the condition attached to it (basket minimum, order-within
cut-off), and the ZIP it is for. A date without its condition is not an answer.
Treat a `<date> - <date>` range as an estimate, not a promise.

**Do not click anything.** If a navigation lands somewhere unexpected — this has
landed on an order-cancellation page — open a fresh tab rather than interacting
with it.
