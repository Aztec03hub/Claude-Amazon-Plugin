---
name: amazon-delivery-check
description: Get the delivery facts that exist only inside the user's signed-in Amazon session - same-day and overnight availability, the Prime basket minimum, the order-within cutoff, coupons and Prime-exclusive pricing - plus a check that the Prime membership is still live on the delivery date. Use when the user asks whether something arrives today or tomorrow, whether it beats a deadline, or what it actually costs at checkout. For the standard Prime date, use amazon-listing-check instead; the free route already has it.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Read
---

# Amazon delivery check

## Come here only for what the free route cannot see

This skill costs a browser session. Spend it deliberately, because the list of
session-only facts is shorter than it used to look. Measured 2026-08-19 across
eleven ASINs:

| Fact | Signed-in session needed? |
| --- | --- |
| The standard Prime arrival date | **No.** It is the second delivery option on the anonymous page, and it matched the signed-in session exactly on 5/5 Amazon-fulfilled ASINs |
| Same-day / overnight availability | **Yes.** Anonymous showed `FREE Monday, August 24`; signed-in showed `FREE Overnight 4 AM - 8 AM` |
| The basket minimum | **Yes.** $25 signed in against $35 anonymous, same ASIN |
| The order-within cutoff | **Yes**, on the leading option |
| Coupons, Prime-exclusive pricing | **Yes.** Never render anonymously |
| Anything about a merchant-fulfilled item | **No.** Four paid-shipping ASINs were identical field for field on both routes |
| Whether Prime is still in force on the delivery date | **Yes**, and nothing else can answer it |

So: run `amazon-listing-check` first. Come here when the answer turns on
same-day/overnight, on the true checkout total, or on a deadline close enough
that the cutoff matters.

The earlier claim that the anonymous route understates arrival by four days was
an artefact of reading `#deliveryBlockMessage`, which stops at the first option.
Corrected 2026-08-19; see [reference/delivery.md](../../reference/delivery.md).

## Check the membership before quoting a Prime promise

A Prime date assumes a live membership on the day the parcel arrives, and no
product page knows that. `/gp/primecentral` does:

```js
const h = await fetch('/gp/primecentral', {credentials:'include'}).then(r => r.text());
const d = new DOMParser().parseFromString(h, 'text/html');
d.querySelectorAll('script,style,noscript').forEach(n => n.remove());
const clean = s => (s||'').replace(/[=?&]/g,' ').replace(/\s+/g,' ').trim();
JSON.stringify({
  state: clean(d.querySelector('[cel_widget_id^="prime-membership-central-profile"]')?.textContent).slice(0,200),
  plan:  clean(d.querySelector('[cel_widget_id^="plan-change-action-desktop"]')?.textContent).slice(0,300),
}, null, 1)
```

Anchor on `cel_widget_id` prefixes, not on class names: Prime Central is built
from CSS modules whose class names carry a build hash and will churn. Strip
`script` and `style` first, or `textContent` returns the page's inline
JavaScript — and the extension blocks the whole result as cookie data.

The account measured on 2026-08-19 read `8 days left in your trial`, converting
to a paid monthly plan on 2026-08-27 — beyond several delivery estimates being
quoted at the time. When the state is a trial or a lapsing membership, say so
alongside any date past its end.

## Batch the whole shortlist in one call

Do not navigate once per ASIN. From a tab already on any Amazon page, a
same-origin `fetch` carries the session, so one `javascript_tool` call prices the
entire shortlist. Read the delivery **attributes**, not the sentence:

```js
const asins = ['B0XXXXXXX1','B0XXXXXXX2'];
const slot = {DEXUnifiedCXPDM:'primary', DEXUnifiedCXSDM:'secondary'};
const out = {};
for (const a of asins) {
  const h = await fetch('/dp/' + a, {credentials:'include'}).then(r => r.text());
  const d = new DOMParser().parseFromString(h, 'text/html');
  const seen = new Set(), options = [];
  for (const el of d.querySelectorAll('[data-csa-c-content-id="DEXUnifiedCXPDM"],[data-csa-c-content-id="DEXUnifiedCXSDM"]')) {
    const g = n => el.getAttribute('data-csa-c-' + n) || null;
    const o = {slot: slot[el.getAttribute('data-csa-c-content-id')],
               cost: g('delivery-price'), when: g('delivery-time'),
               condition: g('delivery-condition'), cutoff: g('delivery-cutoff'),
               program: g('delivery-benefit-program-id')};
    const k = Object.values(o).join('~');
    if (seen.has(k)) continue; seen.add(k); options.push(o);
  }
  out[a] = {
    price:  d.querySelector('#corePriceDisplay_desktop_feature_div .priceToPay')?.textContent.replace(/\s+/g,''),
    shipTo: d.querySelector('#glow-ingress-line2')?.textContent?.trim(),
    buyable: !!(d.querySelector('#add-to-cart-button') || d.querySelector('#buy-now-button')),
    options,
  };
}
JSON.stringify(out, null, 1)
```

This is faster than navigating, keeps 400 KB pages out of context, and avoids a
real hazard — see below.

Reading a rendered page instead? Then `price` must come from `.priceToPay`'s
text, not its `.a-offscreen` span, which is **blank in the live DOM** even though
it carries the value in the raw HTML.

## Navigation hazard

**A plain navigate inside a signed-in Amazon session can land somewhere you did
not ask for.** In one session a navigate to a `/dp/` URL landed on
`/progress-tracker/package/preship/cancel-items` for an unrelated live order — a
page whose controls cancel real orders.

If that happens: click nothing, open a fresh tab, and prefer the read-only
same-origin fetch above, which cannot wander. Never click a control on a page
you did not intend to open.

## Procedure

1. `tabs_context_mcp` first. Create a new tab rather than reusing one of the
   user's, unless they asked otherwise.
2. Navigate once, to any Amazon page.
3. Check the Prime membership state if any date you will quote is more than a
   few days out.
4. Run the batch script above.
5. Confirm `shipTo` before quoting anything. It renders **truncated**, as
   `<Town na...> <ZIP>` — so check the ZIP, which is the part that matters and
   the part that is not cut off. Do not reconstruct the town: `Storrs Ma... 06268`
   is Storrs Mansfield, **Connecticut**, and the fragment reads like a state
   abbreviation for a different one.
6. Close the tab when done.

## Reading the result

Each option carries its own cost, date and condition. State all three, per
option — a date without its condition is not an answer.

| Signal | Meaning |
| --- | --- |
| `when: "Tomorrow, …"` / `"Overnight 4 AM - 8 AM"` | A real promise, this ZIP, this hour |
| `when: "<date> - <date>"` | **Not a promise.** An estimate, typically weeks. With no Prime badge it is the strongest tell of a direct-from-overseas seller |
| `cost: "FREE"` + `condition` set | Free only above that basket total. Not free for a single cheaper item |
| `cost: "$5.85"` | A real fee. Add it to the item price before comparing |
| `cost: "fastest"` | An upgrade whose fee the listing does not state. Say it is unpriced until checkout |
| `program: "paid_shipping"` | The programme, **not** the outcome — it appears alongside `cost: "FREE"`. Read `cost` |
| `cutoff` set | The promise expires. Quote it with the date, and with the time you read it |

An empty option list means the structured block is absent on that listing, not
that there is no delivery. Fall back to `#deliveryBlockMessage` and say so.

## If you must read a rendered page instead

Ask `find` for the delivery date **in the main buy box only, not sponsored or
related items** — without that qualifier it returns an "Overnight" badge
belonging to a sponsored product further down the page and presents it as the
answer. Do not pull the whole page text for one field.

## Related

- [reference/delivery.md](../../reference/delivery.md) — the option contract, and the anonymous/signed-in comparison in full
- [reference/fetch-routes.md](../../reference/fetch-routes.md)
- `amazon-listing-check` — cheaper, and enough for the standard Prime date
- `amazon-account-import` — writes the Prime state to config instead of re-reading it
