# Fetch routes for Amazon.com

Which tool to use for which Amazon question, and — more usefully — which routes
fail in ways that look like success.

## Route table

| Question | Route | Status |
| --- | --- | --- |
| Finding candidate products, reviews, comparisons | `WebSearch` | Works |
| Non-Amazon retailer or manufacturer pages | `WebFetch` | Works |
| **Amazon search or product pages** | `WebFetch` | **Fails.** HTTP 500 on `/dp/`, 503 on `/s?k=`. Not transient. |
| **Amazon search or product pages** | **`scripts/amazon_fetch.py`** | **Works. Default.** Local machine, browser headers. |
| Same-day/overnight availability, the Prime basket minimum, coupons, Prime-exclusive price, cart, order history | A real signed-in browser | Only route that can answer these. The standard Prime date is **not** on this list -- the anonymous route has it; see below |
| Amazon, if the local route is walled | A real browser | Retrying curl reproduces the same wall |

## The status code is not the success test

Amazon's bot wall answers with **HTTP 200 and a captcha body**. Any check
written against the status code will report success while holding a challenge
page. `amazon_fetch.py` tests the body instead: a response containing `captcha`
or `not a robot`, or under 20 KB, is treated as blocked. A real product page is
400–500 KB.

If a fetch comes back blocked, escalate to a real browser rather than retrying —
the same headers reproduce the same wall.

## Delivery dates: which ZIP is the promise for?

This is the single most dangerous thing about Amazon research, because every
failure mode here renders as a confident, correctly-formatted, wrong answer.

Amazon geolocates an anonymous request by IP and renders a delivery promise for
wherever that IP resolves to. So:

- **From the user's own machine**, the promise is for the user's own area and is
  usable. The page carries `Delivering to <Town> <ZIP>` and `"zipcode":"<ZIP>"`.
- **From a cloud fetcher or a VPN exit in another city**, the promise is equally
  well-formed and is for that city. Nothing on the page flags it.

There is no way to tell these apart except by reading the ZIP out of the body.
`amazon_fetch.py` returns it as `ship_to` on every listing, and `--expect-zip`
turns a mismatch into an explicit warning instead of a silent wrong answer.

```bash
scripts/amazon_fetch.py listing B0CHHB4RHV --expect-zip 02139
```

**Never recover the ZIP by regexing `\b\d{5}\b` over the page.** Amazon's static
asset filenames collide with real ZIPs — `01890+Vwk8L.css` appears on every
product page and reads as Winchester MA 01890. Match the labelled fields only.

`ship_to` is reliable on **listing** pages. Search pages often render only the
unresolved `Update location` placeholder, so do not expect a ZIP back from
`search`.

### A single delivery string is the wrong shape

A listing offers up to two options that differ in **cost** as well as speed, and
`#deliveryBlockMessage` — which is what a naive read returns — stops at the first
`</div>`, giving you only the first one. Read `delivery_options` instead, which
`amazon_fetch.py listing` returns from the structured `data-csa-c-*` attributes
Amazon publishes beside the prose. Full contract: [delivery.md](delivery.md).

### What the anonymous route can and cannot see

Corrected 2026-08-19. This page previously said the anonymous route only ever
returns the non-Prime promise and understates arrival by several days. That is
true of `#deliveryBlockMessage` and **false of the page**: the Prime date is in
the second option, and on five Amazon-fulfilled ASINs it matched the signed-in
session exactly (`Tomorrow, August 20` on both routes).

What a signed-in session actually adds:

- the **same-day / overnight upgrade** — anonymous offered "FREE Monday,
  August 24" where signed-in offered "FREE Overnight 4 AM - 8 AM";
- the **lower basket minimum** — $25 signed in against $35 anonymous;
- the **order-within cutoff** on the leading option;
- coupons and Prime-exclusive pricing, which never render anonymously at all.

On merchant-fulfilled items the signed-in session added nothing at all: four
paid-shipping ASINs were identical field for field on both routes. Escalating to
a browser for those spends a session for no new fact.

And a Prime date assumes a live membership on the delivery date, which no product
page knows. See [delivery.md](delivery.md#is-prime-actually-in-force).

## Batch the shortlist in one browser call

Do not navigate once per ASIN. From a tab already on any `amazon.com` page, a
same-origin `fetch` with `credentials:'include'` carries the signed-in session,
so one `javascript_tool` call can price an entire shortlist without touching the
address bar:

```js
const asins = ['B0XXXXXXX1','B0XXXXXXX2','B0XXXXXXX3'];
const out = {};
for (const a of asins) {
  const h = await fetch('https://www.amazon.com/dp/' + a, {credentials:'include'}).then(r => r.text());
  const d = new DOMParser().parseFromString(h, 'text/html');
  out[a] = {
    price:    d.querySelector('#corePrice_feature_div .a-offscreen')?.textContent,
    shipTo:   d.querySelector('#glow-ingress-line2')?.textContent?.trim(),
    delivery: d.querySelector('#deliveryBlockMessage')?.textContent?.replace(/\s+/g,' ').trim(),
  };
}
JSON.stringify(out, null, 1)
```

This is faster than navigation, keeps 400 KB pages out of context, and avoids a
real hazard: **navigating a signed-in Amazon session can land somewhere you did
not ask for.** A plain navigate to a `/dp/` URL once landed on
`/progress-tracker/package/preship/cancel-items` for an unrelated live order — a
page whose controls cancel real orders. Read-only same-origin fetches cannot
wander like that. If a navigation does land somewhere unexpected, click nothing
and open a fresh tab.

That page is now identified: it is the target of the **Cancel items** button on
any order-details page, one link from every live order. See
[account-pages.md](account-pages.md), where the flow is mapped deliberately for
`amazon-order-cancel`. Knowing where it comes from does not soften the rule —
arriving there without asking still means click nothing.

## Reading a delivery date out of a rendered page

Ask for the delivery date **in the main buy box only, not sponsored or related
items**. Without that qualifier a `find` will happily return an "Overnight"
badge belonging to a sponsored product further down the page and present it as
the delivery term for the item you asked about.

Pulling the whole page text is the wrong tool for a single field — a product
page is 400–500 KB and a search page around 700 KB. Query the specific selector.

## Pack sizes and coupons

Price every pack size of the same product separately. Pack pricing on Amazon is
routinely non-monotonic: a 4-pack can be cheaper per unit *and* arrive sooner
than the 2-pack of the identical item, because the packs are separate ASINs with
separate stock.

Coupons appear as a checkbox in the buy box, apply only if ticked, and are
invisible to any anonymous fetch. Record the list price, the coupon and the net
separately — a bare net price is not reproducible.
