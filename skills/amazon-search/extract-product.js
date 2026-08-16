/*
 * Amazon US product-page (/dp/ASIN) extractor.
 *
 * Paste the whole file as the `text` argument to
 * mcp__claude-in-chrome__javascript_tool while a www.amazon.com/dp/... page is open.
 * Verified 2026-08-13.
 *
 * Use this when the search card is not enough. Three facts exist only here:
 * who actually sells it, how many competing offers there are and at what price,
 * and how long the delivery promise stays valid.
 *
 * It scrolls first, on purpose — the product details table is not in the DOM on
 * load, and querying it cold returns nothing, which reads exactly like a listing
 * with no details.
 */
(async () => {
  const txt = (s) => {
    const el = document.querySelector(s);
    return el ? el.textContent.trim().replace(/\s+/g, ' ') : null;
  };

  window.scrollTo(0, document.body.scrollHeight * 0.6);
  await new Promise((r) => setTimeout(r, 2000));
  window.scrollTo(0, document.body.scrollHeight * 0.85);
  await new Promise((r) => setTimeout(r, 2000));
  window.scrollTo(0, 0);

  const details = {};
  document.querySelectorAll('.prodDetTable tr, #productDetails_detailBullets_sections1 tr, #detailBullets_feature_div li')
    .forEach((row) => {
      const t = (row.textContent || '').trim().replace(/\s+/g, ' ');
      const m = t.match(/^(ASIN|Manufacturer|Date First Available|Best Sellers Rank|Item model number)\s*:?\s*(.+)$/i);
      if (m) details[m[1]] = m[2].slice(0, 80);
    });

  /* #deliveryBlockMessage concatenates the fast promise and the slower free
     alternative into one string with no separator, so "Order within ..." runs
     straight into "Or FREE delivery Friday ...". The two slot IDs below split
     them properly — prefer those and keep the raw block only as a fallback. */
  const primary = txt('#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE')
    || txt('#deliveryBlockMessage');
  const secondary = txt('#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE');
  const cutoff = primary
    ? (primary.match(/Order within (?:\d+\s*(?:hrs?|hours?|mins?|minutes?|secs?)\s*)+/i) || [])[0]
    : null;

  return {
    // Authoritative — the URL carries slugs and tracking segments, this does not.
    asin: (document.querySelector('#ASIN') || {}).value || null,
    title: (txt('#productTitle') || '').slice(0, 120),

    price: txt('#corePrice_feature_div .a-offscreen'),
    listPrice: txt('.basisPrice .a-offscreen'),

    // Read the inner status span: #availability's raw text is glued to a blob of
    // embedded JSON config.
    availability: txt('#availability .a-color-success') || txt('#availability .a-color-price'),

    deliveryPromise: primary,
    // The slower free alternative, e.g. "Or FREE delivery Friday, August 14".
    // Its existence means the fast promise is the conditional one.
    deliveryAlternative: secondary,
    // The actionable half. A next-day promise expiring in 12 minutes is not a
    // next-day promise by the time the user reads the answer — quote it with a
    // timestamp or drop it. Note the promise itself can be conditional too:
    // "on qualifying orders over $25" appeared on a $19.98 item.
    orderWithin: cutoff,
    readAt: new Date().toISOString(),

    // These two differ constantly, and the difference is the point:
    // "Amazon / Amazon" is first-party; "Amazon / BrandDirect" is FBA and usually
    // good; anything shipping from an unknown merchant is the risk case.
    shipsFrom: txt('#fulfillerInfoFeature_feature_div .offer-display-feature-text-message'),
    soldBy: txt('#merchantInfoFeature_feature_div .offer-display-feature-text-message'),

    // Offer count plus the lowest price available, which is often well under the
    // buy box — "New & Used (4) from $16.98" against a $19.98 buy box. The price
    // appears twice in the raw text (offscreen copy plus visible copy); dedupe it
    // before quoting.
    otherOffers: txt('#aod-ingress-link'),

    rating: txt('#acrPopover .a-icon-alt'),
    ratingCount: txt('#acrCustomerReviewText'),
    recentSales: txt('#social-proofing-faceout-title-tk_bought'),

    // "Date First Available" is the listing-age signal the trust rubric wants, and
    // it is simply absent on many electronics listings. If it is missing here, say
    // listing age is unavailable — do not substitute review count for it.
    details,
    deliveringTo: (txt('#glow-ingress-line2') || '').slice(0, 40),
  };
})()
