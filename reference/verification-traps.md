# Verification traps on Amazon listings

Things on an Amazon page that read as authoritative and are not. Each of these
produced a confident wrong answer at least once.

## The status code

Amazon's bot wall returns **HTTP 200 with a captcha body**. Check the body, not
the status. See [fetch-routes.md](fetch-routes.md).

## The delivery date belongs to a ZIP you may not have set

An anonymous fetch always renders *a* delivery promise, for whatever ZIP the
requesting IP resolves to. It never errors and never says which. Read `ship_to`
before quoting `delivery`.

Also: a listing offers up to **two** delivery options, differing in cost as well
as speed, and `#deliveryBlockMessage` returns only the first. The second one is
where the Prime date usually is — including on an anonymous fetch. Read
`delivery_options`, not `delivery`; contract in [delivery.md](delivery.md).

## Item Dimensions may be folded or unfolded, in the same field

Amazon's `Item Dimensions L x W x H` is populated by the seller, and for
anything that collapses, sellers disagree about which state to publish. Two
carts in the same category:

- `15.6" x 10.6" x 3.2"` — folded
- `17.52" x 10.23" x 37"` — erect, where 37 in is the *handle height*

Nothing in the field distinguishes them. Take folded size from the bullets,
where sellers advertise it deliberately, and treat a large height in the spec
table as suspect.

The same conflation runs through platform trucks and hand carts generally: a
height quoted in the title is almost always handle height, not deck height. If a
"1 m platform truck" matters, verify the deck.

## The spec table and the bullets disagree, on the same listing

One cart's first bullet opens "At just 4 lbs" while its own spec table says
`Item Weight: 2.8 pounds`. Neither is flagged; both are on the page. Where the
number decides the purchase, read both and record the disagreement rather than
picking the one you prefer.

## The first price on the page is the List Price

The struck-through "List Price" is rendered in the same block as the price you
would pay, and on discounted listings it comes **first**. An extractor that takes
the first price span therefore reports the list price, silently, with no marker.

Measured 2026-08-19 on ASIN `0140449132`: the plugin reported `$16.00` against a
real `$12.91` — a 24% overstatement. Skip any price whose enclosing `a-price`
span carries `a-text-price`, `data-a-strike="true"` or `basisprice`.

`#corePrice_feature_div` is additionally **empty on books**; the price lives in
`#corePriceDisplay_desktop_feature_div`.

And the raw HTML and the live DOM disagree about where the value is. In the HTML
the `priceToPay` screen-reader span carries it; in the rendered DOM that span is
blank and the price is assembled from `.a-price-symbol` / `-whole` / `-fraction`.
A selector proven against one will return nothing against the other.

## A price with no buy box belongs to something else

A variant parent with no featured offer renders no buy box, no delivery block and
no seller row — but the page still carries prices belonging to **other variants**,
and an extractor will return one.

Measured 2026-08-19 on `B003J9LZE4`: `$108.99`, `availability: ""`, no delivery.
Nothing said the item could not be bought. Note this defeats the usual test:
`Currently unavailable` appears only inside JavaScript config strings on such a
page, never as rendered text.

The reliable check is the absence of `#add-to-cart-button` and `#buy-now-button`.
`amazon_fetch.py` reports it as `buyable` and attaches a `no_offer_warning`.

A real browser can disagree here: navigating to the same parent URL redirected to
`?th=1` and pinned a variant, so the browser saw a buy box where the anonymous
fetch saw none. Same ASIN, two answers, both correct for what they fetched.

## The stock line has a second sentence

`In stock` and `In stock. Usually ships within 4 to 5 days` are different answers,
and reading only the first span of `#availability` returns the same text for both.
The handling-time sentence is often the reason a September date sits under an
in-stock badge. `Only 17 left in stock - order soon` lives in a different colour
class again.

## `textContent` on a fetched document pulls in scripts

`DOMParser` builds a document with no layout, so `innerText` is empty and
`textContent` is the obvious substitute — but it concatenates the contents of
every `<script>` and `<style>` too. Three consequences, all observed:

- `#availability` returns `In Stock` followed by an inline stylesheet;
- `#olp_feature_div` returns nothing but CSS;
- the page's inline JSON — including session identifiers — lands in your context,
  and the Chrome extension blocks the whole tool result as cookie/query-string
  data.

Strip `script`, `style` and `noscript` before reading text from a parsed document.

## `?aod=1` returns 200, 3 MB, and no offers

The "all sellers and offers" panel is client-rendered. Fetching `/dp/<ASIN>?aod=1`
or `/gp/offer-listing/<ASIN>` same-origin returns HTTP 200 and a full-size page
containing **zero** `#aod-offer` nodes — a textbook success-shaped failure. The
older ajax endpoints (`/gp/product/ajax?...experienceId=aodAjaxMain` and
variants) now return **404**.

Opening `?aod=1` in a real tab does work, for a human. Treat it as a handoff URL,
not a data source.

## `Sold by` and `Shipper / Seller` are different facts

`#sellerProfileTriggerId` and the `merchantName` JSON key are both gone from the
page as of 2026-08-19, so any extractor keyed on them returns null on every
listing while looking like it simply found no seller.

What renders today is `#merchantInfoFeature_feature_div`, and its **label** is
itself the fulfilment signal:

| Label | Means |
| --- | --- |
| `Sold by X` + `#fulfillerInfoFeature_feature_div` = `Ships from Amazon` | FBA — merchant sells, Amazon fulfils |
| `Shipper / Seller X`, fulfiller div empty | The merchant does both |

Both values are duplicated in the markup for the responsive layouts
(`Sold by waveshare waveshare Sold by waveshare`). The repeat is a layout
artefact, not a second seller.

## A dead ASIN 404s on fetch but not on open

A same-origin `fetch` of `/dp/<ASIN>` for an ASIN with no listing on this
storefront returns a genuine **HTTP 404** with a ~2 KB body. That is a real
existence check, and it is one the browser-handoff route cannot perform — see *An
opened tab is not a live product* above. Two routes, and only one of them can
tell you whether the thing exists.

## Grid prices are positional; listing prices are not

A price in a search grid is the price nearest the link in a flattened page, not
a value read from a labelled field. `amazon_fetch.py search` pairs each result
with the price inside that result's own `data-asin` block, which is structural
and better — but it is still a shortlisting tool.

Open the listing before recommending anything. Three facts exist only there: who
actually sells it, whether it is `Currently unavailable` (which never appears in
search results), and how many competing offers there are at what price.

## Pack sizes are separate ASINs with separate everything

Pack pricing is routinely non-monotonic — a 4-pack can be cheaper per unit *and*
arrive sooner than the 2-pack of the identical item. Price every pack size
separately and write out the per-unit figure.

## Ratings hide the failure mode

A low rating on a low review count is the highest-value signal available here.
Established brand names ship rebadged product more often than the name suggests,
and an unbranded listing with 2,000 ratings is not thereby trustworthy.

Read at least one critical review on anything expensive. The average hides the
failure mode; the review text names it.

Review authenticity cannot be checked programmatically — Fakespot shut down in
2025 and nothing replaced it, and AI-written reviews read cleanly enough that
linguistic tells no longer discriminate. Use structural signals instead: who the
seller is, whether the brand exists off Amazon, whether `Date First Available`
is recent. Say the review score is unverified rather than implying otherwise.

## Sponsored rows are not results

Filter sponsored placements out before any judgement. They skew heavily toward
unknown brands buying placement. `amazon_fetch.py` marks them `sponsored: true`.

## A filter that prunes to nothing is a finding

An empty filtered result set is a fact about the category or the address, not a
successful search. Say so rather than returning an empty table, and say what the
filter cost — the result count before and after.

Likewise, report rows with no price as "no current offer" rather than dropping
them. A missing price is not a cheap price.

## An opened tab is not a live product

Any platform opener — `xdg-open` on Linux, `open` on macOS, `start` on Windows,
and `scripts/open_url.py`, which wraps all three — hands a URL to an
already-running browser and returns without ever seeing the response. A retired,
mistyped or region-wrong ASIN opens Amazon's
"Sorry, we couldn't find that page" placeholder with exactly the same exit
status as a live listing. Opening is a handoff, not a check.

The region case is the frequent one: an ASIN copied from `amazon.co.uk`,
`amazon.de` or `amazon.ca` often has **no `.com` listing at all**. Same
identifier, different catalogue. Rewriting the domain produces a URL that looks
right and resolves to nothing.

Also note that an ASIN is ten characters of `[A-Z0-9]` and **not necessarily
`B0`-prefixed** — books keep their ISBN-10, including trailing-`X` forms. A
validator that insists on `B0` rejects valid input.

## What no route can tell you

- **Price history.** No free programmatic source. Keepa is the working paid one.
- **Listing age**, when `Date First Available` is absent — which is common on
  electronics. Do not substitute review count for age.
- **Per-card brand.** The brand row renders on brand-navigational queries only
  (17 of 21 cards on one query, 0 of 20 on another). The facet rail is the
  source of truth; never build a brand list from cards.
