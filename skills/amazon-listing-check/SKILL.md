---
name: amazon-listing-check
description: Verify price, stock, delivery options and their costs, rating, seller and specifications for one or more Amazon ASINs by reading the product page itself rather than a search result. Use when the user names a specific Amazon product or link, asks what something costs or when it arrives or whether it is in stock, or before recommending anything found in a search grid. Reads the listing, not the grid, because grid prices are positional, stock state is absent from search results, and delivery is two priced options rather than one date.
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

1. **Buyable at all** — `buyable: false` means there is no buy box on this URL.
   Whatever price the page still shows belongs to a different variant or seller;
   `no_offer_warning` says so. Report the item as unavailable, and offer to pin a
   variant (`?th=1&psc=1`) rather than quoting the number.
2. **Price** — from the listing, never the grid. Grid prices are the price
   nearest the link in a flattened page. Note the script now skips the
   struck-through List Price, which used to be what it returned on anything
   discounted.
3. **Stock** — `Currently unavailable` never appears in search results. Quote the
   whole `availability` string: `In stock. Usually ships within 4 to 5 days` is a
   different answer from `In stock`, and it is often the reason the delivery date
   is three weeks out.
4. **Delivery options, plural** — see below.
5. **Rating with review count** — a low rating on a low count is the
   highest-value signal in this workflow. Quote both numbers; a bare star rating
   is not usable.
6. **Seller and fulfiller** — `seller` reads `Sold by X` when Amazon fulfils and
   `Shipper / Seller X` when the merchant does both. The label is the fulfilment
   signal, so keep it rather than reducing to a bare name.
7. **Specs** — the script returns weight, dimensions, material and capacity from
   the detail table. Where a number decides the purchase, cross-read it against
   the bullets; see below.

Read at least one critical review on anything expensive. The average hides the
failure mode; the review text names it.

## Delivery is a list, not a date

`delivery_options` returns one entry per option, each with its own `cost`,
`when`, `condition` and `cutoff`. Usually there are two and the trade-off between
them is the answer:

```
{"slot":"primary",   "cost":"FREE", "when":"Monday, August 24",
 "condition":"on orders shipped by Amazon over $35", "sub_type":"CONDITIONALLY_FREE"}
{"slot":"secondary", "cost":"FREE", "when":"Tomorrow, August 20"}
```

Quote the cost **and** the condition with every date. "Free delivery" on a $9.99
item whose free tier needs a $25 basket is not free. Three ways to misread it:

- `cost` can be the literal string `fastest` — an upgrade whose fee the listing
  does not state. Say it is unpriced until checkout rather than implying it is
  free.
- `program: paid_shipping` does **not** mean you pay; read `cost`.
- An empty `delivery_options` means the structured block is absent on this
  listing, not that there is no delivery. Fall back to the `delivery` prose, and
  say which you used.

The full field contract, and what a signed-in session adds on top, is in
[reference/delivery.md](../../reference/delivery.md).

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
making the date unquotable.

Three things this route cannot see, so do not imply otherwise: coupons,
Prime-exclusive prices, and whether same-day or overnight is available (it is
offered signed-in at a lower basket minimum -- $25 against $35 -- on items where
this route shows only a standard date). The standard Prime date, however, **is**
here, in the second delivery option; do not escalate to a browser for it. If the
total matters, say the listing price may not be the checkout price and offer
`amazon-delivery-check`.

## Storefront and destination

Pass `-m/--marketplace` unless the user's default storefront is genuinely the
right one, and `--expect-postcode` rather than assuming a US ZIP.
`amazon-marketplace-config` resolves both from the stored delivery address in one
call; it also flags the cases where the listed price is not the landed price,
which is every destination served as an export market rather than by its own
storefront.

## Related

- [reference/delivery.md](../../reference/delivery.md) — the delivery-option contract
- `amazon-marketplace-config` — which storefront, which postcode, which egress

- `amazon-fetch-route` — read first if any fetch misbehaves
- `amazon-delivery-check` — Prime dates and coupons
- `amazon-shortlist` — when the user has a need rather than an ASIN
