---
description: Verify price, stock, rating, seller and specs for one or more Amazon ASINs or URLs, reading the listing rather than the search grid
argument-hint: <ASIN or amazon.com URL> [more ASINs...] [--zip 02139]
---

Verify these Amazon products: $ARGUMENTS

Use the `amazon-listing-check` skill.

1. Pull the ten-character ASIN out of each argument — the token after `/dp/` or
   `/gp/product/` in a URL. Everything else in an Amazon URL is tracking.
2. Run `scripts/amazon_fetch.py listing` with **every ASIN in one call**. Pass
   `--zip` with the user's postcode. Without it Amazon renders the page for
   whatever location this process appears to be in, which is wrong everywhere
   except the user's own machine, and looks identical when it is.
3. Report price, stock, rating with review count, seller, and any spec that
   bears on the question.

Rules that matter here:

- If the script reports `blocked`, do not retry it — escalate to a real browser.
- Quote `ship_to` beside any delivery date. A `ship_to_warning` means the date
  is for somewhere else; say so instead of quoting it.
- The date returned is the **non-Prime** one. Say so, and offer
  `/amazon:amazon-delivery` if arrival timing matters.
- `Currently unavailable` never appears in search results, so if one of these
  came from a grid, this is the step that catches it.

If the spec table and the bullets disagree on a number that matters, report both
rather than picking one.
