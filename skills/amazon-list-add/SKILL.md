---
name: amazon-list-add
description: Add a specific product to a named list on the user's signed-in Amazon account - resolve the exact variant first, confirm what is going where, add it, then verify against the list itself. Use when the user says add this to my list, save this for later, or put it on a named list. Requires the user's explicit confirmation of the exact item and list before it adds anything.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Bash(*/amazon_fetch.py *), Read
---

# Amazon list add

The only skill here that writes to a list. Adding is reversible, which makes it
far less dangerous than `amazon-order-cancel` - but adding the *wrong variant*
is not obviously wrong afterwards. It sits on the list looking correct until
someone buys four singles of a thing sold in fives.

So the discipline is: **resolve the variant, confirm it, add once, verify.**

## Resolve the exact ASIN first

An Amazon product page is one cell of a matrix. Every combination of colour,
size and pack count is its own ASIN, and the one the user was looking at is
whichever the link happened to carry.

Before adding anything, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing <ASIN> --zip <postcode>
```

If the result carries `variants.check_pack_size`, **stop and resolve it**. That
warning means the same product exists in another quantity, and it is the single
most expensive mistake available here. Measured on a real cable listing: four
singles at $17.42 came to $69.68 where the five-pack was $47.60.

Narrow options to an ASIN with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" variants <ASIN> --pick "Style=5 Pack" --pick "Color=Blue"
```

Changing an option on Amazon is navigation between ASINs, not configuration of
one. There is nothing to click: pick the ASIN and use it.

## Confirm before adding - always

State back to the user, in plain text:

- the **full title** of the resolved ASIN, and the ASIN itself
- its variant values, when the listing has options
- the current price, and the postcode that price was read for
- the **list name and its visibility** - `Private`, `Public` or `Shared`

Then wait for a clear yes. A yes covers that item and that list, and no other.

Confirming visibility is not ceremony. A Shared list has an audience, and the
user may not have that list in mind when they say "my list".

## Which list

Get ids from `amazon-lists`. Never guess an id and never match a list by
substring - `Ethernet Drops` and `Ethernet Wall Upgrade` both match `Ethernet`,
and they are different lists with different visibility.

If the user's words match more than one list, ask. If they match none, say so
and offer the ones that exist; do **not** fall back to the default list.

## The add

Navigate to the resolved ASIN, pinning the variant:

```
https://<domain>/dp/<ASIN>?th=1&psc=1
```

Then open the list picker and click the target list directly:

| Control | Selector | What it does |
| --- | --- | --- |
| List picker | `#wishListDropDown` | Opens the menu. Safe. |
| A specific list | `#atwl-link-to-list-<LISTID>` | **Adds to that list.** |
| Add to List | `#wishListMainButton` | Adds to the **default** list |

**Never click `#wishListMainButton`.** It adds to whatever list Amazon considers
default, which is generally not the one that was just confirmed, and it gives no
prompt.

Each entry in the open menu carries its list id in its element id, so the target
is exact:

```js
document.querySelector('#atwl-link-to-list-2R4CWUKVGERM4')
```

Use `find` to get element refs and click those. Do not click by coordinate: the
list picker sits directly beside `Add to Cart` and `Buy Now` in the same button
stack, and a coordinate that drifts by a row buys something.

A JavaScript `.click()` on `#wishListDropDown` does **not** open the menu -
Amazon's declarative handler does not fire for it, and the popover renders
empty. Nor does a dispatched `MouseEvent` sequence (`pointerdown`, `mousedown`,
`pointerup`, `mouseup`, `click`, all `bubbles:true`); the handler only responds
to a genuinely trusted click. Use the `computer` tool on a ref from `find`.

**The dropdown click is unreliable, and this is the main thing to plan for.**
Measured over six consecutive adds on one account, roughly half the first
clicks failed to open the menu, with no error and no visible change. Retrying
sometimes worked and sometimes did not, on the same ASIN, seconds apart.
`scroll_to` before the click made no difference either way.

So: after clicking, **always** check that the menu opened before assuming
anything:

```js
[...document.querySelectorAll('[id^="atwl-link-to-list-"]')].length
```

Zero means the menu never opened and **nothing was added**. Do not report the
item as added. Retry once; if it fails again, stop and tell the user which
ASINs did not get added, with their `/dp/` links, rather than looping. This
failure is in Amazon's UI, not in the request, and hammering it does not help.

Once the entries exist, a JavaScript `.click()` on the list link **does** work -
that half is reliable. It is only opening the menu that is flaky.

Never fall back to `#wishListMainButton` when the dropdown will not open. It
adds to the default list, which is not the list that was confirmed.

## Verify

The inline confirmation is not a signal at all. Both `#atwl-inline-sucess-msg`
and `#atwl-inline-error-msg` are pre-rendered templates that **always carry
text** - a successful add returns "Added to" and "Unable to add item to List.
Please try again." simultaneously, with the container not even visible. Reading
either one tells you nothing. Re-read the list:

```
https://<domain>/hz/wishlist/ls/<LISTID>
```

Parse `li[data-itemid]` as described in `amazon-lists` - via
`data-reposition-action-params`, never the blocked `href`.

If verification does not find it, say exactly that: the click was made, the
inline message said what it said, and the list does not show it yet. Give the
list URL so the user can look. **Do not click add again** - the likeliest cause
is that it did work and the page is stale, and a retry produces a duplicate.

## Out of scope

Removing items, moving between lists, changing quantity or priority, creating a
list, and buying anything. Never open a cart or checkout URL, and never touch
`#add-to-cart-button` or `#buy-now-button`.

Close tabs you opened when you are done.
