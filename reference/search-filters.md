# Amazon.com search filter grammar

Filter node IDs for amazon.com search, so a filtered search can be constructed
as a URL instead of clicked through the left rail.

Mapped 2026-08-16 by driving a signed-in Chrome across four queries: `usb c
power bank`, `paper towels`, `aa batteries`, `usb wifi adapter`.

## How the URL is built

Filters live in a single `rh=` parameter. Each is `<group>:<node>`, joined by
commas. URL-encoded, `:` is `%3A` and `,` is `%2C`.

```
https://www.amazon.com/s?k=usb+wifi+adapter&rh=p_85%3A2470955011%2Cp_90%3A8308921011
                                               └── All Prime ──┘ └─ by tomorrow ─┘
```

Nothing else in the URL matters. `qid`, `ref`, `rnid` and `ds` are echoed back
by Amazon after a click and can be dropped when building a URL by hand —
verified by navigating to a hand-built `k` + `rh` URL and confirming the rail
came back with the right boxes ticked.

`amazon_fetch.py search "<query>" --rh p_85:2470955011` does the encoding.

## Nodes

| Rail group | Option | Node |
| --- | --- | --- |
| Delivery | All Prime | `p_85:2470955011` |
| Prime Delivery | Overnight by 11AM | `p_101:19346686011` |
| Delivery Day | Get It by Tomorrow | `p_90:8308921011` |
| Delivery Day | Add to Delivery (Amazon Day) | `p_90:210940785011` |
| Customer Reviews | 4 stars & up | `p_72:1248903011` |

Group refinement IDs, which appear as `rnid=` after a click and help identify
which group an unknown node belongs to: `p_85` → `2470954011`, `p_101` →
`19346684011`, `p_90` → `8308919011`, `p_72` → `1248901011`.

**A facet missing from the sidebar does not mean the node is dead.** It means
this query and this ZIP have no hits for it. Compose from the node IDs
regardless.

**Facet labels drift even when IDs do not.** `p_101` renamed itself between two
consecutive days, because the label names the current cutoff time. Never quote a
cutoff from this table — read it live or omit it.

## Delivery-speed filters are mutually exclusive

`Overnight by 11AM` (`p_101`) and the two `p_90` options are alternative
renderings of one delivery-speed facet, not independent checkboxes. Selecting
`Get It by Tomorrow` while `Overnight by 11AM` was active silently **dropped**
`p_101` from `rh` rather than combining them. The two `p_90` options are
likewise exclusive with each other.

So there is no way to ask for "overnight AND tomorrow". Pick one.

On `usb c power bank`, `p_101` and `p_90` each returned exactly 555 results out
of 10,000+ unfiltered. Whether those are genuinely the same set or that was a
coincidence of one query was not established — do not treat them as
interchangeable on that evidence.

## Filters are sticky across searches

**This is the trap.** After filtering one search by `Get It by Tomorrow`,
navigating to a completely fresh URL with no `rh=` at all —
`https://www.amazon.com/s?k=aa+batteries` — still came back with `Get It by
Tomorrow` ticked and results narrowed to 203. Amazon carries the delivery filter
in session state, not only in the URL.

A research sweep run under a sticky filter silently omits every slower-shipping
product, including, routinely, the best one. Nothing in the result set says it
is filtered except the left rail.

Before reading any result set in a browser, check the rail and confirm which
boxes are ticked. To clear one, click the `< Clear` link under that group's
heading; the cleared URL carries `ref=sr_ex_p_90_0` — `ex` for exclude — which
is a reliable tell that a filter was just dropped.

This does not affect `amazon_fetch.py`, which is stateless and carries no
cookies. That is a reason to prefer it for sweeps.

## Same-day availability is address-dependent

Whether a `Get It Today` group appears in the rail at all depends on the
delivery ZIP. At one rural New England address none of four queries offered it,
and the fastest node available was `Overnight by 11AM`. Do not hunt for a
same-day node that the address does not support — check the rail once, and if it
is absent, answer "can I have it today" through local retail instead.

## What a signed-in grid gives you that an anonymous one cannot

In a signed-in session the search grid itself carries address-correct delivery
information rendered per result:

- `Thu, Aug 20 FREE delivery with Prime`
- `Overnight 7 AM - 11 AM FREE delivery on $25 qualifying items`
- `Order within 18hr 14min to add to Monday's delivery`

The signed-in grid also badges items the account has bought before — `Purchased
Dec 2024`, `Purchased 1 time` — which is worth reading before recommending
anything.

Still open the listing before recommending. Sponsored placements interleave with
organic results regardless of who is signed in, and grid rows frequently show a
different pack size than the one you think you are looking at.

## Reading the rail programmatically

A browser extension may block a script that touches `location.href` or reads
filter `href` attributes, returning something like `[BLOCKED: Cookie/query
string data]` and running nothing. Read the rail with a screenshot of the
left-hand region, or with a `find`, and recover node IDs by clicking a filter
and reading the resulting URL out of the tool's tab-context line.
