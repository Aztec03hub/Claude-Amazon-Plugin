---
name: amazon-order-cancel
description: Cancel an order, or individual items within an order, on the user's signed-in Amazon account - find the order, confirm exactly what is about to be cancelled, submit the cancellation and verify it actually took effect against the order itself. Use when the user says cancel that order, cancel the X I just bought, or stop that delivery. Requires the user's explicit confirmation of the specific order before submitting.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__tabs_close_mcp, Read
---

# Amazon order cancel

The only skill in this plugin that changes the state of a real order. Everything
else here reads.

Cancelling is not reversible. An order cancelled by mistake cannot be
un-cancelled — it has to be placed again, at whatever price and delivery date are
available then, which on a lightning deal or a low-stock item may be neither.

So the discipline is: **identify precisely, confirm explicitly, submit once,
verify independently.**

## Confirm before you submit — always

Never cancel on an inferred antecedent. "Cancel that one" after a list of five
orders is not an instruction, it is an ambiguity.

Before submitting, state back to the user, in plain text:

- the order number;
- the date it was placed;
- **every item that will be cancelled**, by name and price;
- anything in the order that will **not** be cancelled;
- the order total.

Then wait for a clear yes. A yes covers that order and no other; if the user
follows up with a second cancellation, confirm that one too.

If the user names the order unambiguously and up front — an order number, or
"cancel the eraser I ordered yesterday" against exactly one match — you still
show the summary, but one round trip is enough.

## Finding the order

If you have the order number, go straight to it:

```
https://<domain>/your-orders/order-details?orderID=<order-id>
```

Otherwise use `amazon-order-history` to locate it, and match on the item name and
date. Where two orders match, ask — do not take the more recent one.

Read the item names off the **shipment box**, not the page. An order-details page
ends in `Pick up where you left off` and `Buy it again` carousels, and a
document-wide `a[href*="/dp/"]` sweep on a one-item order returned five ASINs,
four of them recommendations. Cancelling on the strength of that reads the wrong
item back to the user.

## Whether it can be cancelled at all

The **Cancel items** control is the test:

```js
document.querySelector('a[href*="preship/cancel-items"]')
```

Present means cancellable. Absent means it is not — already shipped, already
cancelled, or a digital item — and the answer to the user is that Amazon no
longer offers cancellation for this order, with the next option being a refusal
at the door or a return once it arrives. Do not go hunting for another route.

Do **not** key on the button's DOM id. It renders as `a-autoid-7-announce`, and
`a-autoid-N` is assigned in document order at render time: it shifts whenever
anything above it on the page changes.

## The cancel page

```
https://<domain>/progress-tracker/package/preship/cancel-items?orderID=<order-id>
```

Reachable directly by URL, which is more reliable than clicking the button —
the order-details layout reflows and a coordinate click lands on whatever moved
into place. Confirm `location.pathname` after navigating.

This is the page an unexplained navigate landed on in an earlier session, noted
as a hazard in [reference/delivery.md](../../reference/delivery.md). It is one
link from any live order. Now the plugin arrives here deliberately — but the rule
that produced that note still stands everywhere else.

| Control | How to find it |
| --- | --- |
| Per-item checkbox | one `input[type=checkbox]` per line item |
| Select all / Clear | link above the list; flips to `Clear` once anything is ticked |
| Cancellation reason | a `<select>`, optional — locate it by its label |
| Submit | button `Request cancellation`, inert until an item is ticked |

**Cancellation is per item, not per order.** On a multi-item order, ticking one
box cancels one line and leaves the rest live. If the user said "cancel the
order", tick everything and say that you did; if they named one item, tick that
one and say explicitly what remains live.

**Never reach for the reason dropdown with `document.querySelector('select')`.**
That returns `#searchDropdownBox`, the nav bar's department picker, present on
every Amazon page with forty-odd options starting `All Departments`. It looks
like a populated dropdown and it is the wrong element. The reason is optional
anyway — leave it unless the user gave one.

Use `find` to get element refs and click those. Coordinate clicks are fragile
here: the viewport was resized between a screenshot and a click during this
skill's development and the click silently missed, landing on nothing.

## Verifying

Submitting redirects to `/progress-tracker/package/preship/cancel-summary` with
`cancelMessageType=SUCCESS` and a per-item `Cancelled` heading.

**That is a signal, not the thing.** The button says *Request* cancellation, and
`cancelMessageType` is a URL parameter on a page you were redirected to. For an
order further into fulfilment, a request is not a guarantee.

Re-read the order and check it there:

```js
// on /your-orders/order-details?orderID=<order-id>
({
  cancelled: /This order has been cancelled/i.test(document.body.innerText),
  cancelLinkGone: !document.querySelector('a[href*="preship/cancel-items"]'),
})
```

A cancelled order's details page **collapses** — ship-to, payment method, order
summary and the whole shipment box disappear, replaced by one notice. So
`.yohtmlc-shipment-status-primaryText` returns **empty**, not `Cancelled`; do not
read the absence of a status as a failed cancellation.

Do not test with a bare `/cancell?ed/i` against the page text. That matches the
nav department list on every Amazon page and returns true on a live order.

Then close the tab.

## Reporting

Say what was cancelled, what was not, and where the money goes. If the order was
charged, the refund is Amazon's to issue and its timing is not on this page —
say that rather than quoting a date.

If verification did not confirm the cancellation, say exactly that: the request
was submitted, the summary reported success, and the order page does not yet
reflect it. Give the order number so the user can check it themselves. Do not
resubmit.

## Out of scope

Returns, replacements and refund claims on delivered items. Different flow,
different page, and the decision to return is not one to make on inference.

## Related

- [reference/account-pages.md](../../reference/account-pages.md) — the measured cancel flow, end to end
- `amazon-order-history` — finding the order, read-only
- [reference/delivery.md](../../reference/delivery.md) — the navigation hazard this page was the subject of
