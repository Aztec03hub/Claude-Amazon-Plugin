# Planned: an account-state skill (order history + address book)

**Status:** not started. Deferred from the 2026-08-19 session, which was spent on
delivery options and pricing. Written so the next session starts from the
findings rather than the beginning.

## What was asked for

A skill covering two signed-in account pages:

| Page | URL |
| --- | --- |
| Order history | `https://www.amazon.com/gp/css/order-history?ref_=nav_AccountFlyout_orders` |
| Shipping addresses | `https://www.amazon.com/a/addresses?ref_=ya_d_l_addr` |

The `ref_=` parameters are navigation tracking and can be dropped; the canonical
paths are `/gp/css/order-history` and `/a/addresses`.

## What is already known about these pages

Measured 2026-08-19 on `amazon.com`, signed in, via same-origin `fetch` with
`credentials:'include'` from a tab already on the domain — the read-only
technique described in `amazon-delivery-check`.

- **`/gp/css/order-history`** — HTTP 200, ~980 KB, **server-rendered**. Title
  `Your Orders`. `document.querySelectorAll('.order-card')` returns 10 on the
  first page. No `data-testid` attributes anywhere; the `cel_widget_id` values
  present are navigation and ad placements only, so neither of the anchors used
  elsewhere in this plugin applies here. Selector work is still to do — a first
  attempt at locating the `ORDER PLACED` / `TOTAL` / `SHIP TO` labels by leaf-node
  text found none of them, so the labels are probably composed differently than
  they render. Start by dumping one `.order-card` subtree.
- **`/a/addresses`** — HTTP 200, ~436 KB. The older path
  `/gp/css/account/address/view.html` also returns 200 (~444 KB) and may be a
  redirect target rather than a separate page; check which one actually carries
  the address list before writing either into a skill.
- Both were reachable without navigating, so neither needs the risky
  in-session `navigate` documented in `amazon-delivery-check`.

## Constraints the skill must respect

- **Read-only.** No cancelling, no returning, no reordering, no address edits.
  The order-history page sits one click from controls that cancel live orders —
  this plugin has already had a stray navigate land on
  `/progress-tracker/package/preship/cancel-items`.
- **Strip `script`, `style` and `noscript` before reading `textContent`** from a
  parsed document, or the page's inline JSON — including session identifiers —
  lands in context and the Chrome extension blocks the whole tool result as
  cookie data. See `reference/verification-traps.md`.
- **The address book is already owned by `procurement-tools`**
  (`addresses.yaml`). `amazon-account-import` reads and amends that store; a new
  skill must do the same rather than forking it. Two copies of an address is how
  a delivery date gets quoted for last year's flat.
- **Nothing sensitive gets written to disk or echoed into the transcript**:
  no card digits, no gift-card balances, no full street lines, no order totals
  tied to named recipients. `amazon-account-import` already sets this bar.

## Open questions to settle first

1. Does this belong in `amazon-account-import`, which already claims the address
   book and the default ship-to, or is order history a distinct enough job to
   earn its own skill? Order history is a *query* surface ("when did I buy this",
   "have I bought this before", "what is arriving this week") while
   account-import is a *configuration* surface. That argues for a separate skill
   and for account-import keeping addresses.
2. What is the pagination contract on order history — a year selector, a
   `startIndex`, or infinite scroll? Only the first page was fetched.
3. Is there a per-order ASIN list in the markup? If so, "have I bought this
   before" becomes cheap, and it is the highest-value question the page answers.
