# Delivery options, costs and Prime

A listing does not have *a* delivery date. It offers up to two **options**, and
they differ in cost as well as speed — usually the fast one carries a basket
minimum and the slow one does not. Collapsing them into one sentence throws away
the trade-off that decides the purchase.

Everything here was measured on `amazon.com` on **2026-08-19**, ship-to ZIP
`06268`, egressing from the US, against a signed-in Prime account and an
anonymous `curl` side by side.

## Read the attributes, not the sentence

Amazon publishes each option as `data-csa-c-*` attributes on the message span,
right beside the English prose. Reading those gets the fee, the date, the basket
minimum and the cutoff as separate values, and it does not depend on the
storefront rendering English.

| Content id | Slot |
| --- | --- |
| `DEXUnifiedCXPDM` | First option — the one the buy box leads with |
| `DEXUnifiedCXSDM` | Second option — the "Or …" line |

| Attribute | Holds |
| --- | --- |
| `data-csa-c-delivery-price` | `FREE`, a fee like `$5.85`, or the string `fastest` |
| `data-csa-c-delivery-time` | `Tomorrow, August 20`, `Overnight 4 AM - 8 AM`, `September 3 - 8` |
| `data-csa-c-delivery-condition` | `on qualifying orders over $25` — the basket minimum, alone |
| `data-csa-c-delivery-cutoff` | `Order within 4 hrs 3 mins` |
| `data-csa-c-delivery-benefit-program-id` | `cfs`, `paid_shipping`, `SUB_SAME_DAY_OVERNIGHT_PROGRAM`, or empty |
| `data-csa-c-mir-sub-type` | `CONDITIONALLY_FREE` when the free claim has strings |
| `data-csa-c-delivery-origin-country`, `-destination` | Cross-border shipments. Empty on every domestic listing measured |
| `data-csa-c-pickup-location`, `data-csa-c-distance` | Pickup-point options rather than delivery |

`amazon_fetch.py listing` returns these as `delivery_options`;
`skills/amazon-search/extract-product.js` returns them as `deliveryOptions`.

### Four ways this field set will mislead you

1. **`benefit-program-id: paid_shipping` does not mean you pay.** It names the
   programme, not the outcome. Two listings carried `paid_shipping` together
   with `price: FREE` (B002VD5GH6, B00885985C). Read `price`.
2. **`price` is not always a price.** On a second option it is frequently the
   literal string `fastest`, matching prose like "Or fastest delivery August 24
   - 26". The fee for that upgrade is *not* stated on the listing.
3. **The block is re-rendered per breakpoint**, so the same option appears up to
   four times. Deduplicate.
4. **It is sometimes absent entirely.** B002VD5GH6 rendered a primary slot with
   no `DEX` span at all. An empty `delivery_options` is not "no delivery" — fall
   back to the prose in `delivery`.

The attributes do **not** appear on search result cards. Search cards carry
prose only; `extract-results.js` parses that structurally instead.

## The anonymous route already has the Prime date

The plugin previously claimed the anonymous route can only see the
non-Prime promise. That is true of `#deliveryBlockMessage` — whose text stops at
the first `</div>`, i.e. the first option — and false of the page.

The Prime date is in the **second** slot of the anonymous HTML, and on five
Amazon-fulfilled ASINs it matched the signed-in session exactly:

| | Anonymous | Signed in |
| --- | --- | --- |
| First option | `FREE` · Monday, August 24 · *on orders shipped by Amazon over $35* · `cfs` | `FREE` · Overnight 4 AM - 8 AM · *on qualifying orders over $25* · `SUB_SAME_DAY_OVERNIGHT_PROGRAM` |
| Second option | `FREE` · **Tomorrow, August 20** | `FREE` · **Tomorrow, August 20** |

So the free route gets the standard Prime date right. What a signed-in session
adds is narrower than "the Prime date", and worth stating precisely:

- the **same-day / overnight upgrade**, which anonymous never shows;
- the **lower basket minimum** — $25 signed in against $35 anonymous;
- the **order-within cutoff** on the leading option;
- coupons and Prime-exclusive pricing, which never render anonymously.

On merchant-fulfilled items the signed-in session added **nothing**: B0C2H26G6S,
B0GSJGFSGZ, B09FHGX71K and B00885985C were identical field for field on both
routes. Escalating to a browser for those spends a session for no new fact.

## Is Prime actually in force?

Every Prime date assumes a live membership on the delivery date, and nothing on
a product page checks that. `/gp/primecentral` does, and it is readable with a
same-origin `fetch` from a signed-in tab — see `amazon-account-import`.

The account this was measured on was **eight days into a free trial**, converting
to a paid monthly plan on a date beyond several of the delivery estimates being
quoted. A trial that lapses before the parcel arrives silently invalidates the
answer. Check the membership state before quoting a Prime promise more than a
few days out, and say so when it is a trial.

Amazon renders Prime Central with hashed CSS-module class names that will churn.
Anchor on `cel_widget_id` prefixes instead:

| Widget | Carries |
| --- | --- |
| `[cel_widget_id^="prime-membership-central-profile"]` | `N days left in your trial`, membership state |
| `[cel_widget_id^="plan-change-action-desktop"]` | Current plan, price, renewal date, upcoming plan change |

Strip `<script>` and `<style>` before reading `textContent` — see
[verification-traps.md](verification-traps.md).

## Reporting

State, per option: the date, the carriage cost, and the condition attached to it.
A date without its condition is not an answer, and neither is "free delivery" on
a $9.99 item whose free tier needs a $25 basket.

Where the two options differ in cost, say what the faster one costs — in money if
`price` names a figure, in "unstated, shown only at checkout" if it says
`fastest`.

## Related

- [fetch-routes.md](fetch-routes.md) — which route, and proving it worked
- [verification-traps.md](verification-traps.md) — fields that read as authoritative and are not
- `amazon-delivery-check` — the signed-in workflow
- `amazon-account-import` — reading Prime state out of the session
