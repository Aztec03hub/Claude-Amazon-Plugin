# The Amazon US profile

`amazon-us.json` is **encoded context, not an integration**. It exists because
Amazon offers no buy-side API to a shopper, and the exploratory work a profile
front-loads — which filter does what, which selectors survive, what a delivery
string actually means — only has to be done once per marketplace instead of once
per purchase.

`amazon-search` and `brand-scrub` read it. Everything volatile lives here rather
than in a skill, so when Amazon changes, this is the single file that gets
edited.

## What the profile answers

| Section | The question it settles |
| --- | --- |
| `identifier` | What is the canonical handle for a product here, and what does it look like? |
| `search` | How is a search URL constructed — query, filter and sort parameter names? |
| `filters` | Which facet tokens map to which human labels, with caveats? |
| `results_page` | How do you read one search card — which selectors, and what does the text mean? |
| `product_page` | What is only knowable on the detail page — seller identity, competing offers, promise expiry? |
| `recipes` | Composed URLs worth keeping, and what they collapse to in practice |
| `trust_rubric` | How do you tell a real product from junk *on this specific marketplace*? |
| `access` | What API exists, what it really costs, which fetch route works |
| `traps` | What fails silently |
| `session_dependence` | What renders differently signed-in versus anonymous |

`results_page` and `product_page` together are the **extraction contract**.
Anchor them on semantic attributes rather than generated CSS classes — on Amazon
that means `data-cy` attributes and `udm-*` delivery classes, both of which held
across every query tested, while the `a-*` classes around them churn.

Record parse *rules*, not just selectors. Amazon's delivery string is one
sentence carrying three separate facts — when, at what cost, conditional on what
— so a profile that gives you a selector without the grammar still produces
"free next-day" for an item with a $3.16 shipping fee.

## Profiles are time-bound

Facet IDs, sort keys and filter availability change, and some are
session-dependent: the same URL shows different facets signed-in versus
anonymous. The profile carries `verified` and `verified_how`. **Treat anything
older than a few months as a hypothesis** and re-derive it the same way it was
derived the first time.

## How this one was derived

The method is reusable for any marketplace, which matters because each
marketplace now gets its own plugin (see the `shopping` plugin's
`marketplace-plugins` skill for the current roster). Six steps:

1. **Confirm the fetch route reaches the right country.** Wrong-country failures
   return HTTP 200 and plausible content, so an explicit check is the only
   signal that exists.
2. **Fetch a broad search page** in a category with many competing sellers. It
   will be large — save it to a file, never pull it into context.
3. **Extract every filter link and label.** On Amazon these are `[label](url)`
   pairs whose URL carries the filter parameter and whose label is the sidebar
   text.
4. **Recompose the tokens you care about into one URL and re-fetch it.** This
   catches tokens that parse but do not compose.
5. **Record what you confirmed and what you did not, per key.** Re-derive the
   doubtful ones rather than leaving them. `amazon-us.json` carried one confirmed
   sort value and four guesses for a day; a real browser exposes the whole list
   as a plain `<select>`, so the uncertainty was a property of the fetch route,
   not of the page. An unconfirmed key is a task, not a permanent state.
6. **Derive the extraction contract on at least three queries chosen to force
   *different* shapes** — a fast-Prime query, a same-day query and a
   slow-overseas-shipping query. A single query would have shown one delivery
   shape and yielded a parser that silently mislabels the other two.

## Session dependence is the trap that produces a wrong profile

Derive against a **real signed-in session**, not an anonymous fetch. Anonymous
hides the Prime filter and the curated brand facets entirely and shows a
degraded free-shipping stand-in in their place. Both passes are recorded in
`amazon-us.json` under `session_dependence`, because the anonymous result looked
complete and was not.

This is the same class of failure as the delivery-ZIP problem in
[`reference/fetch-routes.md`](../reference/fetch-routes.md): a route that
returns a well-formed answer to a different question.
