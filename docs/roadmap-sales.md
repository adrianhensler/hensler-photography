# Sales roadmap

How Hensler Photography gets from "a portfolio" to "selling prints", in
stages that each have to earn the next. This serves the photographers'
showcase goal (ADR 0004). The AI-showcase goal applies too: the sales
path is built in the open like everything else, and AI-drafted text on a
page someone might buy from is reviewed first.

Last reviewed: 2026-09-28.

## Where things stand

| Piece | State |
|---|---|
| Print inquiries | A mailto link on the About page (`sites/adrian/about.html`, `#print-inquiry`). No inquiry form, no tracking. |
| Per-image pages | Not built. `GET /api/gallery/published/{slug}` already returns one published image by slug, and every image has a unique slug per photographer. |
| Sale flag | `images.available_for_sale` exists, defaults to 0, and nothing sets or reads it yet. |
| Products and orders | `products` (image, type, size, `price_cents`) and `orders` (Stripe payment id, email, shipping address, status) tables exist in `api/database.py` with no routes using them. |
| Print quality | Upload computes recommended print sizes from resolution (300 and 200 DPI). Not stored or shown publicly. |

## Stage 2: permalinks and inquiries

Goal: find out whether anyone wants a print, at near-zero build cost.

1. **`/photo/{slug}` pages** on each portfolio site: the image large, its
   reviewed title and caption, EXIF when shared, and a clear "Prints
   available: ask about this photo" action. Good for sharing and search.
2. **Inquiry that names the photo.** The action pre-fills the photo's
   title and permalink (mailto first, a small form later if volume
   warrants), so every inquiry says which image it's about.
3. **Count it.** Track inquiry clicks per image in the existing analytics
   events, so demand is visible per photo and per photographer.
4. **Review before it sells.** A photo offered for sale should have no
   unreviewed text (the gallery manager's "Needs review" filter).

**Entry criterion for stage 3:** real inquiries turning into paid prints
by hand (invoice, e-transfer or a payment link, then order from a lab and
ship). A few manual sales prove demand and settle pricing, sizes, and a
print lab before any checkout is built.

## Stage 3: storefront

Only after stage 2 shows demand.

- **Checkout:** Stripe Checkout, or a hosted store, rather than a
  hand-built cart. The `products` and `orders` tables are shaped for
  Stripe already.
- **Fulfilment:** a print-on-demand lab (prints and ships to the buyer,
  no inventory) versus local printing and shipping. It decides margins,
  quality control, and who handles tax on cross-border sales.
- **Pricing per product**, stored in `products.price_cents` per image and
  size, with `available_for_sale` as the switch.
- **Policies** a store needs before it takes money: returns, shipping,
  privacy.

## Tax notes (confirm with an accountant)

These are the general Canadian rules as understood on 2026-09-28, written
down so the question isn't lost. They are not tax advice. Check them
with an accountant before the first sale, and again before stage 3.

- **GST/HST registration.** You are a "small supplier" while your taxable
  sales worldwide stay at or below **$30,000 CAD over any four consecutive
  calendar quarters**. Past that, you must register and start charging
  GST/HST. If you pass $30,000 **within a single calendar quarter**, you
  become a registrant on the sale that pushes you over. Registering
  voluntarily before the threshold is allowed; it lets you claim input
  tax credits on business costs, but you then charge HST on every sale.
- **Nova Scotia HST** applies to sales delivered to Nova Scotia buyers once
  registered. It was lowered to 14% on 2025-04-01; confirm the current
  rate at the time. Other provinces use their own GST or HST rate based
  on where the buyer is.
- **Income tax applies from the first dollar**, whatever the GST/HST
  status. Sales are business income, reported on form T2125 with your
  personal return; keep records of prints, lab costs, shipping, and
  fees.
- **Exports.** Physical goods shipped to buyers outside Canada are
  generally zero-rated for GST/HST. US states and the EU have their own
  rules; at small volume US "economic nexus" thresholds are usually far
  away, and a print-on-demand lab or merchant-of-record service can take
  on collection. Verify for the chosen setup.
- **Keep records from day one:** every sale, date, buyer province or
  country, amount, and costs. The four-quarter test is easy to track
  with a simple spreadsheet and hard to reconstruct later.

## Open questions

- Which print lab, and does it ship internationally?
- Signed or limited editions, or open editions?
- Does Liam sell too, and whose name is on the invoice?
- Which photos to offer first? Candidates: featured images with the most
  lightbox views in analytics.
