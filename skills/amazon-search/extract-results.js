/*
 * Amazon US search-results extractor.
 *
 * Paste the whole file as the `text` argument to
 * mcp__claude-in-chrome__javascript_tool while a www.amazon.com/s?... page is open.
 * Returns one row per organic card plus a summary. Verified 2026-08-13.
 *
 * Two rules this file exists to encode, both learned the hard way:
 *
 *  1. It returns PARSED FIELDS ONLY. The Chrome extension blocks any result that
 *     looks like cookie or query-string data, so a row must never contain a raw
 *     href, a "key=value" string, or a "facet:id" token. Building the return value
 *     by joining with "=" is enough to get the entire call blocked.
 *  2. It never returns page text in bulk. A search page is ~700KB; everything here
 *     is a short field, capped.
 */
(() => {
  const txt = (el) => (el ? el.textContent.trim().replace(/\s+/g, ' ') : null);

  // Amazon emits placeholder cards carrying an empty data-asin.
  const cards = [...document.querySelectorAll('[data-component-type="s-search-result"][data-asin]')]
    .filter((c) => c.dataset.asin);

  /* The primary delivery message is one sentence carrying three separate facts:
     when it arrives, what carriage costs, and what that cost is conditional on.
     The bold node isolates the date phrase, so the remainder is the cost clause —
     which is why this parses structurally instead of regexing the whole string. */
  const readDelivery = (card) => {
    const msg = card.querySelector('.udm-primary-delivery-message');
    if (!msg) return { promise: null, when: null, speed: 'unknown', shipping: null, shippingCondition: null };

    const full = txt(msg);
    const when = txt(msg.querySelector('.a-text-bold'));
    const rest = when ? full.replace(when, '').trim() : full;

    // A range ("Aug 24 - Sep 1") is an estimate, not a promise.
    const isRange = !!(when && /^[A-Z][a-z]{2} \d{1,2} - [A-Z][a-z]{2} \d{1,2}$/.test(when));
    let speed = 'dated';
    if (isRange) speed = 'estimate-range';
    else if (/^Today/i.test(when || '')) speed = 'today';
    else if (/^Tomorrow/i.test(when || '')) speed = 'tomorrow';

    const fee = rest.match(/\$[\d,.]+\s+delivery/i);
    const condition = rest.match(/on orders over \$[\d,.]+/i);

    return {
      promise: full,
      when,
      speed,
      shipping: fee ? fee[0].replace(/\s+delivery/i, '') : (/FREE delivery/i.test(rest) ? 'free' : null),
      shippingCondition: condition ? condition[0] : null,
    };
  };

  /* Inside title-recipe the <h2> is the BRAND when a brand row is present and the
     TITLE when it is not, so the anchor is the only thing that always holds the
     title. The brand row renders on brand-navigational queries only — see
     brandCoverage below; do not build a brand list from it. */
  const readTitle = (card) => {
    const recipe = card.querySelector('[data-cy="title-recipe"]');
    if (!recipe) return { title: null, brand: null };
    /* Sponsored cards carry a second a.a-link-normal — the "Leave ad feedback"
       link — and it can come first in document order, so a bare a.a-link-normal
       silently titles the row "Leave ad feedback". Both selectors below were
       clean across 22 cards; the second is the fallback if the clamp class churns. */
    const anchor = recipe.querySelector('a[class*="s-line-clamp"]')
      || recipe.querySelector('a.a-link-normal:has(h2)');
    return {
      title: (txt(anchor) || '').slice(0, 90),
      brand: txt(recipe.querySelector(':scope > div h2')),
    };
  };

  const rows = cards.map((c) => {
    const priceEl = c.querySelector('.a-price .a-offscreen');
    const d = readDelivery(c);
    const t = readTitle(c);
    return {
      asin: c.dataset.asin,
      title: t.title,
      brand: t.brand,                                       // usually null — see brandCoverage
      price: txt(priceEl),                                  // null = no buyable offer
      listPrice: txt(c.querySelector('[data-a-strike="true"] .a-offscreen')),
      primeExclusivePrice: /Exclusive Prime price/i.test(txt(c.querySelector('[data-cy="price-recipe"]')) || ''),
      prime: !!c.querySelector('.udm-delivery-block .a-icon-prime'),
      deliveryWhen: d.when,
      deliverySpeed: d.speed,                               // today | tomorrow | dated | estimate-range | unknown
      shipping: d.shipping,                                 // "free" | "$3.16" | null
      shippingCondition: d.shippingCondition,               // "on orders over $25" | null
      stars: (txt(c.querySelector('[data-cy="reviews-block"] .a-icon-alt')) || '').slice(0, 24),
      scarcity: (txt(c.querySelector('[data-cy="delivery-recipe"]')) || '').match(/Only \d+ left in stock/i)?.[0] || null,
      sponsored: !!c.querySelector('.puis-sponsored-label-text'),
    };
  });

  // The same ASIN routinely appears twice — once in a sponsored slot, once organic.
  const seen = new Set();
  const duplicated = [];
  rows.forEach((r) => {
    if (seen.has(r.asin)) duplicated.push(r.asin);
    seen.add(r.asin);
  });

  return {
    // The whole result set after filters, not just this page — the honest answer
    // to "what did the filter cost".
    resultCount: (txt(document.querySelector('[data-component-type="s-result-info-bar"]')) || '').slice(0, 60),
    deliveringTo: (txt(document.querySelector('#glow-ingress-line2')) || '').slice(0, 40),
    cardsOnPage: rows.length,
    uniqueAsins: seen.size,
    duplicatedAsins: [...new Set(duplicated)],
    sponsoredOnPage: rows.filter((r) => r.sponsored).length,
    noOffer: rows.filter((r) => !r.price).map((r) => r.asin),
    brandCoverage: rows.filter((r) => r.brand).length + '/' + rows.length,
    rows,
  };
})()
