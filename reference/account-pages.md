# The signed-in account pages: orders and addresses

Measured 2026-08-20 on `amazon.com`, signed in, US account. Everything here is a
selector or a route contract, and Amazon re-skins account pages more often than
the storefront — so treat a mismatch as a page change, re-measure, and edit this
file with the new date rather than working around it in a skill.

## Routes

| Page | Canonical path | Aliases that serve the same page |
| --- | --- | --- |
| Address book | `/a/addresses` | `/gp/css/account/address/view.html` |
| Edit one address | `/a/addresses/edit?addressID=<id>` | — |
| Add an address | `/a/addresses/add` | — |
| Order history | `/your-orders/orders` | `/gp/css/order-history`, `/gp/your-account/order-history` |
| One order | `/your-orders/order-details?orderID=<order-id>` | — |
| Cancel an order | `/progress-tracker/package/preship/cancel-items?orderID=<order-id>` | — |
| Cancellation outcome | `/progress-tracker/package/preship/cancel-summary?…` | — |

`ref_=` on any of these is navigation tracking. Drop it.

The two address paths are **not** a redirect pair — both return HTTP 200 at their
own URL with a byte-identical 426 KB body and `finalUrl` unchanged. Either works;
prefer `/a/addresses`. This settles an open question from the previous session,
which guessed one was a redirect target.

## The dividing line: one page fetches, the other does not

This is the single most important fact about these two pages, and they look
identical from the outside.

| | Address book | Order history |
| --- | --- | --- |
| Same-origin `fetch` returns | HTTP 200, 426 KB, **data present** | HTTP 200, 934–957 KB, **data absent** |
| Usable without navigating | **Yes** | **No** |

The order-history page ships `.order-card.js-order-card` elements that are
**empty shells** — one child, ~200–280 bytes of HTML, `textContent.length === 0`.
The cards are filled client-side. So a fetched order-history page gives you:

- `document.querySelectorAll('.order-card').length === 10` — a plausible count
- zero order dates, zero totals, zero order numbers
- no `Order placed` and no `Ship to` anywhere in the body text
- zero `a[href*="order-details"]`
- nine `/dp/` links, which belong to **recommendation carousels, not orders**

Every one of those is the shape of a working extractor finding an empty account.
The previous session's note that "`.order-card` returns 10 on the first page" was
this: counting shells and concluding the data was there. Changing the path does
not help — `/your-orders/orders`, `/gp/css/order-history` and
`/gp/your-account/order-history` all behave the same way.

**Order history therefore requires a rendered tab**, which means accepting the
navigation hazard in [delivery.md](delivery.md) rather than dodging it. The
address book does not; read it with a fetch and never navigate.

`timeFilter` *is* honoured server-side on a fetch — the response shrinks from 934
KB to 768 KB for `timeFilter=year-2026` — which is another way to get a confident
wrong answer, because the parameter working proves nothing about the cards.

## Address book: the field contract

### The first tile is not an address

```
.address-tile                        7 matches
  .first-desktop-address-tile        the "Add address" card — textContent "Add address"
  .normal-desktop-address-tile       6 real addresses
```

Count `.normal-desktop-address-tile`, or `[id^="ya-myab-display-address-block-"]`.
Counting `.address-tile` overstates the book by exactly one, every time.

### The field IDs are duplicated, and `querySelector` returns the wrong address

Each field ID appears **twice per address** — once for each responsive layout —
so with six addresses the page carries twelve nodes with `id="address-ui-widgets-FullName"`:

```
address-ui-widgets-FullName            x12
address-ui-widgets-AddressLineOne      x12
address-ui-widgets-CityStatePostalCode x12
address-ui-widgets-Country             x12
address-ui-widgets-PhoneNumber         x12
address-ui-widgets-AddressLineTwo      x4    (only where line 2 is set)
```

`document.getElementById('address-ui-widgets-FullName')` and
`document.querySelector('#address-ui-widgets-FullName')` both return the **first**
node in the document — block 0's value — for every address you ask about. There
is no error and the value is a real address, just not the one requested.

Always scope to the block:

```js
const block = d.querySelector('#ya-myab-display-address-block-' + i);
const f = name => block.querySelector('#address-ui-widgets-' + name)?.textContent.trim();
```

This is the same duplicate-for-layout artefact as the `Sold by X ... Sold by X`
repeat in [verification-traps.md](verification-traps.md), with a worse failure
mode: there it produced a redundant string, here it produces someone else's flat.

### Display fields

Read from within `#ya-myab-display-address-block-<i>`:

| Field | ID suffix on `address-ui-widgets-` |
| --- | --- |
| Name | `FullName` |
| Street | `AddressLineOne`, `AddressLineTwo` |
| City / state / postcode, one string | `CityStatePostalCode` |
| Country | `Country` |
| Phone | `PhoneNumber` |

`CityStatePostalCode` is **one field**, rendered `Town Name, ST 12345-6789`. The
postcode is the trailing token; take it with a country-shaped pattern, not by
splitting on commas — the town name contains one in several countries.

`PhoneNumber` renders with a label prefix and Unicode directional marks around
the digits (`U+202A` … `U+202C`). Strip `Phone number:` and `[‎‪-‬]`
before storing, or the value round-trips into config with invisible characters
that will not compare equal to anything.

### Which one is the default

Exactly one block contains `[id*="default-shipping"]`
(`#ya-myab-default-shipping-address-icon`). Verified: 1 of 6 blocks. Its
`textContent` is empty — it is an icon, so test for presence, never for text.

### Controls

| Control | Selector | Target |
| --- | --- | --- |
| Edit | `a#ya-myab-address-edit-btn-<i>` | `GET /a/addresses/edit?addressID=<id>` |
| Remove | `a#ya-myab-address-delete-btn-<i>` | `href="#"` — opens `#a-popover-deleteAddressModal-<i>` |

Remove is **not a link**. It opens a modal whose confirm submits
`POST /a/addresses/delete` with `addressID` and `isStoreAddress`. Nothing in this
plugin should build that request.

`addressID` is a 64-character opaque token. It is a durable handle to a physical
address and it does not belong in `addresses.yaml`, in a transcript, or in a
commit. Resolve it fresh from the page each time.

### The edit form is a different ID namespace

The display IDs and the form IDs are **not the same names**, and a selector from
one silently returns nothing on the other:

| Display | Edit form |
| --- | --- |
| `address-ui-widgets-AddressLineOne` | `address-ui-widgets-enterAddressLine1` |
| `address-ui-widgets-CityStatePostalCode` | `address-ui-widgets-enterAddressCity` + `-enterAddressStateOrRegion-dropdown-nativeId` + `-enterAddressPostalCode` |
| `address-ui-widgets-FullName` | `address-ui-widgets-enterAddressFullName` |
| `address-ui-widgets-PhoneNumber` | `address-ui-widgets-enterAddressPhoneNumber` |

Full form on `/a/addresses/edit` and `/a/addresses/add`:

```
input  #addressID                                             (hidden, edit only)
select #address-ui-widgets-countryCode-dropdown-nativeId
input  #address-ui-widgets-enterAddressFullName
input  #address-ui-widgets-enterAddressPhoneNumber
input  #address-ui-widgets-enterAddressLine1
input  #address-ui-widgets-enterAddressLine2
input  #address-ui-widgets-enterAddressCity
select #address-ui-widgets-enterAddressStateOrRegion-dropdown-nativeId   (63 options, US)
input  #address-ui-widgets-enterAddressPostalCode
input  #address-ui-widgets-urbanization                       (Puerto Rico only)
input  #address-ui-widgets-use-as-my-default                  (checkbox)
span   #address-ui-widgets-form-submit-button                 "Update address"
form   action="/a/addresses/edit" method="post"
```

State is a `<select>`, not free text — 63 options on the US storefront (states,
DC, territories and military posts). Typing `Connecticut` into it does nothing.
Set `.value` to the option value and dispatch `change`, or the form submits the
previous state with no visible complaint.

`#address-ui-widgets-form-submit-button` is a `<span>` — Amazon's `a-button`
wrapper — not a `<button>`. A `[type=submit]` selector will not find it, and will
find the site-search "Go" button instead.

## Order history: the field contract

Only from a **rendered tab**. See the dividing line above.

### Cards and their fields

```js
const cards = [...document.querySelectorAll('.order-card')];
```

| Field | How |
| --- | --- |
| Order placed | caps-label lookup, `order placed` |
| Total | caps-label lookup, `total` |
| Order # | caps-label lookup, `order #` |
| Recipient | `.yohtmlc-recipient` |
| Status | `.yohtmlc-shipment-status-primaryText` |
| Status detail | `.yohtmlc-shipment-status-secondaryText` |
| Product titles | `.yohtmlc-product-title` (one per line item) |
| ASINs | `a[href*="/dp/"]` within the card |

The header labels and their values live in the **same row**, not in a
label/value element pair — `Order placed August 19, 2026` is one string. A
two-children lookup returns `null` for all of them, which is how the previous
session concluded the labels "are probably composed differently than they
render". They are not: they are concatenated.

```js
const clean = s => (s||'').replace(/[ ‎‪-‬]/g,' ').replace(/\s+/g,' ').trim();
const field = (card, label) => {
  for (const el of card.querySelectorAll('.a-text-caps')) {
    if (clean(el.textContent).toLowerCase() !== label) continue;
    const box = el.closest('.order-header__header-list-item') || el.closest('.a-column') || el.parentElement;
    return clean(box.textContent).replace(new RegExp('^' + label + '\\s*', 'i'), '');
  }
  return null;
};
```

Verified 10/10 cards for `order placed`, `order #` and status.

### A missing total means cancelled, not a broken selector

6 of 10 cards returned a total. The four that did not were **all** `Cancelled`,
and a cancelled card carries only two caps labels:

| Card state | Caps labels present |
| --- | --- |
| Live order | `Order placed`, `Total`, `Ship to`, `Order #` |
| Cancelled | `Order placed`, `Order #` |

So `total === null` and `ship to === null` are **data**, not extraction failures.
Read the status before reporting either as missing.

### ASINs are per-order and usable

`a[href*="/dp/"]` inside a card returns that order's own ASINs — one card had two
line items and returned both, matching its two `.yohtmlc-product-title` nodes.
This answers "have I bought this before" directly, and it is the highest-value
question the page answers.

It only holds **inside a card**. The same selector against `document` picks up
recommendation carousels, which is what the fetched page's nine `/dp/` links were.

### Pagination and filtering

```
/your-orders/orders?timeFilter=<filter>&page=<n>
```

`page` is 1-indexed. It is **not** `startIndex`. Ten cards per page; the account
measured showed 19 pages under the default filter.

`timeFilter` values, read off `#time-filter`:

```
last30  months-3  year-2026  year-2025 … year-2015
```

The list of years is account-specific — it starts at the first year the account
ordered. Read the options rather than constructing `year-YYYY` for an arbitrary
year.

`#searchOrdersInput` is the in-page order search.

### An empty page does not say it is empty

`?timeFilter=year-2025&page=2` on the measured account rendered:

- `.order-card` — **0**
- no "no orders" message anywhere in the body
- `.a-pagination` — **absent**
- `#time-filter` — correctly showing `year-2025`, so the filter was applied

Zero cards is therefore ambiguous between *this filter has no orders*, *this page
number overshoots the range*, and *the cards had not rendered yet*. The filter
being correctly selected proves the request worked, not that the answer is empty.

Distinguish before reporting: absence of `.a-pagination` alongside zero cards
means there is nothing beyond page 1 for this filter, so re-read page 1. Never
report "you have no orders in 2025" off a page-2 result.

## Order details, and cancellation

Exercised end to end on 2026-08-20 against a real order the user created for the
purpose, and cancelled with their explicit authorisation.

### The order-details page

`/your-orders/order-details?orderID=<order-id>` is server-rendered enough to read
the header — order number, placed date, ship-to, payment method, order summary —
but the shipment box carries the same `yohtmlc-*` hooks as an order card.

**`a[href*="/dp/"]` against `document` is wrong here.** The page ends in `Pick up
where you left off` and `Buy it again` carousels, so a document-wide ASIN sweep
on a **one-item** order returned five ASINs, none of which was the item ordered.
Scope to the shipment box, exactly as on the order card.

### The cancel route, and why a stray navigate once landed on it

`/progress-tracker/package/preship/cancel-items?orderID=<order-id>` is the target
of the **Cancel items** button on the order-details page. This is the page an
unexplained navigate landed on in an earlier session — see the navigation hazard
in [delivery.md](delivery.md). It is not a page Amazon serves at random: it is
one link away from any live order, and the plugin reached it by following that
link. The hazard is real; its cause is now known.

The button's DOM id is `a-autoid-7-announce`. **Never key on that** — `a-autoid-N`
is assigned in document order at render time and shifts when anything above it
changes. The stable anchor is the href:

```js
document.querySelector('a[href*="preship/cancel-items"]')
```

Its absence is also a signal: on an order that cannot be cancelled — already
cancelled, already shipped — the link is simply gone.

### The cancel form

| Control | How to find it |
| --- | --- |
| Per-item checkbox | one `input[type=checkbox]` per line item |
| Select all / Clear | link above the item list; text flips to `Clear` once anything is ticked |
| Cancellation reason | a `<select>`, **optional** |
| Submit | button `Request cancellation`, inert until an item is ticked |

Cancellation is **per item, not per order**. A multi-item order requires ticking
each item, and cancelling one item leaves the rest live.

**Do not reach for the cancellation reason with `document.querySelector('select')`.**
That returns `#searchDropdownBox`, the nav bar's department picker — 40-plus
options beginning `All Departments`, on every Amazon page. It looks exactly like
a populated dropdown and it is not this one. Find the reason select by its label.

### Reading the outcome

Submitting redirects to:

```
/progress-tracker/package/preship/cancel-summary
    ?orderID=<order-id>
    &cancelGuid=<uuid>
    &displayableCancelHeading=Cancellation%2520successful
    &cancelMessageType=SUCCESS
```

`cancelMessageType` is the machine-readable outcome. `displayableCancelHeading`
arrives **double-encoded** — `%2520` is `%20` re-escaped — so it reads as
`Cancellation%20successful` after one decode and needs a second pass.

The summary page renders a per-item status heading; the item cancelled here read
`Cancelled`.

### Verify against the order, not the redirect

The button says **Request cancellation**, and for an order far enough into
fulfilment a request is not a guarantee. `cancelMessageType=SUCCESS` is a URL
parameter on a page Amazon redirected you to — good evidence, but it is a signal,
not the thing. Re-read the order afterwards.

On a cancelled order, `/your-orders/order-details` **collapses**: the ship-to
block, the payment method, the order summary and the whole shipment box are gone,
replaced by a single notice. So:

- `.yohtmlc-shipment-status-primaryText` returns **empty**, not `Cancelled`;
- `a[href*="preship/cancel-items"]` is **absent**;
- the body carries `This order has been cancelled.`

Test for the notice text and the missing cancel link. Do **not** test with a bare
`/cancell?ed/i` against `document.body.innerText` — that matches the nav
department list on every Amazon page, cancelled or not, and returned a confident
true here on wording lifted straight out of the site chrome.

In order history the same order reports status `Cancelled` and, per the card
contract above, drops its `Total` and `Ship to` labels.

## Reading these pages without tripping the extension

Both pages carry session identifiers and CSRF tokens inline. Three things get a
whole tool result blocked as cookie/query-string data, all observed on 2026-08-20:

- reading `outerHTML` of a form or a control;
- listing form `input` elements including their values;
- returning `location.search`, or any href with its query string attached.

Strip `script`, `style` and `noscript` first, return attribute **names** rather
than values, split hrefs on `?` and return the path plus the parameter keys. When
a result is blocked, nothing partial comes back — the whole call is lost, so the
cheap habit is to never put a raw token-bearing string in the return value.
