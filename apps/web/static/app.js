const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const video = $('#video');
const sound = $('#sound');
const toggle = $('#toggle');
const bars = $('#bars');
const map = $('#map');
const ROWS = 3;
const COLS = 4;
const BANDS = ROWS * COLS;
const PAINT = { ink: '#efeae0', raw: '#5d5a54', amber: '#f2a541', teal: '#5cc8b8', grid: '#26262b', muted: '#9a958b' };
const TOUR_SECONDS = 7;

let current = null; // { entry, analysis }
let lastState = -1;
let band = 0;

// Banda 0 (graves) abajo a la izquierda, banda 11 (agudos) arriba a la derecha: igual que pipeline.bandCell.
const slotOf = (index) => (ROWS - 1 - Math.floor(index / COLS)) * COLS + (index % COLS);
const rgb = (color) => `rgb(${color.join(',')})`;
const hz = (value) => (value >= 1000 ? `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)} kHz` : `${Math.round(value)} Hz`);
const time = (seconds, decimals = 1) => {
  const safe = Math.max(0, seconds || 0);
  return `${Math.floor(safe / 60)}:${(safe % 60).toFixed(decimals).padStart(decimals ? 3 + decimals : 2, '0')}`;
};
const fill = (key, text) => $$(`[data-fill="${key}"]`).forEach((node) => { node.textContent = text; });
const tier = (value) => (value < 0.34 ? 0 : value < 0.67 ? 1 : 2);
const describe = (state) => `Energía ${['baja', 'media', 'alta'][tier(state.energy)]}, brillo ${['grave', 'medio', 'agudo'][tier(state.brightness)]}, ${['pocos golpes', 'golpes moderados', 'muchos golpes'][tier(state.attacks)]}`;

function numberedGrid(container) {
  const cells = Array.from({ length: BANDS }, () => document.createElement('span'));
  for (let index = 0; index < BANDS; index += 1) cells[slotOf(index)].textContent = String(index + 1);
  container.replaceChildren(...cells);
}

function buildStatic() {
  for (let index = 0; index < BANDS; index += 1) bars.appendChild(document.createElement('span'));
  numberedGrid(map);
  numberedGrid($('#s8-grid'));
  $$('[data-band]').forEach((select) => {
    for (let index = 0; index < BANDS; index += 1) select.add(new Option(String(index + 1), String(index)));
    select.addEventListener('change', () => {
      band = Number(select.value);
      $$('[data-band]').forEach((other) => { other.value = select.value; });
      drawBandCharts();
    });
  });
}

// ---------- Lectura en vivo ----------
function frameIndex() {
  const count = current.analysis.frames.bands.length;
  return Math.min(count - 1, Math.max(0, Math.floor(video.currentTime * current.analysis.fps)));
}

function paint() {
  requestAnimationFrame(paint);
  if (!current) return;
  const { analysis } = current;
  const index = frameIndex();
  analysis.frames.bands[index].forEach((value, i) => {
    bars.children[i].style.transform = `scaleY(${Math.max(0.02, value)})`;
    map.children[slotOf(i)].style.background = `rgba(0,0,0,${(0.78 - 0.74 * value).toFixed(3)})`;
  });
  const flash = analysis.frames.flash[index];
  const dot = $('#flash-dot');
  dot.style.opacity = String(0.08 + 0.92 * flash);
  dot.style.boxShadow = flash > 0.2 ? `0 0 ${Math.round(22 * flash)}px var(--state)` : 'none';
  setState(analysis.frames.state[index]);
  const progress = Math.min(1, video.currentTime / analysis.durationSeconds);
  $('#clock').textContent = `${time(video.currentTime)} / ${time(analysis.durationSeconds)}`;
  $('#scrub-fill').style.width = `${progress * 100}%`;
  $$('.plot .head').forEach((head) => { head.style.left = `${progress * 100}%`; });
}

function setState(stateId) {
  if (stateId === lastState) return;
  lastState = stateId;
  const state = current.analysis.states[stateId];
  if (!state) return;
  document.documentElement.style.setProperty('--state', rgb(state.rgb));
  fill('stateName', state.name);
  fill('stateDesc', describe(state));
  $$('#states article').forEach((card, index) => card.classList.toggle('on', index === stateId));
}

// ---------- Gráficas ----------
function canvasFor(id) {
  const canvas = $(id);
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 600;
  const height = canvas.clientHeight || 120;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const context = canvas.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function heat(value) {
  const stops = [[15, 15, 18], [92, 38, 30], [242, 165, 65], [250, 240, 214]];
  const scaled = Math.min(0.999, Math.max(0, value)) * (stops.length - 1);
  const low = Math.floor(scaled);
  const mix = scaled - low;
  return `rgb(${stops[low].map((channel, i) => Math.round(channel + (stops[low + 1][i] - channel) * mix)).join(',')})`;
}

function plotLines(id, series, { min = 0, max = 1, marks = [] } = {}) {
  const { context, width, height } = canvasFor(id);
  const pad = 8;
  const y = (value) => height - pad - ((value - min) / Math.max(1e-9, max - min)) * (height - pad * 2);
  context.lineWidth = 1;
  context.strokeStyle = PAINT.grid;
  [min, (min + max) / 2, max].forEach((level) => {
    context.beginPath(); context.moveTo(0, y(level)); context.lineTo(width, y(level)); context.stroke();
  });
  context.setLineDash([4, 4]);
  context.strokeStyle = PAINT.muted;
  context.fillStyle = PAINT.muted;
  context.font = '11px "JetBrains Mono", monospace';
  marks.forEach(({ value, label }) => {
    context.beginPath(); context.moveTo(0, y(value)); context.lineTo(width, y(value)); context.stroke();
    context.fillText(label, 6, y(value) - 4);
  });
  context.setLineDash([]);
  series.forEach(({ values, color, lineWidth = 1.6, area = false }) => {
    const x = (index) => (index / Math.max(1, values.length - 1)) * width;
    context.beginPath();
    values.forEach((value, index) => {
      const point = y(Math.min(max, Math.max(min, value)));
      if (index === 0) context.moveTo(x(index), point); else context.lineTo(x(index), point);
    });
    if (area) {
      context.lineTo(width, y(min)); context.lineTo(0, y(min)); context.closePath();
      context.fillStyle = `${color}40`; context.fill();
    } else {
      context.strokeStyle = color; context.lineWidth = lineWidth; context.stroke();
    }
  });
  return { context, width, height };
}

function drawInput() {
  const { entry, analysis } = current;
  const { input, segmentStart, durationSeconds } = analysis;
  const { context, width, height } = canvasFor('#c-input');
  const from = (segmentStart / input.durationSeconds) * width;
  const to = ((segmentStart + durationSeconds) / input.durationSeconds) * width;
  context.fillStyle = 'rgba(242,165,65,.1)';
  context.fillRect(from, 0, to - from, height);
  const step = width / input.envelope.length;
  input.envelope.forEach((value, index) => {
    const x = index * step;
    const bar = Math.max(1, value * (height - 16));
    context.fillStyle = x >= from && x <= to ? PAINT.amber : PAINT.raw;
    context.fillRect(x, (height - bar) / 2, Math.max(1, step - 1), bar);
  });
  const [x0, y0, x1, y1] = input.crop;
  Object.assign($('#s1-box').style, { left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` });
  $('#s1-img').src = entry.imageUrl;
  fill('imageCaption', `Original de ${input.imageSize[0]} × ${input.imageSize[1]} px. El recuadro es la zona usada.`);
  fill('audioCaption', `Audio de ${time(input.durationSeconds, 0)}. En color, el tramo usado: ${time(segmentStart, 0)}–${time(segmentStart + durationSeconds, 0)}.`);
}

function drawPalette() {
  const { palette } = current.analysis;
  $('#palette').replaceChildren(...palette.map(({ rgb: color, weight }) => {
    const swatch = document.createElement('span');
    swatch.style.background = rgb(color);
    swatch.style.flex = String(weight);
    swatch.textContent = `${Math.round(weight * 100)}%`;
    return swatch;
  }));
  $('#vivid').replaceChildren(...[...palette].sort((a, b) => a.vividRank - b.vividRank).map(({ rgb: color }, index) => {
    const swatch = document.createElement('span');
    swatch.style.background = rgb(color);
    swatch.textContent = String(index + 1);
    return swatch;
  }));
}

function drawSpectrogram() {
  const frames = current.analysis.frames.bandsDb;
  const { context, width, height } = canvasFor('#c-spec');
  const rowHeight = height / BANDS;
  const columnWidth = width / frames.length;
  frames.forEach((frame, column) => {
    frame.forEach((db, index) => {
      context.fillStyle = heat((db + 80) / 80);
      context.fillRect(column * columnWidth, (BANDS - 1 - index) * rowHeight, columnWidth + 0.6, rowHeight + 0.6);
    });
  });
}

function drawBandCharts() {
  if (!current) return;
  const { frames, bandDbRange, bandEdgesHz } = current.analysis;
  const db = frames.bandsDb.map((frame) => frame[band]);
  const [p5, p95] = bandDbRange[band];
  plotLines('#c-db', [{ values: db, color: PAINT.muted, lineWidth: 1.2 }], {
    min: Math.min(...db, p5) - 3,
    max: Math.max(...db, p95) + 3,
    marks: [{ value: p5, label: `p5 ${p5.toFixed(0)} dB` }, { value: p95, label: `p95 ${p95.toFixed(0)} dB` }],
  });
  plotLines('#c-norm', [{ values: frames.bandsRaw.map((frame) => frame[band]), color: PAINT.amber, lineWidth: 1.4 }]);
  plotLines('#c-smooth', [
    { values: frames.bandsRaw.map((frame) => frame[band]), color: PAINT.raw, lineWidth: 1.2 },
    { values: frames.bands.map((frame) => frame[band]), color: PAINT.amber, lineWidth: 2 },
  ]);
  fill('bandRange', `${hz(bandEdgesHz[band])}–${hz(bandEdgesHz[band + 1])}`);
}

function drawOnsets() {
  const { frames, onsetTimes, durationSeconds } = current.analysis;
  const { context, width } = plotLines('#c-onset', [
    { values: frames.flash, color: PAINT.teal, area: true },
    { values: frames.onset, color: PAINT.amber, lineWidth: 1.3 },
  ]);
  context.fillStyle = PAINT.ink;
  onsetTimes.forEach((moment) => context.fillRect((moment / durationSeconds) * width, 0, 1.5, 6));
}

function drawStateStrip(id) {
  const { frames, states } = current.analysis;
  const { context, width, height } = canvasFor(id);
  const step = width / frames.state.length;
  frames.state.forEach((stateId, index) => {
    context.fillStyle = rgb(states[stateId]?.rgb || [80, 80, 80]);
    context.fillRect(index * step, 0, step + 0.6, height);
  });
}

function drawStates() {
  $('#states').replaceChildren(...current.analysis.states.map((state) => {
    const card = document.createElement('article');
    const swatch = document.createElement('i');
    swatch.style.background = rgb(state.rgb);
    const title = document.createElement('strong');
    title.textContent = state.name;
    const detail = document.createElement('small');
    detail.textContent = `${describe(state)}. ${Math.round(state.share * 100)} % del audio analizado.`;
    card.append(swatch, title, detail);
    return card;
  }));
  lastState = -1;
}

function drawSync() {
  const { frames, syncScore } = current.analysis;
  const lum = frames.luminance;
  const lo = Math.min(...lum);
  const hi = Math.max(...lum);
  plotLines('#c-sync', [
    { values: lum.map((value) => (value - lo) / Math.max(1e-6, hi - lo)), color: PAINT.teal, lineWidth: 1.3 },
    { values: frames.onset, color: PAINT.amber, lineWidth: 1.3 },
  ]);
  fill('sync', syncScore.toFixed(2));
}

function drawAll() {
  if (!current) return;
  drawStateStrip('#c-live-states');
  drawInput();
  drawSpectrogram();
  drawBandCharts();
  drawOnsets();
  drawStateStrip('#c-states');
  drawSync();
}

// ---------- Ejemplos ----------
async function show(entry) {
  const response = await fetch(entry.analysisUrl);
  if (!response.ok) throw new Error('No se pudo leer el análisis.');
  const analysis = await response.json();
  current = { entry, analysis };
  video.poster = entry.posterUrl || '';
  video.src = entry.videoUrl;
  video.play().catch(() => toggle.classList.add('paused'));
  map.style.backgroundImage = `url("${entry.posterUrl}")`;
  $('#s8-img').src = entry.posterUrl;
  const edges = analysis.bandEdgesHz;
  fill('bandLo', hz(edges[0]));
  fill('bandMid', hz(edges[Math.round(edges.length / 2)]));
  fill('bandHi', hz(edges.at(-1)));
  fill('onsetCount', String(analysis.onsetTimes.length));
  $('#tempo').textContent = `${Math.round(analysis.tempo)} BPM`;
  $('#source-line').textContent = `Audio: ${entry.title} · Imagen: ${entry.imageName}`;
  $$('.demo').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.id === entry.id)));
  drawPalette();
  drawStates();
  drawAll();
}

function addDemoButton(entry, custom = false) {
  if (custom) $('.demo[data-custom]')?.remove();
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'demo';
  button.dataset.id = entry.id;
  button.setAttribute('aria-pressed', 'false');
  if (custom) button.dataset.custom = 'true';
  const image = document.createElement('img');
  image.src = entry.posterUrl;
  image.alt = '';
  image.loading = 'lazy';
  const text = document.createElement('div');
  const title = document.createElement('strong');
  title.textContent = entry.title;
  const mood = document.createElement('small');
  mood.textContent = entry.mood;
  text.append(title, mood);
  button.append(image, text);
  button.addEventListener('click', () => show(entry).catch(showError));
  $('#demos').appendChild(button);
}

function showError(error) {
  $('#source-line').textContent = error.message || 'No se pudo cargar la demo.';
}

async function loadDemos() {
  const response = await fetch('/api/demo');
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || 'No se pudo cargar la demo.');
  (payload.demos || []).forEach((entry) => addDemoButton(entry));
  fill('credits', payload.credits || '');
  if (payload.demos?.length) await show(payload.demos[0]);
}

// ---------- Reproductor ----------
function playWithSound() {
  video.muted = false;
  video.currentTime = 0;
  video.play();
}
sound.addEventListener('click', playWithSound);
video.addEventListener('volumechange', () => { sound.hidden = !video.muted; });
video.addEventListener('play', () => { toggle.classList.remove('paused'); toggle.setAttribute('aria-label', 'Pausar'); });
video.addEventListener('pause', () => { toggle.classList.add('paused'); toggle.setAttribute('aria-label', 'Reproducir'); });
toggle.addEventListener('click', () => (video.paused ? video.play() : video.pause()));
function seekFrom(element, event) {
  if (!current) return;
  const box = element.getBoundingClientRect();
  video.currentTime = ((event.clientX - box.left) / box.width) * current.analysis.durationSeconds;
}
$('#scrub').addEventListener('click', (event) => seekFrom($('#scrub'), event));
$$('.step .plot').forEach((plot) => plot.addEventListener('click', (event) => seekFrom(plot, event)));
let resizeTimer = null;
window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawAll, 150); });

// ---------- Navegación por pasos ----------
const steps = $$('.step');
const navLinks = $$('.step-nav a, .flow a');
const observer = new IntersectionObserver((entries) => {
  entries.filter((entry) => entry.isIntersecting).forEach((entry) => {
    // Los enlaces del SVG no exponen `hash`; se compara el atributo href.
    navLinks.forEach((link) => link.classList.toggle('on', link.getAttribute('href') === `#${entry.target.id}`));
  });
}, { rootMargin: '-40% 0px -55% 0px' });
steps.forEach((step) => observer.observe(step));

let tourTimer = null;
function stopTour() {
  clearTimeout(tourTimer);
  tourTimer = null;
  steps.forEach((step) => step.classList.remove('touring'));
  $('#tour').setAttribute('aria-pressed', 'false');
  $('#tour').textContent = 'Recorrer los pasos';
}
function tourTo(index) {
  steps.forEach((step, i) => step.classList.toggle('touring', i === index));
  if (index >= steps.length) { stopTour(); return; }
  steps[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
  tourTimer = setTimeout(() => tourTo(index + 1), TOUR_SECONDS * 1000);
}
$('#tour').addEventListener('click', () => {
  if (tourTimer) { stopTour(); return; }
  $('#tour').setAttribute('aria-pressed', 'true');
  $('#tour').textContent = 'Detener';
  playWithSound();
  tourTo(0);
});
window.addEventListener('wheel', () => tourTimer && stopTour(), { passive: true });

// ---------- Archivos propios ----------
const dialog = $('#upload');
const uploadError = $('#upload-error');
$('#open-upload').addEventListener('click', () => { uploadError.textContent = ''; dialog.showModal(); });
$('#upload-cancel').addEventListener('click', () => dialog.close());
$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const image = $('#up-image').files[0];
  const audio = $('#up-audio').files[0];
  if (!image || !audio) { uploadError.textContent = 'Elige una imagen y un audio.'; return; }
  const body = new FormData();
  body.append('image', image);
  body.append('audio', audio);
  $('#upload-go').disabled = true;
  uploadError.textContent = '';
  try {
    const response = await fetch('/api/render', { method: 'POST', body });
    const job = await response.json();
    if (!response.ok) throw new Error(job.detail || 'No se pudo iniciar el render.');
    dialog.close();
    await followJob(job.id, image, audio);
  } catch (error) {
    uploadError.textContent = error.message;
    if (!dialog.open) dialog.showModal();
  } finally {
    $('#upload-go').disabled = false;
  }
});

async function followJob(jobId, image, audio) {
  const busy = $('#busy');
  busy.hidden = false;
  video.pause();
  try {
    for (;;) {
      const response = await fetch(`/api/jobs/${jobId}`);
      const job = await response.json();
      $('#busy-phase').textContent = `${job.phase || 'Procesando'}…`;
      $('#busy-bar').style.width = `${job.progress || 0}%`;
      if (job.status === 'failed') throw new Error(job.error || 'El render falló.');
      if (job.status === 'completed') {
        const entry = {
          id: jobId,
          title: 'Tus archivos',
          mood: `${audio.name} + ${image.name}`,
          imageName: image.name,
          imageUrl: URL.createObjectURL(image),
          videoUrl: job.outputUrl,
          posterUrl: job.posterUrl,
          analysisUrl: job.analysisUrl,
        };
        addDemoButton(entry, true);
        await show(entry);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
  } finally {
    busy.hidden = true;
  }
}

buildStatic();
requestAnimationFrame(paint);
loadDemos().catch(showError);
