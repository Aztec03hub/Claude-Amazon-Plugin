---
name: amazon-marketplace-config
description: Resolve which Amazon storefront, currency, postcode and egress country an answer should be built from, by reading the user's stored delivery addresses and per-marketplace preferences. Use before any Amazon fetch that is going to quote a price or a delivery date, whenever the user names a destination, and whenever an answer would otherwise silently assume amazon.com and a US ZIP.
allowed-tools: Bash(python3 *), Bash(*/user_config.py *), Read
---

# Amazon marketplace config

Amazon is not one shop. It is about twenty separate storefronts with separate
catalogues, separate prices, separate facet grammars and separate delivery
promises, and an answer is only meaningful once you know which one it came from.
This skill turns "where is it going" into that choice, from stored config rather
than from an assumption.

## Get the answer in one call

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/user_config.py" resolve storrs
```

Returns the marketplace id, the domain to fetch, the listing currency, the
postcode to check delivery dates against, which country to egress from, the
facet profile to use, and the user's own notes about buying there.

With no address argument it uses `default_address` from the config. Other modes:
`path` (where the store is, what is in it), `show` (what is configured, street
lines redacted), `show --raw` (everything).

## Where the config lives, and why not here

The plugin ships **no address, no ZIP, no account state**. All of that is in a
user directory outside any repo, and `user_config.py` is the only thing that
knows where.

It searches, first hit wins, rather than owning a path:

| Order | Location |
| --- | --- |
| 1 | `$AMAZON_PLUGIN_CONFIG` — explicit override |
| 2 | `<user-data-root>/marketplaces/` — the shared home |
| 3 | `<user-data-root>/procurement-tools/` — what exists today |

`addresses.yaml` and `marketplaces.yaml` are **already owned by
`procurement-tools`**, and that is correct: a delivery address and a shop's tax
treatment are not Amazon-specific facts. This plugin reads that store. It does
not fork it, and it does not migrate it — two copies of an address is how a
delivery date ends up quoted for last year's flat.

So when config is missing, do not create a private copy. Route to the thing that
owns it:

- **Nothing configured at all** → `/procurement-tools:shop-setup`, which
  interviews the user and writes both files.
- **Amazon account facts missing** — Prime state, the address book, the default
  ship-to → the `amazon-account-import` skill, which reads them out of the
  signed-in session instead of asking.
- **One field wrong or stale** → edit the YAML in place and say which file.

## What to do with the resolved marketplace

**Pass it to everything.** `amazon_fetch.py` takes `-m/--marketplace` on every
mode, and defaults to `amazon-us` only because something has to be the default —
not because the US is the answer.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" listing B0XXXXXXXX \
    -m amazon-uk --expect-postcode "SW1A 1AA"
```

Three things the resolver tells you that change the answer:

**`facet_warning`.** Facet IDs are marketplace-local. `p_85:2470955011` is Prime
on amazon.com and is meaningless on amazon.de — it will not error, it will just
filter to something else or nothing. Only `amazon-us` has a verified facet
profile. On any other marketplace, either derive the grammar first per
[`profiles/README.md`](../../profiles/README.md) or search unfiltered and say
that the search was unfiltered.

**`landed_cost_warning`.** Some destinations have no storefront of their own and
are served as export destinations — Israel is served by amazon.com. For those the
listed price is not the price paid: there is an Import Fees Deposit and shipping
on top, and a US Prime membership buys nothing on the order. Quote the listed
price as the listed price, never as the total.

**`egress`.** The same ASIN fetched from two countries returns two currencies and
two delivery promises, both HTTP 200, with nothing on the page to say which you
got. amazon.com renders ILS from an Israeli IP and USD from a US one. So pick
deliberately — the marketplace's own country to read the listing as it is priced,
the destination country to see what a buyer there is shown — and say in the
answer which one you used.

## Postcodes

`postcode` comes from an explicit `postcode:` key on the address, or from a
pattern match against the country's postcode shape. When neither hits it is
`null`, and `postcode_source` says so.

**Do not fill in a null postcode by reading the address lines yourself.** An
earlier version of the resolver did that by taking the last number on the last
line, which turns "Yaffo 105" into postcode 105 — a value that looks entirely
real and silently produces a delivery promise for somewhere else. If the
postcode is null, ask for it or leave the date unquoted.

## Related

- `amazon-account-import` — fill the store from a signed-in session
- `amazon-fetch-route` — once the marketplace is chosen, which route reaches it
- `/procurement-tools:shop-setup` — the interview that writes the store
