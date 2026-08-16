---
name: amazon-listing-check
description: Verify price, stock, rating, seller and specifications for one or more Amazon.com ASINs by reading the product page itself rather than a search result. Use when the user names a specific Amazon product or link, asks what something costs or whether it is in stock, or before recommending anything found in a search grid. Reads the listing, not the grid, because grid prices are positional and stock state is absent from search results.
allowed-tools: Bash(python3 *), Bash(*/amazon_fetch.py *), Read, WebSearch
---

# Amazon listing check

Turn an ASIN or an Amazon URL into verified facts.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing B0XXXXXXX1 B0XXXXXXX2 --expect-zip 02139
```

Pass every ASIN in one call — the script fetches them in sequence and returns
one JSON array, and a single call keeps the shortlist together.

Extract the ASIN from a URL by taking the ten-character token after `/dp/` or
`/gp/product/`. Everything else in an Amazon URL is tracking.

## What to confirm before recommending anything

1. **Price** — from the listing, never the grid. Grid prices are the price
   nearest the link in a flattened page.
2. **Stock** — `Currently unavailable` is common and **never appears in search
   results**. This alone justifies opening the listing.
3. **Rating with review count** — a low rating on a low count is the highest-value
   signal in this workflow. Quote both numbers; a bare star rating is not usable.
4. **Seller** — Amazon, the brand, or a marketplace reseller.
5. **Specs** — the script returns weight, dimensions, material and capacity from
   the detail table. Where a number decides the purchase, cross-read it against
   the bullets; see below.

Read at least one critical review on anything expensive. The average hides the
failure mode; the review text names it.

## Where the page contradicts itself

Two disagreements are common enough to check for by default:

- **Spec table vs bullets on weight.** One listing's first bullet said "At just
  4 lbs" while its own spec table said `Item Weight: 2.8 pounds`.
- **Folded vs unfolded in `Item Dimensions`.** For anything that collapses,
  sellers publish whichever state they like, with nothing to distinguish them. A
  large height in that field is often handle height, not the packed size.

When a number is load-bearing for the recommendation, quote both readings and
say which you used. See
[reference/verification-traps.md](../../reference/verification-traps.md).

## Pack sizes

Price every pack size separately — they are distinct ASINs with distinct stock,
prices and delivery dates, and pack pricing is routinely non-monotonic. Write
out the per-unit figure rather than leaving the comparison implicit.

## Reporting

State price, stock, rating with count, seller and the date checked. Distinguish
what was read off the listing from what was inferred or came from a search
snippet — mark them differently rather than presenting both in one voice.

Never invent a price, a stock state or a review score. If a route failed, say
which route and how, rather than substituting a remembered figure.

Include `ship_to` beside any delivery date, and treat a `ship_to_warning` as
making the date unquotable. Coupons and Prime-exclusive prices do not render
here at all — if the total matters, say that the listing price may not be the
checkout price and offer to check the signed-in session.

## Related

- `amazon-fetch-route` — read first if any fetch misbehaves
- `amazon-delivery-check` — Prime dates and coupons
- `amazon-shortlist` — when the user has a need rather than an ASIN
