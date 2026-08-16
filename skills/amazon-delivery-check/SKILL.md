---
name: amazon-delivery-check
description: Get the real Amazon.com delivery date for one or more ASINs from the user's signed-in browser session, including Prime and overnight options, plus coupons and Prime-exclusive pricing that anonymous fetches cannot see. Use when the user asks when something would arrive, whether it arrives before a date, what it actually costs at checkout, or when an arrival date decides the purchase.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Read
---

# Amazon delivery check

Four facts exist only in a signed-in session: the Prime arrival date, the
overnight cut-off, coupon checkboxes, and Prime-exclusive pricing. Everything
else should come from `amazon-listing-check`, which is cheaper.

## Why this is not optional when timing matters

The anonymous route returns the free-shipping-over-$35 promise, not the Prime
one. Measured on a seven-ASIN shortlist: anonymous said `Friday, August 21` for
every row, while the signed-in session said `Tomorrow, August 17` for five of
them and offered an overnight 4–8 AM slot on three. A four-day error, always in
the direction that loses the sale.

So: use the anonymous date as the worst case. Come here when the answer decides
something.

## Batch the whole shortlist in one call

Do not navigate once per ASIN. From a tab already on any `amazon.com` page, a
same-origin `fetch` carries the session, so one `javascript_tool` call prices the
entire shortlist:

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

This is faster than navigating, keeps 400 KB pages out of context, and avoids a
real hazard — see below.

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
3. Run the batch script above.
4. Confirm `shipTo` before quoting anything. It renders **truncated**, as
   `<Town na...> <ZIP>` — so check the ZIP, which is the part that matters and
   the part that is not cut off. If it is not the user's address, stop and say
   so; do not quote a date for somewhere else.
5. Close the tab when done.

## Reading the result

The delivery string carries several separate facts. Split them:

| Form | Meaning |
| --- | --- |
| `Tomorrow, <date>` / `Overnight 4 AM - 8 AM` | A real promise, this ZIP, this hour |
| `FREE delivery <weekday>, <date>` | A specific day |
| `<date> - <date>` range | **Not a promise.** An estimate, typically weeks. With no Prime badge it is the strongest tell of a direct-from-overseas seller |
| `on orders shipped by Amazon over $35` | Conditional on basket total. Not free for a single cheaper item |
| `Order within N hrs` | The promise expires. Quote the cut-off with the date |

State the date, the condition attached to it, and the ZIP it is for. A date
without its condition is not an answer.

## If you must read a rendered page instead

Ask `find` for the delivery date **in the main buy box only, not sponsored or
related items** — without that qualifier it returns an "Overnight" badge
belonging to a sponsored product further down the page and presents it as the
answer. Do not pull the whole page text for one field.

## Related

- [reference/fetch-routes.md](../../reference/fetch-routes.md)
- `amazon-listing-check` — cheaper, for everything that is not date- or account-specific
