---
name: amazon-lists
description: Read the user's Amazon lists from their signed-in session - which lists exist, what is on them, and what those items cost and whether they are in stock right now. Use when the user asks what is on a list, whether something is already saved, what a list would cost to buy, or wants a shortlist checked against a list they already keep. Read-only.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Bash(*/amazon_fetch.py *), Read
---

# Amazon lists

Lists live behind the user's login, so `amazon_fetch.py` cannot reach them - it
is stateless and carries no cookies by design. This is the browser route.

Everything here reads. Adding is `amazon-list-add`.

## The index

```
https://<domain>/hz/wishlist/ls
```

Each list is a link whose path carries its id:

```js
[...document.querySelectorAll('a[href*="/hz/wishlist/ls/"]')]
  .map(a => (a.getAttribute('href').match(/\/hz\/wishlist\/ls\/([A-Z0-9]+)/i)||[])[1])
```

**Discard the id `ref`.** Amazon's own tracking links match the same pattern and
produce a phantom list called `ref` above the real ones. It is not a list; do
not offer it to the user or try to open it.

The left rail carries each list's visibility (`Private`, `Public`, `Shared`) on
the line after its name, and marks one `Default List`. Read visibility before
suggesting anything be added: a Shared list has an audience.

The rail is also truncated - it ends in `Show more lists`. Do not report the
visible set as "all your lists" without expanding it.

## One list's contents

```
https://<domain>/hz/wishlist/ls/<LISTID>
```

Each item is `li[data-itemid]`:

| Want | Where |
| --- | --- |
| ASIN | `JSON.parse(li.dataset.repositionActionParams).itemExternalId` gives `ASIN:B0XXXXXXXX|MERCHANT` |
| Item id | `li.getAttribute('data-itemid')` - needed to remove or move it |
| Price when added | `li.getAttribute('data-price')` |
| Title | `li.querySelector('a[id^="itemName_"]').getAttribute('title')` |
| Date added | `li.querySelector('[id^="itemAddedDate_"]').innerText` |

**Do not read the ASIN out of the item's `href`.** The Claude in Chrome
extension blocks scripts that read link hrefs on this page and substitutes the
string `[BLOCKED: Cookie/query string data]` for the value. A script that parses
that gets nothing, silently, and looks like an empty list rather than an error.
`data-reposition-action-params` carries the same ASIN and is not blocked.

`data-price` is **the price the item was at**, not today's. It is the wrong
number to quote, and the gap between the two is usually why the user is asking.

## Getting current prices

Take the ASINs and hand them to the anonymous route in one call:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing B0AAA B0BBB B0CCC --zip <postcode>
```

Faster than opening each product page, it does not disturb the user's tabs, and
it gets a delivery date for a postcode you chose rather than for whatever the
browser session last resolved to.

## Reporting

Say which list, how many items, and the current total. Flag per item:

- price moved since it was added, in either direction
- no longer buyable, or `Only N left`
- a `check_pack_size` warning from the listing call, which means the item is
  sold in another quantity the user has probably not compared

## Boundaries

Read-only. Do not add, remove, reorder or rename anything, and do not click
`Add to Cart`, `Buy it again` or `Delete` while reading - all three render
inside the same item row.

Close tabs you opened when you are done.
