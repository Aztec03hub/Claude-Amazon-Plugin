---
name: amazon-list-add
description: Add a specific product to a named list on the user's signed-in Amazon account - resolve the exact variant first, confirm what is going where, add it, then verify against the list itself. Use when the user says add this to my list, save this for later, or put it on a named list. Requires the user's explicit confirmation of the exact item and list before it adds anything.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Bash(*/amazon_fetch.py *), Read
---

# Amazon list add

The only skill here that writes to a list.

**Do not drive the Add to List button.** Post to the endpoint instead. The
reason is in "Why not the button" below, and it is not a style preference: the
button approach put an item on the wrong list during development.

## Resolve the exact ASIN first

An Amazon product page is one cell of a matrix. Every combination of colour,
size and pack count is its own ASIN, and the one the user was looking at is
whichever the link happened to carry.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing <ASIN> --zip <postcode>
```

If the result carries `variants.check_pack_size`, **stop and resolve it**. That
warning means the same product exists in another quantity. Measured on a real
cable listing: four singles at $17.42 came to $69.68 where the five-pack was
$47.60.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" variants <ASIN> --pick "Style=5 Pack"
```

## Confirm before adding

State the full title, the ASIN, its variant values, the current price with the
postcode it was read for, and the **list name and visibility**. Wait for a clear
yes. A Shared list has an audience, and the user may not have that list in mind
when they say "my list".

Get list ids from `amazon-lists`. Never match a list by substring: `Ethernet
Drops` and `Ethernet Wall Upgrade` both match `Ethernet` and have different
visibility. If the user's words match more than one, ask. If none, say so - do
**not** fall back to the default list.

## The add

Navigate to `https://<domain>/dp/<ASIN>?th=1&psc=1`, then post directly:

```js
const LIST = '<LISTID>';                       // explicit, never implied
const asin = document.querySelector('#ASIN').value;
const oli  = document.querySelector('#offerListingID').value;
const sid  = document.querySelector('#session-id').value;
const csrf = document.querySelector('#lists-sp-csrf-form-token').value;

if (asin !== '<EXPECTED_ASIN>') throw new Error('wrong page: ' + asin);

const body = new URLSearchParams({
  listExternalId: LIST, asin, offerListingId: decodeURIComponent(oli),
  quantity: '1', type: 'wishlist', listType: 'WishList',
  sid, clientName: 'atwl-desktop'
});

const res = await fetch('/hz/wishlist/additemtolist?ie=UTF8', {
  method: 'POST', credentials: 'include',
  headers: {
    'anti-csrftoken-a2z': csrf,
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest'
  },
  body: body.toString()
});
```

Always assert the ASIN on the page matches the one you intend to add before
posting. The page can redirect to a different variant, and a silent mismatch is
how the wrong thing lands on the list looking right.

Take the CSRF token from `#lists-sp-csrf-form-token`. The page carries several
`anti-csrftoken-a2z` inputs and the others belong to cart and creator widgets.

`listExternalId` is required and explicit, so this **cannot** reach the default
list. That is the whole point.

## Why not the button

The product page's Add to List control is a split button: `#wishListMainButton`
(adds to the **default** list, no prompt) and `#add-to-wishlist-button`
(`data-action="atwl-splitbutton-arrow"`, opens the picker). They are adjacent,
about 13px apart, and **both live inside the same form as `#add-to-cart-button`
and `#buy-now-button`**.

Amazon reflows detail pages as images and ad slots resolve. A coordinate
measured one moment lands somewhere else the next: measured at (1645, 499) with
`scrollY: 399`, the page then scrolled to top and the click hit the main button,
adding to the default list. A `MutationObserver` over a failed attempt recorded
**zero DOM activity in 25 seconds** - the clicks were not landing at all, which
is why the failures looked random rather than slow.

Settling the layout first (poll `getBoundingClientRect` until stable, assert
`elementFromPoint`) removes the wrong-list risk but still does not open the
picker reliably. Roughly half of attempts did nothing. A synthetic `MouseEvent`
sequence does not work either; only a trusted click does.

The endpoint has none of these problems.

## Verify

The inline confirmation is worthless: `#atwl-inline-sucess-msg` and
`#atwl-inline-error-msg` are pre-rendered and **both always carry text**, so a
successful add reports "Added to" and "Unable to add item to List" at the same
moment, with the container invisible.

A `200` from the endpoint is also not proof. Re-read the list:

```
https://<domain>/hz/wishlist/ls/<LISTID>
```

Parse `li[data-itemid]` as in `amazon-lists` - via
`data-reposition-action-params`, never the blocked `href`.

**Check the default list too.** Read its item count before and after. If it
grew, something went to the wrong place and the user needs to know immediately.

If the ASIN is not on the target list, say so plainly and give the list URL. Do
not retry blindly.

## Out of scope

Removing items, moving between lists, changing quantity or priority, creating a
list, and buying anything. Never open a cart or checkout URL, and never touch
`#add-to-cart-button` or `#buy-now-button` - both are in the same form as the
control this skill deliberately avoids.

Close tabs you opened when you are done.
