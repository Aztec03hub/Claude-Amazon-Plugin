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

  /* Getting the price you would actually pay is fiddlier than it looks, in two
     separate ways:

       1. The struck-through List Price sits in the same block and on some
          listings comes first. Read the first .a-offscreen and you get it:
          measured 2026-08-19, ASIN 0140449132 read $16.00 against a real $12.91.
       2. In the LIVE DOM the .priceToPay screen-reader span is blank — the price
          is assembled from .a-price-symbol / -whole / -fraction. (In the raw
          HTML that same span does carry the value, which is why the Python
          extractor can regex a-offscreen and this one cannot.)

     So: read .priceToPay's text, and only fall back to a non-struck offscreen
     span. #corePrice_feature_div is additionally EMPTY on books, hence the
     ordering of the containers below. */
  const priceIn = () => {
    const boxes = ['#corePriceDisplay_desktop_feature_div', '#corePrice_feature_div', '#apex_desktop'];
    for (const sel of boxes) {
      const box = document.querySelector(sel);
      if (!box) continue;
      const pay = box.querySelector('.priceToPay');
      if (pay) {
        const v = pay.textContent.replace(/\s+/g, '');
        if (/\d/.test(v)) return v;
      }
      for (const el of box.querySelectorAll('.a-offscreen')) {
        if (el.closest('.a-text-price, .basisPrice, [data-a-strike="true"]')) continue;
        const v = el.textContent.trim();
        if (/\d/.test(v)) return v;
      }
    }
    return null;
  };

  /* Amazon publishes each delivery option as attributes on the message span,
     next to the English sentence: the fee, the date, the basket minimum and the
     cutoff as separate values. Read those instead of parsing the prose — it is
     exact, and it survives a storefront that renders the sentence in another
     language. PDM is the first option, SDM the second. Verified 2026-08-19;
     contract in reference/delivery.md. Falls back to prose when absent, which
     does happen. */
  const readDeliveryOptions = () => {
    const slot = { DEXUnifiedCXPDM: 'primary', DEXUnifiedCXSDM: 'secondary' };
    const seen = new Set();
    const out = [];
    document.querySelectorAll('[data-csa-c-content-id="DEXUnifiedCXPDM"], [data-csa-c-content-id="DEXUnifiedCXSDM"]')
      .forEach((el) => {
        const a = (n) => el.getAttribute('data-csa-c-' + n) || null;
        const row = {
          slot: slot[el.getAttribute('data-csa-c-content-id')],
          cost: a('delivery-price'),          // "FREE" | "$5.85" | "fastest"
          when: a('delivery-time'),
          condition: a('delivery-condition'), // "on qualifying orders over $25"
          cutoff: a('delivery-cutoff'),
          program: a('delivery-benefit-program-id'),
          subType: a('mir-sub-type'),
        };
        // The block is re-rendered per breakpoint; the same option repeats.
        const k = [row.slot, row.cost, row.when, row.condition, row.cutoff].join('~');
        if (seen.has(k)) return;
        seen.add(k);
        out.push(row);
      });
    return out;
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

    price: priceIn(),
    listPrice: txt('.basisPrice .a-offscreen'),

    // Read the inner status span: #availability's raw text is glued to a blob of
    // embedded JSON config. Keep every sentence — "In stock" and "In stock.
    // Usually ships within 4 to 5 days" are different answers, and the second
    // one is the reason a September date sits under an in-stock badge.
    availability: txt('#availability .a-color-success')
      || txt('#availability .a-color-price')
      || txt('#availability .a-color-state'),

    // No buy box means nothing is purchasable at this URL, whatever price the
    // page still shows. On a variant parent that price belongs to a different
    // variant: B003J9LZE4 read $108.99 for a size this URL cannot sell.
    buyable: !!(document.querySelector('#add-to-cart-button') || document.querySelector('#buy-now-button')),

    // Structured, one entry per option, with the fee and the basket minimum as
    // their own fields. Prefer this over the three prose fields below; they are
    // kept because it is empty on some listings.
    deliveryOptions: readDeliveryOptions(),

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
