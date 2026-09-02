---
name: amazon-shortlist
description: Turn a stated need into a short, verified list of Amazon.com candidates — establishing the right product category first, searching with Amazon's filter grammar, then opening each listing before recommending. Use when the user describes what they want rather than naming a product, asks what to buy for a purpose, or wants options compared on Amazon.
allowed-tools: Bash(python3 *), Bash(*/amazon_fetch.py *), Read, WebSearch
---

# Amazon shortlist

From "I need something that does X" to two or three verified candidates and a
recommendation. Not a survey.

## 1. Establish the category before searching

Do not start fetching against the words in the request. Confirm what class of
product actually solves the stated problem first, because a request phrased in
symptoms frequently names the wrong category — and shopping the wrong category
produces a confident, well-priced, useless answer.

Ask what the thing has to *do*, not what it should be called. A request for a
"folding platform truck to carry bags through an airport" is really a request
for a four-caster folding luggage cart; the platform trucks that match the words
are 36 × 24 in steel and weigh 8 kg.

When the requested thing and the needed thing differ, say so plainly in a
sentence, then research the needed thing. Do not silently substitute.

## 2. Search

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" search "folding luggage cart travel" --zip 02139
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/amazon_fetch.py" search "usb c power bank" --rh p_85:2470955011 --zip 02139
```

Run **several differently-phrased queries**, not one. Amazon's index is
title-driven and sellers optimise titles differently across the same category —
one query surfaced only two-wheel hand trucks, another only four-caster carts,
and neither result set hinted the other existed.

Filter nodes and their traps are in
[reference/search-filters.md](../../reference/search-filters.md). The two worth
knowing up front: delivery-speed filters are mutually exclusive, and in a
*browser* they are sticky across searches in a way nothing in the results
discloses. `amazon_fetch.py` is stateless and carries no cookies, which is a
reason to prefer it for sweeps.

## 3. Cut the grid down

Grid output is for shortlisting only. Before spending listing fetches:

- Drop `sponsored: true` rows before any judgement — they skew heavily to
  unknown brands buying placement.
- Drop rows whose title describes a different form factor. Read the title
  properly; the distinguishing spec is often only there.
- Keep the highest review counts *and* at least one low-count outlier if it
  looks structurally different. Review count measures age and marketing, not
  quality.

Aim to take **four to seven ASINs** into the next step.

## 4. Verify the listings

Hand off to `amazon-listing-check` — one call, all ASINs. Nothing gets
recommended on grid data.

## 5. Recommend

Give a recommendation, not a ranked table of everything found. One pick, one
sentence of why, and a **mandatory trade-off**: what this choice gives up. A
recommendation with no stated downside has not been thought through.

Then the candidate table, so the user can see what was rejected and on what
grounds.

Where a stated requirement turned out to be unsatisfiable, say so at the top
rather than burying it — that is usually the most valuable output of the whole
exercise, and it is the part that stays true after prices move.

An empty filtered result set is a finding about the category, not a failed
search. Say what the filter cost: the count before and after.

## Report honestly

- Distinguish verified from inferred rather than presenting both in one voice.
- Quote rating **and** review count, and say review authenticity is unverifiable.
- Never invent a price, stock state, delivery date or review score.
- If the user's sales-tax rate or ZIP is known, quote the delivered total
  separately from the sticker price. If not, do not guess one.

## Related

- `amazon-listing-check` — step 4
- `amazon-delivery-check` — when arrival timing decides it
- [reference/verification-traps.md](../../reference/verification-traps.md)
