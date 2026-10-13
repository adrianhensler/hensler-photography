import { printGeometry } from './geometry.js';

// A registry, not a two-person condition: each seller owns their collection and
// conceptual payment state. No accounts, secrets or financial APIs are involved.
const sellers = [
  { id: 'adrian', name: 'Adrian Hensler', userId: 1, gallery: 'https://adrian.hensler.photography/', samples: [52, 45, 47, 54] },
  { id: 'liam', name: 'Liam Hensler', userId: 2, gallery: 'https://liam.hensler.photography/', samples: [55, 53, 51] }
];
const $ = id => document.getElementById(id);
let currentSeller = sellers[0];
let currentPhoto;
let controller;

function safeImagePath(value) {
  return typeof value === 'string' && /^\/assets\/gallery\/[a-zA-Z0-9_.-]+\.(webp|jpg|jpeg|png)$/.test(value) ? value : null;
}
function usablePhoto(photo) {
  return Number.isInteger(photo.width) && Number.isInteger(photo.height) && photo.width > 0 && photo.height > 0 && safeImagePath(photo.large_url) && safeImagePath(photo.medium_url);
}
function makePhotoChoice(photo) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'photo-choice';
  button.dataset.photoId = photo.id;
  button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', `Study ${photo.title || 'Untitled photograph'} · demonstration`);
  const stage = document.createElement('span');
  stage.className = 'thumbnail';
  const img = document.createElement('img');
  img.src = safeImagePath(photo.medium_url);
  img.alt = photo.alt_text || photo.title || 'Public gallery photograph';
  img.width = photo.width;
  img.height = photo.height;
  img.loading = 'lazy';
  stage.append(img);
  const title = document.createElement('strong');
  title.textContent = photo.title || 'Untitled photograph';
  const action = document.createElement('span');
  action.textContent = 'Explore print study ↗';
  button.append(stage, title, action);
  button.addEventListener('click', () => { selectPhoto(photo); $('photo-title').focus({ preventScroll: true }); $('study').scrollIntoView({ block: 'start' }); });
  return button;
}
function selectPhoto(photo) {
  currentPhoto = photo;
  $('study').hidden = false;
  document.querySelectorAll('.photo-choice').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.photoId === String(photo.id))));
  ['selected-photo', 'print-photo'].forEach(id => {
    const img = $(id);
    img.src = safeImagePath(photo.large_url);
    img.alt = photo.alt_text || photo.title || 'Public gallery photograph';
    img.width = photo.width;
    img.height = photo.height;
  });
  $('photo-title').textContent = photo.title || 'Untitled photograph';
  $('photo-seller').textContent = `Photograph by ${currentSeller.name}`;
  $('pixel-size').textContent = `Source image: ${photo.width.toLocaleString()} × ${photo.height.toLocaleString()} pixels (width × height). Pixels are not print centimetres.`;
  $('provenance').textContent = Object.values(photo.ai_disclosure || {}).some(Boolean) ? 'Some source gallery metadata is AI-drafted. The photograph is unchanged; see the real gallery for its context.' : '';
  $('order-status').textContent = '';
  renderStudy();
}
function setInset(node, outer, inner) {
  node.style.left = `${(outer.width - inner.width) / 2 / outer.width * 100}%`;
  node.style.top = `${(outer.height - inner.height) / 2 / outer.height * 100}%`;
  node.style.width = `${inner.width / outer.width * 100}%`;
  node.style.height = `${inner.height / outer.height * 100}%`;
}
function renderStudy() {
  if (!currentPhoto) return;
  const finish = $('finish').value;
  const longEdge = Number($('size').value);
  const geometry = printGeometry(currentPhoto.width, currentPhoto.height, longEdge, finish);
  const rows = [['Image area', geometry.image], ['Paper outer size · 2 cm border', geometry.paper]];
  if (finish !== 'paper') rows.push(['Mat outer size · 5 cm surround', geometry.mat]);
  if (finish === 'frame') rows.push(['Frame outer size · 2 cm face', geometry.frame]);
  $('dimensions').replaceChildren(...rows.map(([label, box]) => {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    const value = document.createElement('dd');
    term.textContent = label;
    value.textContent = `${box.width.toFixed(2)} × ${box.height.toFixed(2)} cm`;
    row.append(term, value);
    return row;
  }));
  $('frame').style.aspectRatio = `${geometry.frame.width} / ${geometry.frame.height}`;
  setInset($('mat'), geometry.frame, geometry.mat);
  setInset($('paper'), geometry.mat, geometry.paper);
  setInset($('print-photo'), geometry.paper, geometry.image);
  // contain ensures even integer-rounded WebP variants retain their own ratio.
  $('print-photo').style.objectFit = 'contain';
  const price = ({20: 45, 30: 70, 40: 100})[longEdge] + ({paper: 0, mat: 35, frame: 90})[finish];
  $('example-price').textContent = `Illustrative CAD $${price} · not an offer`;
  $('order-status').textContent = '';
}
async function loadSeller() {
  controller?.abort();
  const request = new AbortController();
  controller = request;
  currentSeller = sellers.find(s => s.id === $('seller').value) || sellers[0];
  const seller = currentSeller;
  currentPhoto = null;
  $('study').hidden = true;
  $('collection').replaceChildren();
  $('load-status').textContent = 'Loading public photographs…';
  $('seller-caption').textContent = `A selection from ${seller.name}’s public gallery.`;
  $('payment-seller').textContent = seller.name;
  $('payment-status').textContent = '';
  $('gallery-link').href = seller.gallery;
  $('gallery-link').textContent = `Return to ${seller.name.split(' ')[0]}’s real gallery ↗`;
  try {
    const response = await fetch(`/api/gallery/published?user_id=${seller.userId}`, { signal: request.signal, credentials: 'omit' });
    if (!response.ok) throw new Error('Gallery unavailable');
    const data = await response.json();
    if (request.signal.aborted) return;
    const available = (Array.isArray(data.images) ? data.images : []).filter(usablePhoto);
    const curated = seller.samples.map(id => available.find(p => p.id === id)).filter(Boolean);
    const photos = curated.length ? curated : available.slice(0, 4);
    if (!photos.length) throw new Error('No published photographs');
    $('collection').replaceChildren(...photos.map(makePhotoChoice));
    $('load-status').textContent = '';
    selectPhoto(photos[0]);
  } catch (error) {
    if (error.name === 'AbortError') return;
    $('load-status').textContent = 'This public collection could not be loaded. Please visit the real gallery or try another photographer. No order can be placed.';
  }
}
sellers.forEach(seller => {
  const option = document.createElement('option');
  option.value = seller.id;
  option.textContent = seller.name;
  $('seller').append(option);
});
$('seller').addEventListener('change', loadSeller);
['size', 'finish'].forEach(id => $(id).addEventListener('change', renderStudy));
$('checkout-demo').addEventListener('click', () => {
  $('order-status').textContent = `Demonstration only. A future order would belong to ${currentSeller.name}. There is no checkout, reservation or payment, and nothing has been saved.`;
});
$('onboarding-demo').addEventListener('click', () => {
  $('payment-status').textContent = `Concept only: ${currentSeller.name} would complete Stripe-hosted onboarding for their own seller account and use their full Stripe dashboard. This button opens no service, connects no account and changes no settings.`;
});
loadSeller();
