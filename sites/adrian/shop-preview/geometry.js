// Millimetres internally; geometry is a study, never a printer recipe or offer.
export const sheets = [
  { id: '8x10', label: '8 × 10 in · stock fit', width: 254, height: 203.2 },
  { id: '11x14', label: '11 × 14 in · stock fit', width: 355.6, height: 279.4 },
  { id: '13x19', label: '13 × 19 in · nominal stock fit', width: 482.6, height: 330.2 },
  { id: 'a3plus', label: 'A3+ · 483 × 329 mm', width: 483, height: 329 },
  { id: '16x20', label: '16 × 20 in · other printer / lab', width: 508, height: 406.4 },
  { id: '30x13', label: '30 × 13 in · custom geometry only', width: 762, height: 330.2 },
  { id: 'square10', label: '10 × 10 in square target · trim/print recipe unproved', width: 254, height: 254 },
  { id: 'square12', label: '12 × 12 in square target · trim/print recipe unproved', width: 304.8, height: 304.8 },
  { id: 'square16', label: '16 × 16 in square target · other printer/lab, unproved', width: 406.4, height: 406.4 }
];
export const packages = {
  print: { label: 'Paper print only', mat: false, frame: false },
  mat: { label: 'Paper print + physical window mat', mat: true, frame: false },
  frame: { label: 'Paper print + physical mat + frame', mat: true, frame: true }
};
export const patterns = {
  plain: 'Plain white · no decorative ink',
  feather: 'Printed fine line / feather study',
  leather: 'Printed leather-look illustration',
  stone: 'Printed stone-look illustration'
};
const centered = (outer, inner) => ({ left: (outer.width-inner.width)/2, right: (outer.width-inner.width)/2, top: (outer.height-inner.height)/2, bottom: (outer.height-inner.height)/2 });
export function layoutVariant(width, height, options) {
  if (![width,height].every(v => Number.isFinite(v) && v > 0)) throw new Error('Positive pixel dimensions required');
  const target = sheets.find(sheet => sheet.id === options.sheet);
  const pack = packages[options.package];
  if (!target || !pack || !Object.hasOwn(patterns,options.pattern)) throw new Error('Unknown variant');
  const paper = width >= height ? { width: target.width, height: target.height } : { width: target.height, height: target.width };
  const border = 12.7; // Illustrative unprinted 0.5 in paper edge, not matboard.
  const presentationClearance = 12.7; // Genuine 0.5 in surround inside that edge, on ALL sides.
  const gap = 6.35; // Window reveals 0.25 in outside the image; no overlap assumed.
  const inset = Math.max(border + presentationClearance, pack.mat ? 25.4 + gap : 0);
  const maximum = Math.min((paper.width-2*inset)/width,(paper.height-2*inset)/height);
  const requested = options.edge === 'auto' ? maximum : Number(options.edge)/Math.max(width,height);
  if (!Number.isFinite(requested) || requested <= 0) throw new Error('Invalid image edge');
  const image = { width:width*requested, height:height*requested };
  const surround = centered(paper,image);
  const innerSurround = Object.fromEntries(Object.entries(surround).map(([side,value])=>[side,value-border]));
  const inkField = { width:paper.width-2*border, height:paper.height-2*border };
  const matWindow = pack.mat ? { width:image.width+2*gap, height:image.height+2*gap } : null;
  const warnings = [];
  const fits = Object.values(surround).every(value=>value >= inset-1e-8);
  if (!fits) warnings.push('Image does not fit the all-side clearances: retain at least 12.7 mm of inner surround beyond the 12.7 mm white paper edge on every side, plus any physical mat requirement. Choose a shorter image edge or larger target. No cropping or automatic edge-to-edge mode is applied.');
  if (target.width === target.height) warnings.push('Square sheet/frame target is a geometry study: trimming, paper/driver support and a measured frame still need an unproved print recipe and physical proof. No square fabrication is promised.');
  const short = Math.min(paper.width,paper.height), long = Math.max(paper.width,paper.height);
  if (short > 330.2+1e-8 || long > 990.6+1e-8) warnings.push('Beyond the original Canon PRO-200 manual-feed envelope: outsourced / other printer required. Stock frame fit is not printer capability.');
  if (options.printer === 'top' && (short > 328.93+1e-8 || long > 990.6+1e-8)) warnings.push('Exceeds the stated nominal 12.95 × 39 in top-feed custom envelope; check the exact supported paper/driver size. Manual-feed limits are different.');
  const endClearance = paper.width >= paper.height ? surround.left : surround.top;
  if (options.printer === 'fineart' && endClearance < 25-1e-8) warnings.push('Image enters the 25 mm fine-art feed-end margins. This geometric study is not a printable recipe as drawn.');
  if (options.printer === 'fineart' && options.pattern !== 'plain') warnings.push('Decorative ink begins 12.7 mm from the paper edge, inside the 25 mm fine-art end exclusions. The printed surround also needs a revised print layout.');
  const annotated = target.width === target.height ? 'Square paper/frame-fit target: trimming and a supported print recipe remain unproved; image dimensions are separate from this target.' : options.sheet === '30x13' ? 'Custom 30 × 13 in is geometry only; a 28 × 12 in image is not a proven paper/driver recipe.' : ['13x19','a3plus'].includes(options.sheet) ? 'Nominal 19 × 13 in (482.6 × 330.2 mm) is not true A3+ (483 × 329 mm).' : 'These are nominal paper/frame-fit dimensions, not photograph dimensions. Measure the real frame and prove the paper/driver recipe.';
  return { paper,image,surround,innerSurround,border,presentationClearance,fits,inkField,matWindow,matOuter:pack.mat ? paper : null,matSurround:pack.mat ? centered(paper,matWindow) : null,frameFit:paper,frameExternal:null,pack,warnings,annotated,endLimit:long-50,valid:!warnings.length };
}
export function packageSummary(options) {
  const pack = packages[options.package];
  const decorated = options.pattern !== 'plain';
  return {
    included: ['One paper photograph', decorated ? `${patterns[options.pattern]} outside the photograph, on the same sheet` : 'Plain unprinted white paper surround', ...(pack.mat ? ['Separate physical window mat — specifications unapproved'] : []), ...(pack.frame ? ['Physical frame — model / external size unapproved'] : [])],
    excluded: [...(!pack.mat ? ['No physical matboard, bevel or spacer'] : []), ...(!pack.frame ? ['No frame, glazing or hanging hardware'] : []), ...(decorated ? ['The printed design is not real leather, stone, feathers or textured matboard; it creates no physical spacer or bevel'] : [])]
  };
}
