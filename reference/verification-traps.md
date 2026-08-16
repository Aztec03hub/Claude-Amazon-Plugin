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

Also: an anonymous date is the **non-Prime** date. On one seven-ASIN shortlist
the anonymous route said 21 August for every row while the signed-in Prime
session said 17 August for five of them.

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

## What no route can tell you

- **Price history.** No free programmatic source. Keepa is the working paid one.
- **Listing age**, when `Date First Available` is absent — which is common on
  electronics. Do not substitute review count for age.
- **Per-card brand.** The brand row renders on brand-navigational queries only
  (17 of 21 cards on one query, 0 of 20 on another). The facet rail is the
  source of truth; never build a brand list from cards.
