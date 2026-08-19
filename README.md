# amazon

Claude Code plugin for **Amazon marketplace research**, across Amazon's regional
storefronts.

Amazon is the case where "the fetch returned something" and "the fetch worked"
come apart. The default fetch tool cannot reach it at all, its bot wall answers
with HTTP 200, and every delivery date it renders is for whichever ZIP the
requesting IP resolved to — with nothing on the page to say which. Each of those
failures produces a confident, well-formatted, wrong answer.

This plugin encodes the routing and the verification discipline that survive
those, so an Amazon question gets an answer you can act on.

## Scope

This is the **Amazon** plugin: all of Amazon's regional storefronts, not just
amazon.com. The machinery is region-neutral and the volatile knowledge is data —
`profiles/amazon-marketplaces.json` for domain, currency and postcode format,
`profiles/<marketplace>.json` for the search grammar. Only `amazon-us` has a
verified search grammar today; the rest are a derivation away, not a rewrite
away. See [reference/marketplaces.md](reference/marketplaces.md).

Nothing personal ships in the repo. Delivery addresses and per-marketplace
preferences live in a user directory outside it, shared with `procurement-tools`
rather than forked — see [Configuration](#configuration).

It is deliberately narrow, and complements rather than replaces:

- [`procurement-tools`](https://github.com/danielrosehill/Claude-Purchasing-Plugin) —
  the generalist ecommerce research plugin: intake, specs, cross-vendor
  comparison, recommendations, preference memory.
- [`shopping`](https://github.com/danielrosehill/Claude-Shopping-Plugin) —
  region-specific consumer retail.

Use `procurement-tools` for the buying workflow. Use this when the question is
specifically *what does Amazon say*.

## Commands

| Command | Does |
| --- | --- |
| `/amazon:amazon-find <need>` | Category-first research: establish what actually solves the problem, search, verify, recommend one with a trade-off |
| `/amazon:amazon-check <ASIN\|URL>...` | Verified price, stock, rating, seller and specs, read off the listing |
| `/amazon:amazon-delivery <ASIN>...` | Same-day/overnight availability, the Prime basket minimum, cutoffs, coupons and Prime-exclusive pricing from your signed-in browser |

## Skills

Anonymous, cheap, stateless — start here:

- **`amazon-fetch-route`** — pick the route, prove it worked. Read before the
  first fetch of a session.
- **`amazon-shortlist`** — need → category → search → verified candidates.
- **`amazon-listing-check`** — price, stock, rating, seller, specs for named ASINs.
- **`amazon-marketplace-config`** — which storefront, currency, postcode and
  egress country an answer should be built from, resolved from the stored
  delivery address. Read before anything that quotes a price or a date.
- **`amazon-open-asin`** — open an ASIN in your own browser as a clean `/dp/` URL
  on the right storefront, tracking stripped. Hands the page over; reads nothing.

Signed-in browser, for facts that only a session renders:

- **`amazon-delivery-check`** — overnight availability, cut-offs, coupons, and
  whether Prime is still in force on the delivery date.
- **`amazon-search`** — filtered search with per-card real delivery, using the
  facet grammar and tested extractors in `profiles/amazon-us.json`.
- **`brand-scrub`** — harvests the brand facet into a durable allow/blocklist, so
  the next search starts from a filtered field.
- **`amazon-account-import`** — fills the address book, default ship-to and Prime
  state into the user config from the session, so the interview covers only what
  Amazon cannot answer.

`profiles/amazon-us.json` holds everything volatile — facet IDs, sort keys,
selectors, trust rubric, session-dependence notes. When Amazon changes, that is
the file that gets edited. See [`profiles/README.md`](profiles/README.md).

## Configuration

The plugin ships **no address, no ZIP, no account state**. It reads them from a
user directory, found by search rather than by a hardcoded path:

| Order | Location |
| --- | --- |
| 1 | `$AMAZON_PLUGIN_CONFIG` |
| 2 | `<user-data-root>/marketplaces/` |
| 3 | `<user-data-root>/procurement-tools/` |

`addresses.yaml` and `marketplaces.yaml` are already owned by
[`procurement-tools`](https://github.com/danielrosehill/Claude-Purchasing-Plugin),
and a delivery address is not Amazon-specific knowledge, so this plugin adopts
that store instead of forking it. It never migrates one silently — two copies of
an address is how a delivery date gets quoted for last year's flat.

```bash
python3 scripts/user_config.py path              # where the store is
python3 scripts/user_config.py show              # what is in it, redacted
python3 scripts/user_config.py resolve storrs    # storefront, currency, postcode, egress
```

Filling it, two halves:

- **`/procurement-tools:shop-setup`** interviews the user for what no account
  knows — deadlines, luggage limits, tax rates, where the driver actually goes.
- **`amazon-account-import`** reads what the account does know straight out of a
  signed-in session: the address book, the default ship-to, Prime state.

## The script

`scripts/amazon_fetch.py` fetches Amazon from the local machine and prints JSON.
`-m/--marketplace` picks the storefront on every mode.

```bash
python3 scripts/amazon_fetch.py probe
python3 scripts/amazon_fetch.py listing B0CHHB4RHV B0XXXXXXXX --expect-postcode 02139
python3 scripts/amazon_fetch.py search "usb c power bank" --rh p_85:2470955011
python3 scripts/amazon_fetch.py probe -m amazon-uk B0XXXXXXXX
```

No dependencies beyond `curl` and Python 3.

`probe` answers the three questions that matter before trusting anything: is the
route working, is it being walled, and which postcode will delivery dates be for.

Note that `amazon-us` throughout this repo is a **storefront** id, not the plugin
id. The plugin is `amazon`; `amazon-us` is one of the twenty storefronts it
speaks to, and `profiles/amazon-us.json` is that storefront's search grammar.

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
- **Delivery is two priced options, not one date.** The fast one usually carries
  a basket minimum. `#deliveryBlockMessage` returns only the first; the Prime
  date is normally the second, and it is present anonymously.
- **`Item Dimensions` may be folded or unfolded**, in the same field, with
  nothing to distinguish them — and a large height is often handle height.
- **Delivery filters are sticky across browser searches** and mutually
  exclusive with each other. A sweep run under a stuck filter silently drops
  every slower-shipping product.
- **Navigating a signed-in session can land somewhere you did not ask for.**
  Prefer read-only same-origin fetches, which cannot wander.
- **An ASIN is only meaningful with its storefront.** The same ten characters can
  be a live listing on `amazon.co.uk`, a different product on `amazon.com`, and
  nothing on `amazon.de`. Rewriting the domain is a guess, and it returns HTTP
  200 either way.
- **The currency is a property of the route, not the listing.** `amazon.com`
  renders ILS from an Israeli IP and USD from a US one, same URL, same ASIN.

Full detail in [`reference/`](reference):
[fetch-routes](reference/fetch-routes.md) ·
[delivery](reference/delivery.md) ·
[marketplaces](reference/marketplaces.md) ·
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
/plugin install amazon
```

## License

MIT.
