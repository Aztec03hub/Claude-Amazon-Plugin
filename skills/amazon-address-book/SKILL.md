---
name: amazon-address-book
description: Read and change the delivery addresses on the user's signed-in Amazon account - list the address book, correct a wrong street or postcode, add a new address, and change which one is the default ship-to. Use when the user says fix my Amazon address, add my new place, update the postcode, or make X the default delivery address. Reading is free; every change is confirmed against a before-and-after diff first, and removing an address is out of scope.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__tabs_close_mcp, Bash(python3 *), Read, Edit
---

# Amazon address book

Two halves, with a hard line between them.

**Reading** the address book is cheap, safe and fetchable — no navigation, no
clicking. Do it freely.

**Changing** an address decides where physical parcels go. Every change gets a
before-and-after diff, the user's explicit yes, and a verifying re-read
afterwards. A silently wrong address is not an error message; it is a parcel at
the old flat.

Removing an address is **out of scope**. Say so and let the user do it.

## Reading: fetch, never navigate

Unlike order history, this page is fully server-rendered — 426 KB with the
addresses in it. So use the read-only same-origin `fetch` from a tab on any
Amazon page, which cannot wander into a live order's controls.

```js
const d = new DOMParser().parseFromString(
  await fetch('/a/addresses', {credentials:'include'}).then(r => r.text()), 'text/html');
d.querySelectorAll('script,style,noscript').forEach(n => n.remove());

const clean = s => (s||'').replace(/\s+/g,' ').trim();
const blocks = [...d.querySelectorAll('[id^="ya-myab-display-address-block-"]')];
const rows = blocks.map((b, i) => {
  const f = n => clean(b.querySelector('#address-ui-widgets-' + n)?.textContent);
  return {
    i,
    name: f('FullName'),
    line1: f('AddressLineOne'),
    line2: f('AddressLineTwo'),
    cityStatePostcode: f('CityStatePostalCode'),
    country: f('Country'),
    phone: f('PhoneNumber').replace(/^Phone number:\s*/i,'').replace(/[‎‪-‬]/g,''),
    isDefault: !!b.querySelector('[id*="default-shipping"]'),
  };
});
JSON.stringify(rows, null, 1)
```

Three things in that snippet are load-bearing:

- **Scope every field to its block.** The field IDs are duplicated once per
  responsive layout — six addresses produce twelve nodes with
  `id="address-ui-widgets-FullName"` — so `document.querySelector('#address-ui-widgets-FullName')`
  returns **block 0's name for every address**, with no error and a real-looking
  value. This is the single most dangerous bug available in this skill.
- **Count `[id^="ya-myab-display-address-block-"]`, not `.address-tile`.** The
  first `.address-tile` is the *Add address* card, so tile count overstates the
  book by exactly one.
- **`isDefault` tests for presence, not text.** The default marker is an icon
  with empty `textContent`.

`CityStatePostalCode` is one field (`Town Name, ST 12345-6789`). The phone
renders with a label and invisible directional marks; strip both.

## Before changing anything

1. Read the book and show the user the address as it stands **today** — not as
   `addresses.yaml` remembers it. The account is the source of truth here.
2. State the change as a diff, field by field:

   ```
   Storrs (default ship-to)
     line1:    1631 STORRS RD          →  1631 Storrs Road, Apt 4
     postcode: 06268-1332              →  unchanged
   ```
3. Ask. Wait for a clear yes. Approval for one address is not approval for the
   next one.
4. Say explicitly if the address being changed is the **default ship-to**, since
   the change then applies to every order placed without choosing an address.

If the user's instruction is ambiguous about which address — "fix my address"
against a book of six — ask which, listing them by label and town. Never pick the
default and proceed.

## Making the change

Editing needs a real form, so this half **does** navigate.

```
https://<domain>/a/addresses/edit?addressID=<id>
```

Get `addressID` from the read above — `a#ya-myab-address-edit-btn-<i>` carries it
in its href. It is a 64-character opaque token: resolve it fresh every time,
never store it in `addresses.yaml`, never paste it into the transcript or a
commit.

Confirm `location.pathname` is `/a/addresses/edit` after the navigate before
touching a field.

### The form is a different ID namespace from the display

This catches people. The display IDs do not work on the form:

| Field | Form ID |
| --- | --- |
| Country | `select#address-ui-widgets-countryCode-dropdown-nativeId` |
| Name | `#address-ui-widgets-enterAddressFullName` |
| Phone | `#address-ui-widgets-enterAddressPhoneNumber` |
| Street 1 | `#address-ui-widgets-enterAddressLine1` |
| Street 2 | `#address-ui-widgets-enterAddressLine2` |
| City | `#address-ui-widgets-enterAddressCity` |
| State | `select#address-ui-widgets-enterAddressStateOrRegion-dropdown-nativeId` |
| Postcode | `#address-ui-widgets-enterAddressPostalCode` |
| Default ship-to | `input[type=checkbox]#address-ui-widgets-use-as-my-default` |
| Submit | `span#address-ui-widgets-form-submit-button` — "Update address" |

`/a/addresses/add` is the same form without `#addressID`.

**State is a `<select>`, not a text box** — 63 options on the US storefront.
Typing a state name into it does nothing and the form submits the old state with
no complaint. Set `.value` to the option's value and dispatch a `change` event,
or pick it with `find` + `computer`.

**Submit is a `<span>`**, Amazon's `a-button` wrapper. A `[type=submit]` selector
finds the site-search "Go" button instead. Click it by its id, or via `find`.

Change only the fields in the diff. Leave every other field exactly as loaded —
re-typing an unchanged field is how a working phone number acquires a typo.

## Setting a different default ship-to

Tick `#address-ui-widgets-use-as-my-default` on the address that should become
the default and submit. Amazon clears the flag on the previous default; there is
no separate "unset" step, and doing it the other way round leaves the account
with no default.

## After the change: verify, then sync

Re-read `/a/addresses` and diff against what you intended. Report what actually
changed, not what you submitted. Amazon normalises addresses — it will
recase, re-abbreviate and sometimes append a ZIP+4 — so the stored value may
legitimately differ in formatting from what was typed. Say so rather than
reporting a mismatch as a failure.

Then offer to sync the user config, which does not update itself:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/user_config.py" path
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/user_config.py" show
```

Amend the matching entry in `addresses.yaml` — the `postcode`, `lines` and
`country` keys and nothing else. **Amend, never regenerate.** Those entries carry
hand-written knowledge Amazon does not have: `tax`, `delivery.deadline`,
`delivery.constraints`, access notes. Rewriting the file drops them silently, and
they are not recoverable from the account.

If the changed address is the default ship-to, `marketplaces.yaml` →
`default_ship_to` may also need updating. Ask before touching it.

A postcode change is the one that matters most downstream: every delivery date
this plugin quotes is resolved from it. A stale `addresses.yaml` postcode
produces confident delivery promises for the old address, which is exactly the
failure mode the rest of this plugin exists to prevent.

## What this skill will not do

- **Remove an address.** Removal posts to `/a/addresses/delete` behind a modal.
  Nothing here builds that request. Point the user at the Remove button.
- **Touch payment methods.** Different page, not in scope.
- **Write card details, gift-card balances or order history** to config. See
  `amazon-account-import` for the standing bar on what may be stored.

## Related

- [reference/account-pages.md](../../reference/account-pages.md) — measured selectors and traps for this page
- `amazon-account-import` — the first-run import of the whole book into config
- `amazon-marketplace-config` — reads the postcode this skill maintains
- `amazon-delivery-check` — what a wrong postcode silently costs you
