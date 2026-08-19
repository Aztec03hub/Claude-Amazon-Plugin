---
name: amazon-order-history
description: Query the user's Amazon order history from their signed-in session - when something was bought, what it cost, what is arriving this week, whether an ASIN has been ordered before, and what the current status of an order is. Use when the user asks have I bought this before, when did I order that, what is arriving, how much did I pay for it, or what happened to an order. Read-only; to cancel an order use amazon-order-cancel.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Read
---

# Amazon order history

The question this page answers best is **"have I bought this before"**, because
every order card carries its own ASINs. Repeat-purchase, price-paid and
what-is-arriving all fall out of the same read.

Read-only. This skill never cancels, returns, reorders or changes an address.

## This page does not fetch

Everywhere else in this plugin, a same-origin `fetch` beats navigating. **Not
here.** Order history ships its cards as empty shells and fills them client-side,
so a fetch returns HTTP 200, ~950 KB, ten `.order-card` elements and no order
data at all — a textbook success-shaped failure. Details and measurements in
[reference/account-pages.md](../../reference/account-pages.md).

So this skill accepts the navigation hazard rather than dodging it:

1. `tabs_context_mcp` first; create a **new** tab, do not reuse the user's.
2. Navigate to `https://<domain>/your-orders/orders`.
3. **Check `location.pathname` before reading.** A navigate inside a signed-in
   session has landed somewhere unrequested before. If it did, click nothing —
   open a fresh tab.
4. Read with `javascript_tool`.
5. Close the tab.

Click nothing on this page. Every card carries live controls — `Cancel items`,
`Return or replace`, `Buy it again` — and a stray click on any of them acts on a
real order.

Get the domain from `amazon-marketplace-config`; the address book and order
history are per-storefront, so `amazon.co.uk` and `amazon.com` are two reads.

## The extractor

```js
const clean = s => (s||'').replace(/[ ‎‪-‬]/g,' ').replace(/\s+/g,' ').trim();
const field = (card, label) => {
  for (const el of card.querySelectorAll('.a-text-caps')) {
    if (clean(el.textContent).toLowerCase() !== label) continue;
    const box = el.closest('.order-header__header-list-item') || el.closest('.a-column') || el.parentElement;
    return clean(box.textContent).replace(new RegExp('^' + label + '\\s*','i'), '');
  }
  return null;
};
const rows = [...document.querySelectorAll('.order-card')].map(c => ({
  placed:  field(c, 'order placed'),
  total:   field(c, 'total'),
  orderId: field(c, 'order #'),
  status:  clean(c.querySelector('.yohtmlc-shipment-status-primaryText')?.textContent),
  detail:  clean(c.querySelector('.yohtmlc-shipment-status-secondaryText')?.textContent),
  items:   [...c.querySelectorAll('.yohtmlc-product-title')].map(t => clean(t.textContent)),
  asins:   [...new Set([...c.querySelectorAll('a[href*="/dp/"]')]
             .map(a => (a.getAttribute('href').match(/\/dp\/([A-Z0-9]{10})/)||[])[1]).filter(Boolean))],
}));
JSON.stringify({page: 1, n: rows.length, rows}, null, 1)
```

The header label and its value are **one string** in one row — `Order placed
August 19, 2026` — not a label element beside a value element. That is why the
lookup strips the label prefix rather than reading a sibling. Verified 10/10
cards.

`asins` must be scoped **inside the card**. The same selector against `document`
returns recommendation carousels; on a fetched page those nine carousel links
were the only `/dp/` links present, and on a one-item order-details page a
document-wide sweep returned five ASINs, none of them the item ordered.

## Reading the result

| Signal | Meaning |
| --- | --- |
| `total: null` **and** `status: "Cancelled"` | The order was cancelled. Cancelled cards carry only `Order placed` and `Order #` — the missing total is data, not a parse failure |
| `total: null` and status is anything else | A genuine extraction failure. Say so; do not report the order as free |
| `status: "Arriving tomorrow"` | A live promise |
| `status: "Now arriving today 5:15 PM - 7:15 PM"` | A narrowed same-day window, more recent than the original promise |
| Several `items` on one card | One order, several line items — the `total` is for the whole card, not per item |

Never divide a card total across its line items to price one of them. The card
total includes tax and shipping for the order.

## Paging and filtering

```
/your-orders/orders?timeFilter=<filter>&page=<n>
```

`page` is 1-indexed, ten cards per page. It is **not** `startIndex`.

`timeFilter` takes `last30`, `months-3`, or `year-YYYY`. Read the real list off
`#time-filter` rather than constructing a year — the options start at the first
year the account ordered, and a year before that is not offered.

```js
[...document.querySelectorAll('#time-filter option')].map(o => o.value)
```

Each page is a fresh navigate. Budget accordingly: "have I ever bought X" over a
ten-year account is dozens of page loads, so ask the user for a time window
before sweeping, or use `#searchOrdersInput` instead.

### Zero cards does not mean zero orders

An out-of-range page renders **no cards, no message and no `.a-pagination`**,
with `#time-filter` still correctly showing the filter you asked for. The filter
being applied proves the request worked; it says nothing about whether the answer
is empty.

Before reporting "no orders":

- confirm `.a-pagination` is present, or that you are on page 1;
- re-read page 1 for that filter;
- say which filter and which page the answer came from.

Reporting "you have no orders in 2025" off a page-2 result is the failure this
warning exists to prevent.

## What to report, and what not to

Answer the question asked. Do not dump the order history.

Order numbers, totals and recipient names are all on this page. Quote an order
number only when the user needs it to act — a cancellation, a return, a support
call. Do not echo recipient names or ship-to addresses into the transcript, and
do not write any of it to disk: nothing in this skill writes to
`addresses.yaml` or anywhere else.

For a price paid, state the date alongside it. An Amazon price from eleven months
ago is not evidence about today's price — `amazon-listing-check` is.

## Related

- [reference/account-pages.md](../../reference/account-pages.md) — the measured contract for this page
- `amazon-order-cancel` — the write path, for cancelling
- `amazon-listing-check` — what a thing costs *now*, versus what it cost then
- `amazon-marketplace-config` — which storefront to read
