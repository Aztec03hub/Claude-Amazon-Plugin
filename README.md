# Amazon plugin (Lafayette fork)

Marketplace research that reads the listing rather than the search grid, for a
delivery postcode you choose rather than one your network implies.

Fork of [danielrosehill/Claude-Amazon-Plugin](https://github.com/danielrosehill/Claude-Amazon-Plugin)
with cross-platform fixes and three additions: a delivery-location override,
variation-matrix resolution, and list read/write.

---

## Why this exists

`WebFetch` cannot reach amazon.com. `/dp/` returns HTTP 500 and `/s?k=` returns
503, consistently rather than transiently, and the bot wall returns **HTTP 200
with a captcha body** - so a status code is not a success test. This plugin
shells out to `curl` with browser headers and checks page size instead.

## Requirements

Python 3 and `curl`. That is the whole dependency list. `curl` is resolved once
via `shutil.which`; if it is missing you get a JSON error naming the install
command for your platform, not a traceback.

Works on Windows, WSL, Linux and macOS. See
[skills/amazon-fetch-route](skills/amazon-fetch-route/SKILL.md) for the
platform-specific gotchas, which are real and have bitten.

## The script

```bash
python3 scripts/amazon_fetch.py probe
python3 scripts/amazon_fetch.py listing  B0AAA B0BBB --zip 60137
python3 scripts/amazon_fetch.py search   "folding luggage cart" --zip 60137 --rh p_85:2470955011
python3 scripts/amazon_fetch.py variants B0AAA --pick "Style=5 Pack"
```

`listing` takes several ASINs in one call. Batch them.

### `--zip` - set the delivery location

**Pass it on every call.** Amazon derives the delivery address from the
requesting IP, so every price, Prime badge, stock figure and delivery date is
rendered for wherever the request originates. On a laptop at home that is right
by accident. From a datacenter, a VPN, CI or an agent sandbox it is silently
wrong, and the output looks identical either way.

Measured, same ASIN, same minute, from a cloud host in South Carolina:

| | ship-to | delivery |
| --- | --- | --- |
| no flag | North Charleston 29415 | Wednesday, 9 September |
| `--zip 60137` | Glen Ellyn 60137 | Monday, 7 September |

Same price, two days apart on delivery, nothing on the page saying which you
got. `--zip` implies `--expect-zip`, so the location is applied *and* verified.
If Amazon rejects the postcode the script exits rather than returning
host-location data dressed as the requested one.

### `variants` - options are separate ASINs

Every combination of colour, size and pack count is its own ASIN, and Amazon
ships the whole matrix inside the product page. `listing` surfaces it:

- `variants.this` - this ASIN's own option values
- `variants.also_available` - siblings differing in exactly one dimension
- `variants.check_pack_size` - **present when a quantity option exists**

Treat `check_pack_size` as blocking. Measured on a real cable listing: four
singles at $17.42 came to $69.68 where the five-pack was $47.60, and neither
page mentions the other.

The quantity dimension is detected from its **values**, not its label. Amazon's
dimension names are seller-chosen: on that listing the pack count was under
`Style` while `Size` meant cable length.

### Output shape

JSON on stdout. With `--zip` it is
`{"delivery_location": {...}, "results": [...]}`; without, just the results.

## Skills

| Skill | Route | Does |
| --- | --- | --- |
| `amazon-fetch-route` | script | Which route to use, and proving it worked |
| `amazon-listing-check` | script | Verified price, stock, seller, specs for ASINs |
| `amazon-shortlist` | script | Need to a shortlist, category-first |
| `amazon-marketplace-config` | script | Which storefront and postcode to use |
| `amazon-search` | browser | Signed-in search grid with real delivery dates |
| `amazon-delivery-check` | browser | Same-day, cutoffs, Prime-exclusive pricing |
| `amazon-order-history` | browser | What was bought, when, for how much |
| `amazon-order-cancel` | browser | Cancel an order, with confirmation and verification |
| `amazon-address-book` | browser | Read and edit delivery addresses |
| `amazon-account-import` | browser | Pull addresses and Prime state into config |
| `amazon-lists` | browser | Read lists, priced against current listings |
| `amazon-list-add` | browser | Add a resolved ASIN to a named list |
| `amazon-open-asin` | script | Open listings in the user's own browser |
| `brand-scrub` | browser | Build trusted/blocked brand lists |

**Script route** is anonymous and stateless - no cookies, no session. It cannot
see anything behind the login, and it is immune to the sticky-filter problem
that affects browsing.

**Browser route** drives Claude in Chrome against the user's signed-in session.
Needed for anything account-specific.

## Lists

`amazon-lists` is read-only. `amazon-list-add` writes, and **posts to the
endpoint rather than driving the Add to List button**:

```
POST /hz/wishlist/additemtolist    listExternalId=<LISTID>&asin=<ASIN>&...
header: anti-csrftoken-a2z   (from #lists-sp-csrf-form-token)
```

`listExternalId` is required and explicit, so it cannot reach the default list.
The button approach can and did - the split button's two halves sit ~13px apart,
one adds to the default list with no prompt, and both live in the same form as
add-to-cart and buy-now. Amazon reflows detail pages as images resolve, so a
coordinate measured a moment earlier lands elsewhere.

Verification re-reads the list. The inline confirmation is worthless:
`#atwl-inline-sucess-msg` and `#atwl-inline-error-msg` are both pre-rendered and
both always carry text.

## Things that will catch you

Read [reference/verification-traps.md](reference/verification-traps.md). The
short version:

- HTTP 200 can be a captcha wall. Check bytes, not status.
- Grid prices are positional; open the listing.
- The first price on the page is often the List Price.
- **The deciding spec is frequently only inside the product images**, which a
  text fetch cannot read. "The listing does not say" is often wrong.
- Reviews hold the only real measurements, and the keyword-filtered reviews URL
  returns zero bytes without a session.

## Local changes vs upstream

- UTF-8 stdout/stderr, so legacy Windows code pages do not abort a completed run
- `scripts/open_url.py` replacing `xdg-open`, WSL-aware
- `--zip` delivery-location override
- `variants` mode and `check_pack_size`
- `amazon-lists` and `amazon-list-add`
- `curl` resolved and validated rather than assumed
- Compression disabled on the address-change POST, which decodes to garbage on
  brotli/zstd-enabled curl builds
