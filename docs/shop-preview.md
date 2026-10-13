# TEST print studies — paper, printed surrounds, physical mats

Updated 2026-10-13 from clean main / production revision
`70e966493980ea337b997c5846cdf082a82d8f49` after Adrian's review of PR #89.
Public, unlinked URL: https://adrian.hensler.photography/shop-preview/

## Scope and truthful states

This is enquiry-only, not for sale. Every variant is TEST, unapproved and
unproofed. It has no checkout, financial APIs, AI APIs, customer-data fields,
storage, account changes, authenticated testing or production seller rollout.
No Jev service is connected. Printed patterns are optional CSS illustrations
outside the photo, not ready-to-print art files or actual material samples.
Plain white paper is the default design baseline, not an approved product.

Only the four files in `sites/adrian/shop-preview/`, its focused test, and this
document change. Existing gallery pages, photos, shared assets, navigation,
sitemap, management console, API, database, authentication, Caddy and Compose
remain untouched. No service restart is needed. Noindex is indexing guidance;
this unlinked page is public and is not access-controlled.

Adrian is the only active record in the current design study. The registry still
contains independent future photographer records, but does not enable their
testing or sales. The seller selector explains this scope, not an access policy.
Adrian-only authenticated testing and production activation are later work,
requiring a separate review. Proposed seller-owned payments remain conceptual.

## Geometry model — millimetres internally

Targets: stock 8 × 10, 11 × 14, nominal 13 × 19, true A3+ 483 × 329 mm,
16 × 20 (other printer / lab), and custom 30 × 13 in (geometry only).
Orientation follows the photograph without rotating or altering its pixels.
The image ratio comes from source integer pixel width/height, not the API's
rounded aspect_ratio and never a universal 21:9 assumption.

The sheet is centred on the image. The default image fits within an illustrative
12.7 mm unprinted edge. Optional printed artwork occupies the field inside
that white edge, behind and outside the photograph. Total image-to-paper
surrounds, the unprinted edge and decorative remainder are separately reported
for top/bottom/left/right. Sizes display both mm and inches to three decimals;
calculations retain full precision. A requested 12/18/28 in long edge is not
silently reduced, cropped or stretched when it fails the clearances: the warning
and dimensions remain visible, and package diagrams are withheld.

If a physical mat is selected, image fitting reserves at least 25.4 mm of mat
outside a window that reveals 6.35 mm beyond each image edge. The proposed mat
outer size equals the paper / nominal frame fit. The window is a centred opening,
not printed texture, and its four surround widths are listed. No overlap is
assumed in this geometric plan: real bevel, overlap, cut/depth tolerances and
paper support require a measured proof. Matboard covers any paper / printed
surround outside the window. It is explicitly included only in the mat/frame
package options.

Frame nominal fit means the sheet / mat outer target, not the frame's outside
size or visible glazing aperture. External frame dimensions stay **unsettled**
until a measured frame model is chosen. The outline is schematic. No frame,
glazing or hardware is implied by the paper-only option. Printed leather/stone/
feather illustrations are not those materials, not matboard and not spacers or
bevels; buyer summaries say this explicitly.

## Printer constraints — not proven recipes

The original Canon PRO-200 envelope supplied for this task is manual custom up
to 13 × 39 in; top-feed custom nominally 12.95 × 39 in. The checker treats the
top-feed figure as nominal: near-boundary exact paper/driver sizes must be checked.
Paper/driver settings may prevent using the full nominal envelope. A stock-frame
target outside the manual envelope is marked outsourced / other-printer required.
Lab and local self-print routes are possibilities, never approved fulfilment.

The 25 mm fine-art feed-end check covers both the image and decorative ink.
An 18 × 7.714 in hypothetical 21:9 image on nominal 19 × 13 in paper is geometry,
not a fine-art print recipe. Exact 19 in minus two 25 mm margins leaves
17.031496 in; a true 483 mm A3+ long edge leaves 17.047244 in (about 17.05 in).
These are kept distinct rather than treating nominal 19 in as 483 mm. Likewise,
28 × 12 in on custom 30 × 13 in is only a geometric example, not proof of a
supported driver/paper combination. Printer, paper/finish and physical proof
remain unsettled even when the geometric tests pass.

## Seller review / buyer preview

The buyer view shows proposed contents, exclusions, dimensions and unsettled
paper/finish, signing, price and fulfilment choices. Packaging, destination,
lead time and damage/return terms still require discussion. No mock selection
creates a purchasable product or changes real accounts.

The separate seller-review panel has eleven per-variant checklist points:
photo/crop; geometry; paper/profile; physical mat/frame or exclusion; proof;
signing; price; packaging; destination/fulfilment; lead time; damage/returns.
All marks are simulated and reset on every variant selection change. Even
eleven checked boxes remain NOT seller-approved, with no physical proof recorded.
Nothing is persisted or published. The panel is not the management console.

The contact link uses `adrianhensler@gmail.com`, already publicly displayed in
`sites/adrian/index.html` and `sites/adrian/about.html`, and independently verified
on the live About page. A title-escaped TEST subject opens the visitor's email
app. The page sends no message, collects no personal data and accepts no order.

## Verification and additive deployment

Focused tests cover exact geometry, square/portrait/landscape/10:1/1:10 extremes,
all sheet/package targets and four surrounds; margin/envelope warnings; true A3+
versus nominal dimensions; invalid-fit diagrams; truthful package wording;
simulated approvals/reset; no personal fields, writes or storage; keyboard and
320/390/768/1440 px layouts; safe text/image URLs and failed galleries.

Run `npx playwright test tests/shop-preview.spec.js` in the established dev/CI
stack. For isolated static verification, set SHOP_PREVIEW_BASE_URL; gallery/image
requests are intercepted by the test. Actual published WebP images are separately
rendered and inspected. Synthetic SVG ratio checks use their declared viewport,
not WebKit's rounded raster-cache dimensions.

Publish only this preview-scoped PR after exact-head CI and review. Recheck main
and production are clean at the base, and that no unrelated commits would ship.
After merge, compare the merged tree to the reviewed head, assert the exact six
preview/test/document paths, then fast-forward production to that exact revision.
Existing bind-mounted static routing serves the updated directory automatically;
do not edit live files while preparing, change configuration, or restart services.
Verify live desktop/mobile, enquiries, notices, proportions, current gallery
behavior, unchanged public-page bodies and unchanged container start timestamps.
