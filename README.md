# amazon-us

Claude Code plugin for **Amazon.com marketplace research**.

Amazon is the case where "the fetch returned something" and "the fetch worked"
come apart. The default fetch tool cannot reach it at all, its bot wall answers
with HTTP 200, and every delivery date it renders is for whichever ZIP the
requesting IP resolved to — with nothing on the page to say which. Each of those
failures produces a confident, well-formatted, wrong answer.

This plugin encodes the routing and the verification discipline that survive
those, so an Amazon question gets an answer you can act on.

## Scope

This is the **marketplace-specific** plugin for Amazon US. It is deliberately
narrow, and complements rather than replaces:

- [`purchasing`](https://github.com/danielrosehill/Claude-Purchasing-Plugin) —
  the generalist ecommerce research plugin: intake, specs, cross-vendor
  comparison, recommendations, preference memory.
- [`shopping`](https://github.com/danielrosehill/Claude-Shopping-Plugin) —
  region-specific consumer retail.

Use `purchasing` for the buying workflow. Use this when the question is
specifically *what does Amazon say*.

## Commands

| Command | Does |
| --- | --- |
| `/amazon-us:amazon-find <need>` | Category-first research: establish what actually solves the problem, search, verify, recommend one with a trade-off |
| `/amazon-us:amazon-check <ASIN\|URL>...` | Verified price, stock, rating, seller and specs, read off the listing |
| `/amazon-us:amazon-delivery <ASIN>...` | Real Prime dates, coupons and Prime-exclusive pricing from your signed-in browser |

## Skills

Anonymous, cheap, stateless — start here:

- **`amazon-fetch-route`** — pick the route, prove it worked. Read before the
  first fetch of a session.
- **`amazon-shortlist`** — need → category → search → verified candidates.
- **`amazon-listing-check`** — price, stock, rating, seller, specs for named ASINs.

Signed-in browser, for facts that only a session renders:

- **`amazon-delivery-check`** — Prime dates, overnight cut-offs, coupons.
- **`amazon-search`** — filtered search with per-card real delivery, using the
  facet grammar and tested extractors in `profiles/amazon-us.json`.
- **`brand-scrub`** — harvests the brand facet into a durable allow/blocklist, so
  the next search starts from a filtered field.

`profiles/amazon-us.json` holds everything volatile — facet IDs, sort keys,
selectors, trust rubric, session-dependence notes. When Amazon changes, that is
the file that gets edited. See [`profiles/README.md`](profiles/README.md).

## The script

`scripts/amazon_fetch.py` fetches Amazon from the local machine and prints JSON.

```bash
python3 scripts/amazon_fetch.py probe
python3 scripts/amazon_fetch.py listing B0CHHB4RHV B0XXXXXXXX --expect-zip 02139
python3 scripts/amazon_fetch.py search "usb c power bank" --rh p_85:2470955011
```

No dependencies beyond `curl` and Python 3.

`probe` answers the three questions that matter before trusting anything: is the
route working, is it being walled, and which ZIP will delivery dates be for.

## What it knows that is not obvious

- **`WebFetch` cannot reach amazon.com.** HTTP 500 on `/dp/`, 503 on `/s?k=`.
  Consistently, not transiently. Don't spend a call rediscovering it.
- **The bot wall returns HTTP 200 with a captcha body.** Status codes are not
  the success test. Check the body: a real page is 400–500 KB.
- **Delivery dates belong to a ZIP.** Fetching from the user's own machine gives
  the user's own area; a cloud fetcher or a VPN exit in another city gives an
  equally confident date for somewhere else. `--expect-zip` turns that from a
  silent wrong answer into a warning.
- **Never recover the ZIP by regexing for five digits.** Amazon's asset
  filenames collide with real ZIPs — `01890+Vwk8L.css` reads as Winchester MA on
  every product page.
- **An anonymous date is the non-Prime date.** Measured gap on one seven-ASIN
  shortlist: four days.
- **`Item Dimensions` may be folded or unfolded**, in the same field, with
  nothing to distinguish them — and a large height is often handle height.
- **Delivery filters are sticky across browser searches** and mutually
  exclusive with each other. A sweep run under a stuck filter silently drops
  every slower-shipping product.
- **Navigating a signed-in session can land somewhere you did not ask for.**
  Prefer read-only same-origin fetches, which cannot wander.

Full detail in [`reference/`](reference):
[fetch-routes](reference/fetch-routes.md) ·
[search-filters](reference/search-filters.md) ·
[verification-traps](reference/verification-traps.md)

## Privacy and safety

- Ships **no address, no account, no credentials**. Where a ZIP matters the
  skills ask for one rather than assuming, and report the ZIP a page actually
  resolved to alongside any date.
- `amazon_fetch.py` is anonymous and stateless — no cookies, no session.
- The browser skill is read-only. It does not add to cart, place orders, or
  click controls. If a navigation lands on an unexpected page it opens a fresh
  tab instead of interacting.

## Install

```
/plugin marketplace add danielrosehill/Claude-Code-Plugins
/plugin install amazon-us
```

## License

MIT.
