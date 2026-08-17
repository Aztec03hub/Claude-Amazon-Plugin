---
name: amazon-open-asin
description: Open one or more Amazon.com ASINs in the user's own browser, as clean canonical /dp/ URLs with the tracking stripped. Use when the user says open, show me, pull up, or let me look at an Amazon product, or wants to finish a purchase decision by eye after a shortlist. This hands the page over and reads nothing — for facts about the product use amazon-listing-check instead.
allowed-tools: Bash(xdg-open *), Bash(google-chrome *), mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, Read
---

# Amazon open ASIN

Put a product page in front of the user. No fetch, no parse, no verification —
this skill ends when the tab is open.

## The URL

```
https://www.amazon.com/dp/<ASIN>
```

That is the whole canonical form. Everything else in an Amazon URL — `ref=`,
`crid`, `sprefix`, `qid`, `sr`, `tag`, the hyphenated product-name slug — is
tracking or session state and gets dropped. Build the URL from the ASIN rather
than passing through the one you were given.

Two parameters are worth keeping **if the user supplied them**: `th=1` and
`psc=1`, which pin a specific variant. On a child ASIN of a multi-variant
listing, dropping them can land on the parent's default colour or size.

## Getting the ASIN out of the argument

Take the ten-character token after any of these:

| Form | Example |
| --- | --- |
| `/dp/<ASIN>` | `amazon.com/dp/B0CHHB4RHV` |
| `/gp/product/<ASIN>` | `amazon.com/gp/product/B0CHHB4RHV` |
| `/gp/aw/d/<ASIN>` | mobile share links |
| `/<slug>/dp/<ASIN>` | the long shared-from-browser form |
| `/product-reviews/<ASIN>` | a reviews link |

An ASIN is exactly ten characters, `[A-Z0-9]`. **Do not require a `B0` prefix.**
Books keep their ISBN-10 as the ASIN, so `0140449132` and trailing-`X` forms are
valid. If the argument is not ten characters, it is not an ASIN — it is probably
a search term, and belongs to `amazon-shortlist`.

## Opening it

Default route, one line, no dependencies:

```bash
xdg-open "https://www.amazon.com/dp/B0CHHB4RHV" >/dev/null 2>&1
```

The default browser here is Chrome, so this lands in the user's real signed-in
profile — prices, Prime badges and delivery dates on the opened page are the
user's own.

Use `tabs_create_mcp` instead when the page is going to be **worked on** and not
just looked at: it returns a tab id the delivery and search skills can address.
Call `tabs_context_mcp` first, and create a new tab rather than navigating one of
the user's existing ones.

Several ASINs get one tab each. Above about five, say how many are coming and
confirm before opening — a shortlist sweep can otherwise dump twenty tabs into a
window the user was using for something else.

## The trap in this skill

**A successful open is not evidence the ASIN exists.** `xdg-open` hands the URL
to an already-running Chrome and exits 0 immediately; it never sees the response.
A retired, mistyped or region-wrong ASIN opens Amazon's "Sorry, we couldn't find
that page" dog with exactly the same exit status as a live product.

So do not report an open as a confirmed product. Say what you opened, and if the
ASIN has not been verified this session, say that too rather than restating the
product name from memory.

The region case is the one that bites: an ASIN copied from `amazon.co.uk`,
`amazon.de` or `amazon.ca` frequently has **no `.com` listing at all**. Same
identifier, different catalogue. When the source URL was a non-`.com` Amazon
domain, open the `.com` URL if that is what was asked for, but flag that the ASIN
may not resolve there — do not silently rewrite the domain and present it as the
same product.

## Other views of the same ASIN

| Want | URL |
| --- | --- |
| Product page | `/dp/<ASIN>` |
| All reviews | `/product-reviews/<ASIN>` |
| Critical reviews only | `/product-reviews/<ASIN>?filterByStar=critical` |
| All sellers and offers | `/dp/<ASIN>?aod=1` |

The critical-reviews link is the useful one before an expensive purchase: the
average hides the failure mode, the one-star text names it.

## What this skill does not do

Never build or open a URL that changes state — no `/gp/aws/cart/add.html`, no
checkout, no one-click. Opening a page is a look; anything that mutates a cart or
an order is an action the user did not ask for. This plugin stays read-only.

Do not open a page in order to read it. A browser tab is the most expensive way
to get a price. For price, stock, rating, seller or specs use
`amazon-listing-check`; for a real Prime date use `amazon-delivery-check`.

## Related

- `amazon-listing-check` — the facts, without a tab
- `amazon-delivery-check` — signed-in dates, coupons, Prime-exclusive prices
- `amazon-shortlist` — when the argument was a need, not an ASIN
