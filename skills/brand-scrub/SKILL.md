---
name: brand-scrub
description: Ingest a marketplace search-results page, scrub the brand facet, and classify every manufacturer into a persistent allowlist or blocklist. Use when the user wants to filter out third-party junk brands, build or extend a trusted-brand list, or re-run a search restricted to brands they rate. Works against a profile in profiles/ (amazon-us today).
allowed-tools: Read, Write, Edit, Bash(mkdir *), Bash(cat *), Bash(python3 *), mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp
---

# Brand scrub

Turn a results page into a durable judgement about manufacturers. Amazon's catalogue is
open, so any popular category fills with interchangeable no-name brands. The star
ratings do not separate them — the brand does. This skill harvests the brands a search
actually surfaced, asks the user once which are real, and remembers the answer so the
next search in any category starts from a filtered field.

The output is not a report. It is a **re-runnable filtered URL** plus a durable list.

## Where the list lives

`<plugin-data-dir>/brands.json`, where `<plugin-data-dir>` is `$CLAUDE_USER_DATA/amazon/`
if set, else `$XDG_DATA_HOME/claude-plugins/amazon/`, else
`~/.local/share/claude-plugins/amazon/`. Create it if absent. Same convention as
the convention the plugin ecosystem uses for per-plugin data.

Shape, keyed by marketplace profile id:

```json
{
  "amazon-us": {
    "allow": { "236374": {"name": "Pelican",  "why": "professional case maker, warranty off-platform"} },
    "block": { "251638": {"name": "RLSOCO",   "why": "no presence off Amazon"} },
    "unrated": { "83034": {"name": "Smatree"} }
  }
}
```

Brand IDs are the source of truth, not names — names collide and get rebranded, the
`p_123` ID is stable and global. Keep `why` short; it is what stops the same brand being
re-litigated in six months.

## Procedure

### 1. Load the profile

Read `profiles/<marketplace>.json` (default `amazon-us`). Take the brand facet key
(`p_123`), the refinement rail selector, the sponsored-card selector and the search URL
grammar from it. Do not hardcode any of these here — when Amazon changes them, the
profile is the one place that gets edited.

### 2. Get the page in the real browser

Drive `claude-in-chrome`, not a headless fetch. Per the profile's `session_dependence`,
an anonymous session hides the curated brand facets and the Prime filter entirely, so a
scrub run anonymously silently sees a different brand field.

Take the user's URL if they gave one; otherwise compose one from their query.

### 3. Scrub the facet rail, not the cards

**Read brands from the `p_123` facet rail.** The profile's `results_page.brand_per_card`
records why, and the mechanism matters because the cards *look* like they have a brand
field: inside `[data-cy="title-recipe"]` the `<h2>` holds the brand when a brand row is
present and the product title when it is not, so a naive extractor returns a plausible
mixture of brands, titles and "Amazon's Choice" badges with nothing marking which is
which. The brand row also renders on brand-navigational queries only — 17 of 21 cards on
`waveshare raspberry pi hat`, 0 of 20 on `usb c hub`. A card-based scrub would therefore
harvest nothing on exactly the generic category searches this skill exists to clean up.

Extract `{label, id}` pairs from the rail. Two extraction rules that will otherwise cost
a debugging cycle each:

- **Return parsed fields, never raw hrefs.** The Chrome extension blocks JS results that
  look like cookie or query-string data. Split each token into separate `facet` and `id`
  fields before returning. Returning `"p_123:236374"` as one string, or the href it came
  from, gets the entire result blocked.
- **Expand the rail first.** Facet lists are truncated behind "See more". Click it, or
  the scrub only sees the first handful of brands.

Also count sponsored versus organic cards and report the ratio. Sponsored slots skew
heavily to unknown brands buying placement — 4 of 12 on the reference query.

### 4. Classify

Split the harvested brands three ways against `brands.json`: already allowed, already
blocked, and new.

For the new ones, apply the profile's `trust_rubric` to form a **proposal**, then put it
to the user. Do not silently auto-classify — the whole value of the list is that it
encodes their judgement, and a wrong entry is sticky.

Present it as a table: brand, ID, your proposal, and the one-line reason. Group the
obvious cases together so the user can accept a batch and only argue with the edge cases.

The rubric's sharpest discriminator in practice: does the brand exist off the
marketplace? A real manufacturer has a site, a warranty and a support channel. Where you
genuinely cannot tell, propose `unrated` rather than guessing — an honest unknown is
cheap, a wrong block is invisible and permanent.

### 5. Write back and re-run

Merge the user's decisions into `brands.json`. Then compose the filtered search from the
profile's `brand_allowlist` recipe — repeat the brand facet key once per allowed ID, since
the marketplace ORs values within a single facet — and give the user:

1. The **filtered URL**, allowlist brands only.
2. A **highlighted ranking** of the current page's organic results: allowlisted brands
   first, unrated after, blocked ones listed last but not hidden — the user asked to see
   what was excluded, and a silent exclusion is how a good product gets lost.
3. What the filter cost, in one line: how many of the original results survived.

Always report that last number, and take it from the result-info bar
(`[data-component-type="s-result-info-bar"]`) rather than counting cards — that bar gives
the whole filtered result set, cards give one page of it. The Prime + tomorrow +
sold-by-Amazon + 4-star stack left 31 of "usb c hub" on 2026-08-13. A filter that prunes
to nothing is a finding about the category, not a success.

## Scope

Allowlists are **cross-category**. Pelican earns trust in cases and keeps it everywhere;
Anker earns it in charging and keeps it. Do not partition the list by category — that
multiplies the maintenance and loses the transferability that makes it worth keeping.

The exception worth honouring: a brand that is genuinely good in one category and a
badge-engineered licensee in another. Record that in `why` rather than forking the list.

## Related

- `profiles/amazon-us.json` — the facet grammar and trust rubric this reads
- [`profiles/README.md`](../../profiles/README.md) — how this profile was derived
- `amazon-search` — consumes the allowlist; its `extract-results.js` already
  returns the sponsored flag and result count this skill needs
- `amazon-shortlist` — consumes the allowlist once it exists
