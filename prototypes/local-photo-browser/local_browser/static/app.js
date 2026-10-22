const $ = (id) => document.getElementById(id);
const form = $('filters');
let rows = [], selected = -1, offset = 0, request = 0, timer;
const limit = 100;
const viewer = $('viewer');
const element = (tag, text) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
};
async function api(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Unable to load library (${response.status}). Restart to rescan if previews are missing.`);
  return response.json();
}
function picture(row, size) {
  const img = element('img');
  img.src = `/image/${row.id}/${size}`;
  img.alt = row.alt_text || row.caption || row.original_filename;
  img.loading = 'lazy';
  img.addEventListener('error', () => { img.alt = 'Preview unavailable — restart to rescan'; });
  return img;
}
function select(index) {
  if (!rows.length) return;
  selected = Math.max(0, Math.min(rows.length - 1, index));
  const row = rows[selected];
  document.querySelectorAll('.tile').forEach((tile, i) => tile.setAttribute('aria-pressed', String(i === selected)));
  const title = element('h2', row.original_filename);
  const button = element('button', 'Open preview');
  button.className = 'preview-open';
  button.addEventListener('click', openViewer);
  const details = element('dl');
  const fields = {relative_path:'Path', date_taken:'Captured (camera time)', modified_at:'Modified (UTC)', camera:'Camera', lens:'Lens', focal_length:'Focal length', aperture:'Aperture', shutter_speed:'Shutter', iso:'ISO', location:'Location', category:'Category', tags:'Tags', caption:'Caption', description:'Description'};
  for (const [key, label] of Object.entries(fields)) {
    const value = Array.isArray(row[key]) ? row[key].join(', ') : row[key];
    details.append(element('dt', label), element('dd', value || '—'));
  }
  details.append(element('dt', 'Dimensions'), element('dd', `${row.width} × ${row.height}`));
  $('inspector').replaceChildren(title, picture(row, 'preview'), button, details);
  if (viewer.open) updateViewer();
}
function updateViewer() {
  const row = rows[selected];
  $('large').src = `/image/${row.id}/preview`;
  $('large').alt = row.caption || row.original_filename;
  $('viewername').textContent = row.original_filename;
  $('back').disabled = selected <= 0;
  $('forward').disabled = selected >= rows.length - 1;
}
function openViewer() {
  if (selected < 0) return;
  updateViewer();
  viewer.showModal();
}
function render(result) {
  rows = result.items;
  selected = -1;
  $('grid').replaceChildren();
  const fragment = document.createDocumentFragment();
  rows.forEach((row, i) => {
    const tile = element('button');
    tile.className = 'tile';
    tile.setAttribute('aria-pressed', 'false');
    tile.append(picture(row, 'thumbnail'), element('span', row.original_filename), element('small', `${(row.date_taken || row.modified_at).slice(0, 10)} · ${row.camera_model || 'No camera EXIF'}`));
    tile.addEventListener('click', () => select(i));
    tile.addEventListener('dblclick', openViewer);
    tile.addEventListener('keydown', (event) => { if (event.key === 'Enter') { select(i); openViewer(); } });
    fragment.append(tile);
  });
  $('grid').append(fragment);
  $('count').textContent = `${result.total} photos${result.total ? ` · ${offset + 1}–${offset + rows.length}` : ' · No matches'}`;
  $('page').textContent = `Page ${Math.floor(offset / limit) + 1}`;
  $('previous').disabled = offset === 0;
  $('next').disabled = offset + limit >= result.total;
  $('inspector').replaceChildren(element('p', rows.length ? 'Select a photo to inspect its metadata.' : 'No photos match these filters. Try clearing them.'));
}
async function refresh() {
  const version = ++request;
  const params = new URLSearchParams(new FormData(form));
  params.set('sort', $('sort').value);
  params.set('direction', $('direction').value);
  params.set('offset', offset);
  params.set('limit', limit);
  try {
    const result = await api(`/api/photos?${params}`);
    if (version !== request) return;
    $('error').hidden = true;
    render(result);
  } catch (error) {
    if (version !== request) return;
    $('error').textContent = error.message;
    $('error').hidden = false;
  }
}
form.addEventListener('submit', (e) => e.preventDefault());
form.addEventListener('input', () => { clearTimeout(timer); offset = 0; timer = setTimeout(refresh, 180); });
form.addEventListener('reset', () => { offset = 0; setTimeout(refresh); });
for (const id of ['sort', 'direction']) $(id).addEventListener('change', () => { offset = 0; refresh(); });
$('previous').addEventListener('click', () => { offset = Math.max(0, offset - limit); refresh(); });
$('next').addEventListener('click', () => { offset += limit; refresh(); });
$('close').addEventListener('click', () => viewer.close());
$('back').addEventListener('click', () => select(selected - 1));
$('forward').addEventListener('click', () => select(selected + 1));
viewer.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); select(selected + (e.key === 'ArrowRight' ? 1 : -1)); }
});
async function init() {
  try {
    const [facets, status] = await Promise.all([api('/api/facets'), api('/api/status')]);
    for (const [key, values] of Object.entries(facets)) {
      for (const value of values) {
        const option = element('option', value);
        option.value = value;
        form.elements[key].append(option);
      }
    }
    $('scan').textContent = JSON.stringify(status, null, 2);
    await refresh();
  } catch (error) { $('error').textContent = error.message; $('error').hidden = false; }
}
init();
