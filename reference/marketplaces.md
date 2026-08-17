# Amazon storefronts, and what is scoped to which

Verified 2026-08-17.

Amazon is roughly twenty separate storefronts, one per country. They share a
login and a URL shape and almost nothing else. Two consequences run through this
whole plugin:

**An ASIN is only meaningful together with its storefront.** The same
ten-character identifier can be a live listing on `amazon.co.uk`, a different
product on `amazon.com`, and nothing at all on `amazon.de`. There is no global
catalogue to fall back on. Carry the marketplace id alongside every ASIN;
rewriting the domain to the user's home storefront is not a translation, it is a
guess that returns HTTP 200 either way.

**Everything volatile is per storefront.** Facet IDs, sort keys, the currency,
the postcode format, which delivery filters exist, whether Prime exists at all.
None of it transfers.

## What is verified where

| Layer | File | Scope |
| --- | --- | --- |
| Domain, currency, symbol, postcode label, locale | `profiles/amazon-marketplaces.json` | all storefronts |
| Facet grammar, sort keys, selectors, trust rubric | `profiles/amazon-us.json` | **amazon-us only** |
| Delivery addresses, per-marketplace account state | user config, outside the repo | per user |

Only `amazon-us` has a verified facet profile, derived against a real signed-in
browser. Every other storefront has `"facet_profile": null`, and that is a
statement of fact, not an oversight to be papered over. Using the US facet IDs
against another domain does not error — `p_85:2470955011` simply filters to
something else, or to nothing, and the result looks like a clean answer.

To add one, follow the five-step derivation recipe in
[`profiles/README.md`](../profiles/README.md), against a signed-in session on
that domain, and record `verified` and `verified_how` with the date. Note that
Amazon's facet rail is session-dependent: an anonymous fetch hides the Prime
facet entirely and substitutes a different one, so an anonymously-derived profile
is wrong in a way that looks complete.

## Statements in this plugin that are about amazon-us specifically

Read these as scoped, not general:

- `WebFetch` returning 500 on `/dp/` and 503 on `/s?k=` was measured against
  amazon.com. The block is near-certainly Amazon-wide, but only amazon.com was
  tested.
- The 400–500 KB real-page size and the 20 KB wall threshold come from
  amazon.com product pages.
- Every `p_*` facet token quoted anywhere in this repo is a US node id.
- The `"zipcode": "\d{5}"` fallback in `ship_to()` is a US shape. The two
  labelled selectors it tries first are not.
- Delivery date wording — "FREE delivery", "Order within N hrs" — is the
  English-language rendering. Non-English storefronts render the same facts in
  the local language and the string tables have not been derived.

## Countries with no storefront of their own

Some destinations are served as export markets by another storefront. Israel is
served by `amazon.com`: there is no `amazon.co.il`.

For these the listed price is not the landed price — an Import Fees Deposit and
international shipping go on top — and a home-country Prime membership does not
apply to the order. `profiles/amazon-marketplaces.json` records them under
`no_local_marketplace`, and `user_config.py resolve` returns a
`landed_cost_warning` for any address in one.

## The currency-follows-the-route trap

`amazon.com` renders prices in ILS when the request egresses from an Israeli IP
and in USD from a US one. Same URL, same ASIN, HTTP 200 both times, nothing on
the page announcing which you got.

So the currency in an answer is a property of the **route**, not of the listing,
and any price quoted without knowing the egress country is unquotable. This is
also why the price extractor cannot be `\$[\d,.]+`: a USD-only regex returns
null on every non-US storefront, and null on amazon.com itself from Israel.
`amazon_fetch.py` matches any currency and validates the result instead — see
`price()` and the `CURRENCY` pattern.
