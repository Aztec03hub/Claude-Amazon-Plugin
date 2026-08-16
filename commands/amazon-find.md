---
description: Research a need on Amazon — establish the right product category, search, then verify the shortlist on the listings before recommending
argument-hint: <what you need, in your own words>
---

Find the right Amazon product for: $ARGUMENTS

Use the `amazon-shortlist` skill, then `amazon-listing-check`.

Work in this order, and do not skip the first step:

1. **Establish the category.** Confirm what class of product actually solves
   this, before searching for the words in the request. A need phrased in
   symptoms often names the wrong category. If the requested thing and the
   needed thing differ, say so in a sentence and research the needed thing.
2. **Search several differently-phrased queries** with
   `scripts/amazon_fetch.py search`, not one. Sellers optimise titles
   differently across the same category and a single query routinely returns
   only one sub-type of the product.
3. **Cut the grid** — drop sponsored rows and wrong form factors, keep four to
   seven ASINs.
4. **Verify all of them on the listings** in one `listing` call. Nothing is
   recommended on grid data.
5. **Recommend one**, with a mandatory trade-off — what this pick gives up.
   Then the candidate table showing what was rejected and why.

If a stated requirement turns out to be unsatisfiable, lead with that. It is
usually the most valuable finding and it stays true after prices move.

If the user has not given a ZIP and delivery matters, ask once rather than
quoting a date for wherever this machine resolves.
