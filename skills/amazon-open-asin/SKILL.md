---
name: amazon-open-asin
description: Open one or more Amazon ASINs in the user's own browser, on the right regional storefront, as clean canonical /dp/ URLs with the tracking stripped. Use when the user says open, show me, pull up, or let me look at an Amazon product, or wants to finish a purchase decision by eye after a shortlist. This hands the page over and reads nothing — for facts about the product use amazon-listing-check instead.
allowed-tools: Bash(python3 *), Bash(*/user_config.py *), Bash(*/open_url.py *), mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, Read
---

# Amazon open ASIN

Put a product page in front of the user. No fetch, no parse, no verification —
this skill ends when the tab is open.

## Which storefront

Not automatically amazon.com. Amazon runs a separate storefront per country and
they are separate catalogues; opening the wrong one is the most likely way this
skill wastes the user's time.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/user_config.py" resolve
```

That returns the `domain` for the user's default delivery address; pass an
address id to open against a different destination. Take the domain from
whichever source is most specific:

1. The user said which one — "on the UK site".
2. The ASIN came with a URL this session — use **that** URL's domain. An ASIN is
   only meaningful together with the storefront it was found on.
3. The resolver's answer for the relevant address.
4. Only if none of the above and the config is empty: amazon.com, and say that
   you assumed it.

## The URL

```
https://<domain>/dp/<ASIN>
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
| `/gp/product/<ASIN>` | `amazon.co.uk/gp/product/B0CHHB4RHV` |
| `/gp/aw/d/<ASIN>` | mobile share links |
| `/<slug>/dp/<ASIN>` | the long shared-from-browser form |
| `/product-reviews/<ASIN>` | a reviews link |

An ASIN is exactly ten characters, `[A-Z0-9]`. **Do not require a `B0` prefix.**
Books keep their ISBN-10 as the ASIN, so `0140449132` and trailing-`X` forms are
valid. If the argument is not ten characters, it is not an ASIN — it is probably
a search term, and belongs to `amazon-shortlist`.

## Opening it

Default route, one line, no dependencies beyond the Python this plugin already
needs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/open_url.py" "https://www.amazon.com/dp/B0CHHB4RHV"
```

Do **not** call `xdg-open` directly. It exists only on Linux and BSD desktops —
the equivalent is `open` on macOS and `start` on Windows — so hardcoding it
breaks this skill outright on the other two platforms. `open_url.py` wraps
`webbrowser` from the standard library, which resolves the right handler per
platform, and takes several URLs in one call.

This lands in the user's default browser, and so in their real signed-in
profile — prices, Prime badges and delivery dates on the opened page are the
user's own, for whichever storefront that account is signed in to.

Use `tabs_create_mcp` instead when the page is going to be **worked on** and not
just looked at: it returns a tab id the delivery and search skills can address.
Call `tabs_context_mcp` first, and create a new tab rather than navigating one of
the user's existing ones.

Several ASINs get one tab each. Above about five, say how many are coming and
confirm before opening — a shortlist sweep can otherwise dump twenty tabs into a
window the user was using for something else.

## The trap in this skill

**A successful open is not evidence the ASIN exists.** The platform opener hands
the URL to an already-running browser and returns as soon as it is accepted; it
never sees the response. `open_url.py` reports `opened: true` on exactly that
basis and says so in its own output.
A retired, mistyped or wrong-storefront ASIN opens Amazon's "Sorry, we couldn't
find that page" dog with exactly the same exit status as a live product.

So do not report an open as a confirmed product. Say what you opened and on which
storefront, and if the ASIN has not been verified this session, say that too
rather than restating the product name from memory.

The cross-storefront case is the one that bites: an ASIN from `amazon.co.uk`
frequently has **no listing on `amazon.com`** and vice versa. Same identifier,
different catalogue. Never rewrite the domain to the user's home storefront and
present the result as the same product — either open it where it was found, or
say that the ASIN needs to be looked up again on the other storefront.

## Other views of the same ASIN

| Want | URL |
| --- | --- |
| Product page | `/dp/<ASIN>` |
| All reviews | `/product-reviews/<ASIN>` |
| Critical reviews only | `/product-reviews/<ASIN>?filterByStar=critical` |
| All sellers and offers | `/dp/<ASIN>?aod=1` — for the user's eyes only. Fetching it returns HTTP 200 and 3 MB with **zero** offers in the markup; the panel is client-rendered. |

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

- `amazon-marketplace-config` — which storefront, and for which address
- `amazon-listing-check` — the facts, without a tab
- `amazon-delivery-check` — signed-in dates, coupons, Prime-exclusive prices
- `amazon-shortlist` — when the argument was a need, not an ASIN
