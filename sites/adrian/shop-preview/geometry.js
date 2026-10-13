// All physical measurements are illustrative centimetres. Use integer source
// pixel dimensions, never the gallery API's rounded aspect_ratio field.
export function printGeometry(width, height, longEdge, finish) {
  if (![width, height, longEdge].every(v => Number.isFinite(v) && v > 0)) {
    throw new Error('Positive source dimensions are required.');
  }
  const scale = longEdge / Math.max(width, height);
  const image = { width: width * scale, height: height * scale };
  const expand = (box, border) => ({ width: box.width + 2 * border, height: box.height + 2 * border });
  const paper = expand(image, 2);
  const mat = expand(paper, finish === 'paper' ? 0 : 5);
  const frame = expand(mat, finish === 'frame' ? 2 : 0);
  return { image, paper, mat, frame };
}
