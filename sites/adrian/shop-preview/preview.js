import { layoutVariant, packageSummary, sheets, packages, patterns } from './geometry.js?v=surrounds1';

// Independent seller records remain extensible. Only Adrian is active in this
// public design study; this is not authentication or a rollout to other users.
const sellers = [
  { id: 'adrian', name: 'Adrian Hensler', userId: 1, gallery: 'https://adrian.hensler.photography/', active: true, samples: [52,45,47,54] },
  { id: 'liam', name: 'Liam Hensler', userId: 2, gallery: 'https://liam.hensler.photography/', active: false, samples: [55,53,51] }
];
const seller = sellers.find(record => record.active);
const $ = id => document.getElementById(id);
const controls = ['sheet','edge','pattern','package','printer','material','signing','fulfilment','price'];
let currentPhoto;
const reviewPoints = [
  'Final photograph / crop reviewed (this study adds no crop)',
  'Image, paper, border and surround geometry reviewed',
  'Paper brand, weight, finish and print profile reviewed',
  'Physical mat / frame specs reviewed, or explicitly excluded',
  'Physical proof approval would be required — no proof recorded here',
  'Signing choice and placement reviewed',
  'Price and charges reviewed',
  'Packaging and protection reviewed',
  'Destination and fulfilment route reviewed',
  'Lead time reviewed',
  'Damage / return terms reviewed'
];
function safeImagePath(value) {
  return typeof value === 'string' && /^\/assets\/gallery\/[a-zA-Z0-9_.-]+\.(webp|jpg|jpeg|png)$/.test(value) ? value : null;
}
function usablePhoto(photo) {
  return Number.isInteger(photo.width) && Number.isInteger(photo.height) && photo.width > 0 && photo.height > 0 && safeImagePath(photo.large_url) && safeImagePath(photo.medium_url);
}
const selectedOptions = () => Object.fromEntries(controls.map(id => [id,$(id).value]));
const sizeText = box => `${box.width.toFixed(3)} × ${box.height.toFixed(3)} mm (${(box.width/25.4).toFixed(3)} × ${(box.height/25.4).toFixed(3)} in)`;
const surroundText = value => (Math.abs(value)<0.0005 ? 0 : value).toFixed(3);
function fillSelect(id, entries, value) {
  $(id).replaceChildren(...entries.map(([key,label]) => { const option=document.createElement('option'); option.value=key; option.textContent=label; return option; }));
  if (value) $(id).value=value;
}
function makePhotoChoice(photo) {
  const button=document.createElement('button'); button.type='button'; button.className='photo-choice'; button.dataset.photoId=photo.id;
  button.setAttribute('aria-pressed','false'); button.setAttribute('aria-label',`Study ${photo.title || 'Untitled photograph'} · TEST`);
  const stage=document.createElement('span'); stage.className='thumbnail';
  const image=document.createElement('img'); image.src=safeImagePath(photo.medium_url); image.alt=photo.alt_text || photo.title || 'Public photograph';
  image.width=photo.width; image.height=photo.height; image.loading='lazy'; stage.append(image);
  const title=document.createElement('strong'); title.textContent=photo.title || 'Untitled photograph';
  const action=document.createElement('span'); action.textContent='Explore print study ↗'; button.append(stage,title,action);
  button.addEventListener('click',()=>{selectPhoto(photo);$('photo-title').focus({preventScroll:true});$('study').scrollIntoView({block:'start'});});
  return button;
}
function selectPhoto(photo) {
  currentPhoto=photo; $('study').hidden=false;
  document.querySelectorAll('.photo-choice').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.photoId===String(photo.id))));
  ['selected-photo','plain-photo','print-photo'].forEach(id=>{const image=$(id);image.src=safeImagePath(photo.large_url);image.alt=photo.alt_text || photo.title || 'Public photograph';image.width=photo.width;image.height=photo.height;});
  $('photo-title').textContent=photo.title || 'Untitled photograph'; $('photo-seller').textContent=`Photograph by ${seller.name}`;
  $('pixel-size').textContent=`Source: ${photo.width.toLocaleString()} × ${photo.height.toLocaleString()} pixels · ratio ${(photo.width/photo.height).toFixed(6)}:1. Pixels are not paper dimensions.`;
  $('provenance').textContent=Object.values(photo.ai_disclosure || {}).some(Boolean) ? 'Some source gallery metadata is AI-drafted. The photograph is unchanged.' : '';
  renderStudy();
}
function setInset(node,outer,inner) {
  Object.assign(node.style,{left:`${(outer.width-inner.width)/2/outer.width*100}%`,top:`${(outer.height-inner.height)/2/outer.height*100}%`,width:`${inner.width/outer.width*100}%`,height:`${inner.height/outer.height*100}%`});
}
function drawComparison(geometry,options) {
  const fits=geometry.surround.left >= (geometry.pack.mat ? 31.75 : 12.7)-1e-8 && geometry.surround.top >= (geometry.pack.mat ? 31.75 : 12.7)-1e-8;
  $('comparison').hidden=!fits;
  $('diagram-status').textContent=fits ? '' : 'This image does not fit the proposed sheet / mat clearances. The package diagrams are withheld rather than cropping the photograph.';
  if (!fits) return;
  ['plain-paper','study-paper'].forEach(id=>$(id).style.aspectRatio=`${geometry.paper.width} / ${geometry.paper.height}`);
  ['plain-photo','print-photo'].forEach(id=>setInset($(id),geometry.paper,geometry.image));
  setInset($('printed-field'),geometry.paper,geometry.inkField);
  $('printed-field').className=`printed-field pattern-${options.pattern}`;
  $('study-paper').classList.toggle('with-frame',geometry.pack.frame);
  $('physical-mat').hidden=!geometry.pack.mat;
  if (geometry.pack.mat) {
    const horizontal=geometry.matSurround.left/geometry.paper.width*100, vertical=geometry.matSurround.top/geometry.paper.height*100;
    $('physical-mat').style.gridTemplateColumns=`${horizontal}% 1fr ${horizontal}%`;
    $('physical-mat').style.gridTemplateRows=`${vertical}% 1fr ${vertical}%`;
  }
  $('presentation-caption').textContent=`${patterns[options.pattern]} · ${packages[options.package].label}${geometry.pack.frame ? ' (frame outline schematic)' : ''}`;
}
function dimensionRow(label,value) {
  const row=document.createElement('div'),term=document.createElement('dt'),definition=document.createElement('dd');
  term.textContent=label;definition.textContent=value;row.append(term,definition);return row;
}
function renderMeasurements(geometry,options) {
  const rows=[['Image area',sizeText(geometry.image)],['Paper sheet outer',sizeText(geometry.paper)],['Unprinted paper edge',`${geometry.border.toFixed(3)} mm on each side`],['Printed artwork field',options.pattern==='plain' ? 'None · plain white paper' : sizeText(geometry.inkField)]];
  rows.push(['Physical mat window',geometry.matWindow ? `${sizeText(geometry.matWindow)} · no overlap assumed` : 'Not included'],['Physical mat outer',geometry.matOuter ? sizeText(geometry.matOuter) : 'Not included'],['Nominal frame / rabbet fit target',`${sizeText(geometry.frameFit)}${geometry.pack.frame ? ' · frame model unapproved' : ' · frame not included'}`],['Frame external size',geometry.pack.frame ? 'Unsettled · requires measured frame model' : 'Not included']);
  $('dimensions').replaceChildren(...rows.map(([label,value])=>dimensionRow(label,value)));
  const surrounds=[['Paper edge',Object.fromEntries(['top','bottom','left','right'].map(side=>[side,geometry.border]))],['Total image-to-paper surround',geometry.surround]];
  if(options.pattern!=='plain') surrounds.push(['Printed surround beyond white edge',Object.fromEntries(Object.entries(geometry.surround).map(([key,value])=>[key,value-geometry.border]))]);
  if(geometry.matSurround) surrounds.push(['Physical mat around window',geometry.matSurround]);
  $('surrounds').replaceChildren(...surrounds.map(([label,values])=>{const row=document.createElement('tr');const term=document.createElement('th');term.scope='row';term.textContent=label;row.append(term);['top','bottom','left','right'].forEach(side=>{const cell=document.createElement('td');cell.textContent=surroundText(values[side]);row.append(cell);});return row;}));
  $('sheet-note').textContent=`${geometry.annotated} The image is centred; negative surrounds indicate an invalid fit, not a crop. Physical window reveals 6.35 mm beyond each image edge in this study; cut tolerances, overlap and depth remain unapproved.`;
}
function listItems(items) {
  return items.map(text=>{const item=document.createElement('li');item.textContent=text;return item;});
}
function renderBuyer(geometry,options) {
  const summary=packageSummary(options);
  $('buyer-size').textContent=`Image ${sizeText(geometry.image)} on paper ${sizeText(geometry.paper)}. ${geometry.warnings.length ? 'Fit constraints below need resolution.' : 'Geometric fit only; no proven print recipe.'}`;
  $('included').replaceChildren(...listItems(summary.included)); $('excluded').replaceChildren(...listItems(summary.excluded));
  const status=['material','signing','price','fulfilment'].map(id=>`${({material:'Paper / finish',signing:'Signing',price:'Price',fulfilment:'Fulfilment / destination'})[id]}: ${$(id).selectedOptions[0].textContent}`);
  $('buyer-unsettled').textContent=`${status.join(' · ')}. All choices are illustrative and unapproved.`;
  $('contact-print').href=`mailto:adrianhensler@gmail.com?subject=${encodeURIComponent(`TEST print enquiry: ${currentPhoto.title || 'Untitled photograph'}`)}`;
}
function renderGuidance(geometry,options) {
  $('fit-warnings').replaceChildren(...listItems(geometry.warnings));
  const decorated=options.pattern!=='plain';
  $('guidance-text').textContent=`Simulated suggestion: keep the photograph’s ${(currentPhoto.width/currentPhoto.height).toFixed(6)}:1 ratio. ${decorated ? 'The printed design is artwork outside the photo, not a physical mat.' : 'Plain paper is a useful proof baseline.'} ${options.printer==='fineart' ? `The 25 mm feed-end check permits at most ${(geometry.endLimit/25.4).toFixed(3)} in along this sheet’s long edge; decorative ink must also respect those exclusions.` : 'A frame-fit target does not prove the selected paper/driver can print it.'} Paper/finish, colour proof, package and delivery still need Adrian’s real approval.`;
}
function updateApproval() {
  const count=document.querySelectorAll('#review-checklist input:checked').length;
  $('approval-status').textContent=`${count}/${reviewPoints.length} marked in this local simulation only. NOT seller-approved. No physical proof is recorded; no approval, product or publication is saved. TEST / not for sale.`;
}
function renderStudy() {
  if(!currentPhoto) return;
  const options=selectedOptions(),geometry=layoutVariant(currentPhoto.width,currentPhoto.height,options);
  document.querySelectorAll('#review-checklist input').forEach(input=>input.checked=false);
  drawComparison(geometry,options);renderMeasurements(geometry,options);renderBuyer(geometry,options);renderGuidance(geometry,options);updateApproval();
}
function showPerspective(name) {
  ['buyer','seller'].forEach(perspective=>{$(`${perspective}-panel`).hidden=perspective!==name;$(`${perspective}-tab`).setAttribute('aria-pressed',String(perspective===name));});
}
async function loadCollection() {
  try {
    const response=await fetch(`/api/gallery/published?user_id=${seller.userId}`,{credentials:'omit'});
    if(!response.ok) throw new Error('Unavailable');
    const data=await response.json(),available=(Array.isArray(data.images)?data.images:[]).filter(usablePhoto);
    const curated=seller.samples.map(id=>available.find(photo=>photo.id===id)).filter(Boolean),photos=curated.length?curated:available.slice(0,4);
    if(!photos.length) throw new Error('Empty');
    $('collection').replaceChildren(...photos.map(makePhotoChoice));$('load-status').textContent='';selectPhoto(photos[0]);
  } catch(error) { $('load-status').textContent='This public collection could not be loaded. Please visit the real gallery. No order can be placed.'; }
}
fillSelect('seller',[[seller.id,`${seller.name} · current TEST study`]]);$('seller').disabled=true;
fillSelect('sheet',sheets.map(sheet=>[sheet.id,sheet.label]),'13x19');
fillSelect('pattern',Object.entries(patterns),'plain');
fillSelect('package',Object.entries(packages).map(([id,pack])=>[id,pack.label]),'print');
reviewPoints.forEach((text,index)=>{const label=document.createElement('label'),input=document.createElement('input'),span=document.createElement('span');input.type='checkbox';input.id=`review-${index}`;input.addEventListener('change',updateApproval);span.textContent=text;label.append(input,span);$('review-checklist').append(label);});
controls.forEach(id=>$(id).addEventListener('change',renderStudy));
$('buyer-tab').addEventListener('click',()=>showPerspective('buyer'));$('seller-tab').addEventListener('click',()=>showPerspective('seller'));
loadCollection();
