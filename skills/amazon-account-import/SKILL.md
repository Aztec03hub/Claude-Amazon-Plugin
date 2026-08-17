---
name: amazon-account-import
description: Fill the user's stored delivery addresses and per-marketplace preferences by reading them out of a signed-in Amazon session — the address book, the default ship-to, Prime membership state and the account's home marketplace — instead of interviewing the user for facts their account already knows. Use when the config is empty or stale, when the user says pull my addresses from Amazon, or after they add an address or start or cancel Prime.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Read, Edit, Write
---

# Amazon account import

The account already holds the delivery addresses, the default ship-to and the
Prime state. Reading them beats asking for them: the user types nothing, and the
values match what Amazon will actually apply at checkout rather than what the
user remembers.

This is the session half of configuration. The interview half is
`/procurement-tools:shop-setup`, which covers what no account knows — deadlines,
luggage limits, where the driver actually goes, which shops are in scope.

## Before you start

1. Find the store: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/user_config.py" path`.
2. Read what is already there: `... show`. **Amend, never overwrite.** The
   existing entries carry hand-written knowledge — access constraints, delivery
   deadlines, tax notes — that is not recoverable from Amazon and that a
   regenerated file would silently drop.
3. Say which marketplace you are importing from. An Amazon login works across
   storefronts but the address book and Prime state are per-marketplace, so
   `amazon.co.uk` and `amazon.com` are two imports, not one.

## Read it, do not click it

Work the way `amazon-delivery-check` does: one tab on any page of the target
domain, then same-origin `fetch` from `javascript_tool`. A plain navigate inside
a signed-in Amazon session has been observed landing on an order-cancellation
page for an unrelated live order. Read-only fetches cannot wander.

```js
const out = {};
const grab = async (path) => {
  const h = await fetch(path, {credentials:'include'}).then(r => r.text());
  return new DOMParser().parseFromString(h, 'text/html');
};
const home = await grab('/');
out.shipTo = home.querySelector('#glow-ingress-line2')?.textContent?.trim();
JSON.stringify(out, null, 1)
```

`#glow-ingress-line2` is the one selector here that this plugin has already
verified in use. Everything below it is a starting point, not a known-good
selector — Amazon's account pages are re-skinned more often than the storefront.

## What to pull, and where it lives

| Fact | Where to look | Goes to |
| --- | --- | --- |
| Default ship-to | `#glow-ingress-line2` on any page | `marketplaces.yaml` → marketplace `default_ship_to` |
| Address book | `/a/addresses` (older accounts: `/gp/css/account/address/view.html`) | `addresses.yaml` → one entry per address |
| Prime state | `/gp/primecentral` | `marketplaces.yaml` → marketplace `account` |
| Account home marketplace | which domain the session is signed in on | the marketplace id itself |

Treat every path in that table as unconfirmed. If one 404s or renders an
unexpected shape, **find the working one and write it back into this file** with
the date — that is the whole value of the skill on the second run.

The default ship-to line renders truncated, as `<Town na...> <ZIP>`. The postcode
is the part that matters and it is the part that survives truncation; do not
reconstruct the town name from the fragment.

## Writing it back

Ask before writing. This copies postal addresses and account state out of a
browser session onto disk — local, in the user's own directory, but still their
call to make and worth one sentence rather than a surprise.

Then, per address, write only what Amazon actually knows:

```yaml
- id: <short slug the user will type>
  label: "<what the user calls this place>"
  country: US
  currency: USD
  postcode: "02139"          # explicit, so nothing has to infer it from the lines
  lines:
    - "..."
  source: amazon-us session
  imported: 2026-08-17
```

`postcode` as its own key is the point of the import: the resolver otherwise has
to pattern-match it out of the address lines, and on an address whose format it
does not know it gives up rather than guessing wrong.

Leave `tax`, `delivery.deadline` and `delivery.constraints` alone. Amazon does
not know them, and blanking them destroys the useful half of the file.

## What never gets written

Card numbers, the last four digits, CVV, gift-card balances, order history,
passwords, session cookies. None of it is needed to decide where a parcel goes,
and this store is a plaintext YAML file that gets read by other tooling.

Payment is representable as `payment_on_file: true` and nothing more, and only if
something downstream actually needs to know it.

## Report

Say how many addresses were found, how many were new, which existing entries you
left untouched and why, and what you could not read. Do not echo the full street
lines back into the transcript — the id and the label are enough to confirm the
right thing was imported.

## Related

- `amazon-marketplace-config` — reads what this writes
- `/procurement-tools:shop-setup` — the interview for everything Amazon cannot tell you
- `amazon-delivery-check` — the same session, for dates rather than config
