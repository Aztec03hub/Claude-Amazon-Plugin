---
name: amazon-search
description: Run a filtered Amazon US search inside the user's signed-in browser and return a decision table with per-card real delivery dates, Prime-exclusive pricing and brand facets. Use when the answer needs facts that only a signed-in session renders — what arrives today or tomorrow, what it actually costs at checkout, or a search restricted to a trusted brand list. For an anonymous sweep, or when the user has described a need rather than a product, start with amazon-shortlist instead and come here only if the session-only fields are required.
allowed-tools: Read, Write, Edit, Bash(mkdir *), Bash(python3 *), mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__find, mcp__claude-in-chrome__tabs_close_mcp
---

# Amazon search (signed-in)

**Scope.** This is the browser-driven search. It costs a real browser session and
earns that cost only when you need per-card delivery dates, Prime-exclusive
prices or the brand facet. For establishing the category and sweeping candidates,
`amazon-shortlist` is cheaper, stateless, and immune to the sticky-filter trap
below.

Turn a shopping question into a table the user can act on. Three fields carry the
decision, and everything here exists to get them right:

| Field | Why it is the one that matters |
| --- | --- |
| **ASIN** | The only unambiguous handle. Titles churn, listings get relisted, search rank moves. Quote it every time. |
| **Real cost** | Sticker price is not cost. Shipping fees, basket minima and Prime-exclusive pricing all move it. |
| **Delivery** | "Prime" is not a delivery date, and "FREE delivery" is not always free. Say which day, and say what it is conditional on. |

## Drive the real browser

Use `claude-in-chrome` against the user's signed-in session. This is not a preference,
it is a correctness requirement — the profile's `session_dependence` records that an
anonymous page hides the Prime filter and the curated brand facets entirely and shows a
degraded free-shipping stand-in instead. A run without a Prime session answers a
different question and looks identical.

Delivery promises are computed against the session's delivery ZIP. Read it
(`#glow-ingress-line2`) and state it with the answer. Do not change it — that is the
user's account setting.

## Procedure

### 1. Load the profile

Read `profiles/amazon-us.json`. Everything volatile lives there: facet IDs, sort keys,
selectors, recipes. Do not hardcode any of it in this skill — when Amazon changes, the
profile is the single file that gets edited.

Check its `verified` date. Anything more than a few months old is a hypothesis; re-derive
per `profiles/README.md` rather than trusting it silently.

### 2. Compose the search

Start from a `recipes` entry rather than assembling facets from scratch:

- `reputable_fast` — the default. Prime + tomorrow + sold by Amazon + 4 stars & up.
- `same_day` — when the user says today. Expect it to be empty for most electronics.
- `budget` — arbitrary cent ranges work; use the user's real number, never round it to
  one of the buckets the sidebar offers.
- `brand_allowlist` — once `brand-scrub` has built a list.

Two things that will otherwise waste a cycle:

- **A facet missing from the sidebar does not mean the token is dead.** It means this
  query and ZIP have no hits for it. Compose from the profile's IDs regardless.
- **Facet labels drift even when IDs do not.** `p_101` renamed itself between two
  consecutive days because the label names the current cutoff. Never quote a cutoff from
  the profile — read it live or omit it.

### 3. Extract

Run `extract-results.js` from this directory via `javascript_tool`. It returns parsed
rows, never page text. Two constraints are baked into it and must survive any edit:

- **Return parsed fields only.** The Chrome extension blocks results that look like
  cookie or query-string data. A row must never contain a raw href, a `key=value` string
  or a `facet:id` token — joining output with `=` is enough to get the whole call blocked.
- **Never pull the page into context.** A search page is ~700KB.

For a specific product, run `extract-product.js` on its `/dp/{ASIN}` page. Go there when
the user is close to deciding, because three facts exist only on that page: who actually
sells it, how many competing offers there are and at what price, and how long the
delivery promise stays valid.

### 4. Read the delivery string properly

The promise is one sentence carrying three separate facts. The extractor splits them;
this is what the splits mean:

| `deliverySpeed` | Meaning |
| --- | --- |
| `today` / `tomorrow` | A real promise, against this ZIP, at this hour |
| `dated` | A specific day a little further out |
| `estimate-range` | **Not a promise.** "Aug 24 - Sep 1" is an estimate, typically two to three weeks, and with no Prime badge it is the strongest per-card tell of a direct-from-overseas seller |

And on cost:

- `shipping: "free"` — free.
- `shipping: "$3.16"` — a real fee. **Add it to the item price before comparing.**
- `shippingCondition: "on orders over $25"` — the free claim is conditional on basket
  total. Same-day free delivery carried a $25 minimum, and a $19.98 item's next-day
  promise carried one too. Calling that free for a single-item order is wrong.
- `primeExclusivePrice: true` — that price needs a membership. Say so when comparing
  against a non-Prime retailer.

### 5. Rank and answer

Filter out sponsored rows before any judgement — they skew heavily to unknown brands
buying placement. Apply the profile's `trust_rubric`, and the `brand-scrub` allowlist if
one exists.

Output shape:

```
## {query} — Amazon US
Delivering to {ZIP} · read {timestamp} · {resultCount}

| # | Product | ASIN | Price | + shipping | Arrives | Prime |
|---|---------|------|-------|-----------|---------|-------|
| 1 | ...     | B0…  | $19.98| free      | Tomorrow| yes   |
```

Then, in a line or two: what the filters cost (the `resultCount` before and after), and
anything excluded that the user might have wanted to see. A filter that prunes to nothing
is a finding about the category, not a success — say so rather than quietly returning an
empty table.

Report rows with no price as "no current offer" rather than dropping them. A missing
price is not a cheap price.

## What this cannot tell you

Say these plainly rather than improvising around them:

- **Review authenticity.** Fakespot died 2025-07-01 and nothing replaced it. AI-written
  reviews read cleanly, so linguistic tells no longer discriminate. Use the structural
  signals in the profile's `trust_rubric` — seller identity, whether the brand exists off
  Amazon — and say the review score is unverified.
- **Listing age.** "Date First Available" is absent from many electronics listings. When
  it is missing, say so; do not substitute review count for age.
- **Per-card brand.** The brand row renders on brand-navigational queries only — 17 of 21
  cards on `waveshare raspberry pi hat`, 0 of 20 on `usb c hub`. The facet rail is the
  source of truth. Never build a brand list from cards.
- **Price history.** No free source. Keepa is the only working programmatic route and it
  is paid, ~7 tokens per ASIN for a real seller check.

## Related

- `profiles/amazon-us.json` — facet grammar, extraction contract, trust rubric
- `brand-scrub` — builds the durable brand allowlist this consumes
- `amazon-shortlist` — category-first, anonymous sweep; start there
- `amazon-delivery-check` — dates for ASINs you already have, without a search
- [`reference/search-filters.md`](../../reference/search-filters.md) — `rh=` node grammar and the sticky-filter trap
- [`profiles/README.md`](../../profiles/README.md) — how this profile was derived
