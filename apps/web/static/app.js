const feedback = document.querySelector('#render-feedback');
const demoMeta = document.querySelector('#demo-meta');
const demoSelector = document.querySelector('#demo-selector');
const demoVideo = document.querySelector('#demo-video');
const demoImage = document.querySelector('#demo-image');
const demoRender = document.querySelector('#demo-render');
const demoImageGrid = document.querySelector('#demo-image-grid');
const renderProcess = document.querySelector('#render-process');
const renderPhase = document.querySelector('#render-phase');
let selectedDemo = null;
let selectedImageUrl = null;
let activeAnalysis = null;
let analysisAnimationId = null;
let analysisAnimationStart = 0;
let analysisAnimationOffset = 0;

const analysisControls = document.querySelector('#analysis-controls');
const analysisPlay = document.querySelector('#analysis-play');
const analysisTime = document.querySelector('#analysis-time');
const analysisReadout = document.querySelector('#analysis-readout');

function drawWaveform(values) {
  const canvas = document.querySelector('#pipeline-waveform');
  if (!canvas || !values?.length) return;
  const context = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const middle = height / 2;
  const scale = Math.max(...values.map((value) => Math.abs(Number(value) || 0)), 1e-9);
  context.clearRect(0, 0, width, height);
  context.fillStyle = '#17202a';
  context.fillRect(0, 0, width, height);
  context.strokeStyle = '#52606d';
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(0, middle);
  context.lineTo(width, middle);
  context.stroke();
  context.strokeStyle = '#39a394';
  context.lineWidth = 2;
  context.beginPath();
  values.forEach((value, index) => {
    const x = index * width / Math.max(1, values.length - 1);
    const y = middle - (Number(value) || 0) / scale * (middle - 12);
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  context.stroke();
}

function drawNormalization(rawValues, normalizedValues) {
  const canvas = document.querySelector('#pipeline-normalization');
  if (!canvas || !rawValues?.length || !normalizedValues?.length) return;
  const context = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 16;
  const rawMax = Math.max(...rawValues.map((value) => Number(value) || 0), 1e-9);
  context.clearRect(0, 0, width, height);
  context.fillStyle = '#17202a';
  context.fillRect(0, 0, width, height);
  context.strokeStyle = '#52606d';
  context.lineWidth = 1;
  [0, .5, 1].forEach((level) => {
    const y = height - padding - level * (height - padding * 2);
    context.beginPath();
    context.moveTo(padding, y);
    context.lineTo(width - padding, y);
    context.stroke();
  });
  const drawLine = (values, color, scale = 1) => {
    context.strokeStyle = color;
    context.lineWidth = 2;
    context.beginPath();
    values.forEach((value, index) => {
      const x = padding + index * (width - padding * 2) / Math.max(1, values.length - 1);
      const y = height - padding - ((Number(value) || 0) / scale) * (height - padding * 2);
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.stroke();
  };
  drawLine(rawValues, '#39a394', rawMax);
  drawLine(normalizedValues, '#e39b3b');
}

function renderAnalysisFrame(index = 0) {
  if (!activeAnalysis?.melBands?.length) return;
  const frameIndex = Math.max(0, Math.min(activeAnalysis.melBands.length - 1, Number(index) || 0));
  const frame = activeAnalysis.melBands[frameIndex] || [];
  const rawRms = activeAnalysis.rawRms || [];
  const rms = activeAnalysis.rms || [];
  const progress = frameIndex / Math.max(1, activeAnalysis.melBands.length - 1);
  document.querySelectorAll('#pipeline-bands span').forEach((bar, bandIndex) => {
    bar.style.height = `${18 + Number(frame[bandIndex] || 0) * 80}%`;
  });
  const peakValue = Math.max(...frame.map((value) => Number(value) || 0), 0);
  const peakBand = frame.indexOf(peakValue);
  const melReadout = document.querySelector('#mel-readout');
  if (melReadout) melReadout.textContent = `Pico de energía: banda ${peakBand + 1} · ${peakValue.toFixed(2)}`;
  const cursor = document.querySelector('#frequency-cursor');
  if (cursor) cursor.style.left = `${progress * 100}%`;
  const waveformCursor = document.querySelector('#waveform-cursor');
  if (waveformCursor) waveformCursor.style.left = `${progress * 100}%`;
  const normalizationCursor = document.querySelector('#normalization-cursor');
  if (normalizationCursor) normalizationCursor.style.left = `${progress * 100}%`;
  if (analysisTime) analysisTime.value = String(frameIndex);
  const time = Number(activeAnalysis.times?.[frameIndex] || 0);
  if (analysisReadout) analysisReadout.textContent = `${time.toFixed(2)} s · ventana ${frameIndex + 1}/${activeAnalysis.melBands.length}`;
  const rmsReadout = document.querySelector('#rms-readout');
  if (rmsReadout) rmsReadout.textContent = `RMS bruto ${Number(rawRms[frameIndex] || 0).toFixed(4)} · normalizado ${Number(rms[frameIndex] || 0).toFixed(4)}`;
}

function syncAnalysisToVideo() {
  if (!activeAnalysis || !Number.isFinite(demoVideo.currentTime)) return;
  const times = activeAnalysis.times || [];
  if (!times.length) return;
  let frameIndex = 0;
  while (frameIndex < times.length - 1 && times[frameIndex + 1] <= demoVideo.currentTime) frameIndex += 1;
  renderAnalysisFrame(frameIndex);
}

function stopAnalysisPlayback() {
  if (analysisAnimationId !== null) cancelAnimationFrame(analysisAnimationId);
  analysisAnimationId = null;
}

function startAnalysisPlayback() {
  if (!activeAnalysis?.times?.length) return;
  stopAnalysisPlayback();
  const duration = Number(activeAnalysis.times.at(-1) || 0);
  analysisAnimationStart = performance.now() - analysisAnimationOffset * 1000;
  const tick = (now) => {
    const elapsed = Math.min(duration, (now - analysisAnimationStart) / 1000);
    analysisAnimationOffset = elapsed;
    let frameIndex = 0;
    while (frameIndex < activeAnalysis.times.length - 1 && activeAnalysis.times[frameIndex + 1] <= elapsed) frameIndex += 1;
    renderAnalysisFrame(frameIndex);
    if (Number.isFinite(demoVideo.duration)) demoVideo.currentTime = elapsed;
    if (elapsed < duration) {
      analysisAnimationId = requestAnimationFrame(tick);
    } else {
      analysisAnimationId = null;
      analysisAnimationOffset = 0;
      if (analysisPlay) analysisPlay.textContent = 'Reproducir proceso';
    }
  };
  analysisPlay.textContent = 'Pausar proceso';
  analysisAnimationId = requestAnimationFrame(tick);
}

function buildPipelineVisuals() {
  for (let index = 0; index < 12; index += 1) {
    const band = document.createElement('span');
    band.style.height = '0%';
    document.querySelector('#pipeline-bands').appendChild(band);
  }
  for (let index = 0; index < 24; index += 1) {
    const tile = document.createElement('span');
    tile.style.setProperty('--tile-index', index);
    document.querySelector('#pipeline-grid').appendChild(tile);
  }
  const context = document.querySelector('#pipeline-spectrogram').getContext('2d');
  context.fillStyle = '#17202a';
  context.fillRect(0, 0, 240, 84);
}

function updatePipelineVisual(progress = 0, complete = false, mlEnabled = false) {
  const currentStage = complete ? (mlEnabled ? 6 : 5) : progress >= 95 ? 5 : progress >= 40 ? 4 : progress >= 35 ? 3 : progress >= 15 ? 2 : 1;
  document.querySelectorAll('[data-visual-stage]').forEach((stage) => {
    const stageNumber = Number(stage.dataset.visualStage);
    stage.classList.toggle('visual-active', stageNumber === currentStage && !complete);
    stage.classList.toggle('visual-done', stageNumber <= currentStage && complete);
  });
  const outputState = document.querySelector('#output-state');
  outputState.textContent = complete ? 'MP4 listo' : progress ? `${progress}% en proceso` : 'Esperando render';
}

function updateGridImage(imageUrl) {
  if (!imageUrl) return;
  const grid = document.querySelector('#pipeline-grid');
  grid.classList.remove('has-preview');
  grid.style.backgroundImage = 'none';
  document.querySelectorAll('#pipeline-grid span').forEach((tile, index) => {
    const column = index % 6;
    const row = Math.floor(index / 6);
    tile.style.backgroundImage = `url(${imageUrl})`;
    tile.style.backgroundPosition = `${column * 20}% ${row * 33.333}%`;
  });
}

async function loadAnalysis(analysisUrl) {
  if (!analysisUrl) return;
  const response = await fetch(analysisUrl);
  if (!response.ok) return;
  const analysis = await response.json();
  activeAnalysis = analysis;
  if (analysisControls) analysisControls.hidden = false;
  if (analysisTime) {
    analysisTime.max = String(Math.max(0, (analysis.melBands || []).length - 1));
    analysisTime.value = '0';
  }
  const rms = analysis.rms || [];
  const waveform = analysis.waveform || [];
  const melBands = analysis.melBands || [];
  const spectrogram = document.querySelector('#pipeline-spectrogram');
  const context = spectrogram.getContext('2d');
  context.clearRect(0, 0, spectrogram.width, spectrogram.height);
  context.fillStyle = '#17202a';
  context.fillRect(0, 0, spectrogram.width, spectrogram.height);
  const columns = Math.min(120, melBands.length);
  const rows = 12;
  for (let column = 0; column < columns; column += 1) {
    const sourceIndex = Math.floor(column * melBands.length / columns);
    const frame = melBands[sourceIndex] || [];
    for (let row = 0; row < rows; row += 1) {
      const value = Number(frame[row] || 0);
      const lightness = 14 + Math.round(value * 58);
      context.fillStyle = `hsl(${178 - row * 8}, 70%, ${lightness}%)`;
      context.fillRect(column * spectrogram.width / columns, (rows - row - 1) * spectrogram.height / rows,
        Math.ceil(spectrogram.width / columns), Math.ceil(spectrogram.height / rows));
    }
  }
  document.querySelectorAll('#pipeline-wave span').forEach((bar, index, bars) => {
    const sourceIndex = Math.floor(index * waveform.length / bars.length);
    bar.style.height = `${18 + Math.abs(waveform[sourceIndex] || 0) * 80}%`;
  });
  document.querySelectorAll('#raw-bars span').forEach((bar, index) => {
    const rawValues = analysis.rawRms || [];
    const sourceIndex = Math.floor(index * rawValues.length / Math.max(1, document.querySelectorAll('#raw-bars span').length));
    const rawMax = Math.max(...rawValues, 1e-9);
    bar.style.height = `${18 + ((rawValues[sourceIndex] || 0) / rawMax) * 80}%`;
  });
  document.querySelectorAll('#normalized-bars span').forEach((bar, index) => {
    const sourceIndex = Math.floor(index * rms.length / Math.max(1, document.querySelectorAll('#normalized-bars span').length));
    const normalizedValue = rms[sourceIndex] || 0;
    bar.style.height = `${18 + normalizedValue * 80}%`;
  });
  drawWaveform(waveform);
  drawNormalization(analysis.rawRms || [], rms);
  const inputReadout = document.querySelector('#input-readout');
  const image = document.querySelector('#pipeline-image');
  const duration = Number(analysis.times?.at(-1) || 0);
  const paletteCount = analysis.palette?.colors?.length || 0;
  if (inputReadout) inputReadout.textContent = `WAV · ${duration.toFixed(2)} s · ${melBands.length} ventanas · imagen ${image?.naturalWidth || '—'} × ${image?.naturalHeight || '—'} px · ${paletteCount} colores extraídos`;
  const palette = document.querySelector('#image-palette');
  if (palette) {
    palette.replaceChildren();
    (analysis.palette?.colors || []).forEach((color, index) => {
      const swatch = document.createElement('span');
      swatch.title = `Color ${index + 1}: rgb(${color.join(', ')})`;
      swatch.style.background = `rgb(${color.join(',')})`;
      palette.appendChild(swatch);
    });
  }
  renderAnalysisFrame(0);
  const clusterVisual = document.querySelector('#kmeans-visual');
  clusterVisual.replaceChildren();
  (analysis.states || []).forEach((state) => {
    const dot = document.createElement('span');
    dot.title = `${state.name} · intensidad ${Number(state.intensity).toFixed(2)}`;
    dot.style.background = `rgb(${state.color.join(',')})`;
    clusterVisual.appendChild(dot);
  });
  document.querySelector('#kmeans-state').textContent = analysis.states?.length ? `${analysis.states.length} estados agrupados` : 'sin ML en esta ruta';
}

function setMappingPreview(mappingUrl) {
  const grid = document.querySelector('#pipeline-grid');
  if (!grid || !mappingUrl) return;
  grid.style.backgroundImage = `url(${mappingUrl})`;
  grid.classList.add('has-preview');
}

demoVideo.addEventListener('timeupdate', syncAnalysisToVideo);
demoVideo.addEventListener('play', () => {
  if (analysisPlay) analysisPlay.textContent = 'Pausar proceso';
});
demoVideo.addEventListener('pause', () => {
  if (analysisAnimationId === null && analysisPlay) analysisPlay.textContent = 'Reproducir proceso';
});
demoVideo.addEventListener('ended', () => {
  stopAnalysisPlayback();
  if (analysisPlay) analysisPlay.textContent = 'Reproducir proceso';
});
analysisTime?.addEventListener('input', () => {
  const frameIndex = Number(analysisTime.value);
  renderAnalysisFrame(frameIndex);
  const time = Number(activeAnalysis?.times?.[frameIndex] || 0);
  analysisAnimationOffset = time;
  stopAnalysisPlayback();
  if (analysisPlay) analysisPlay.textContent = 'Reproducir proceso';
  if (Number.isFinite(time)) demoVideo.currentTime = time;
});
analysisPlay?.addEventListener('click', () => {
  if (analysisAnimationId === null) {
    startAnalysisPlayback();
    demoVideo.play().catch(() => {});
  } else {
    stopAnalysisPlayback();
    demoVideo.pause();
    if (analysisPlay) analysisPlay.textContent = 'Reproducir proceso';
  }
});

function selectDemo(demo) {
  selectedDemo = demo;
  demoVideo.src = demo.videoUrl;
  demoVideo.load();
  updatePipelineVisual(0, true, demo.mlEnabled !== false);
  updateGridImage(selectedImageUrl);
  loadAnalysis(demo.analysisUrl);
  setMappingPreview(demo.mappingUrl);
  demoMeta.textContent = `Video preparado · ${demo.description || 'Audio público'} · ${demo.durationSeconds || 20} s · ${demo.mlEnabled !== false ? 'ML activado' : 'modo determinista'}`;
}

async function renderWithImage(imageFile, audioUrl) {
  if ((!imageFile && !selectedImageUrl) || !audioUrl) {
    demoMeta.textContent = 'Selecciona una imagen y un audio de prueba.';
    return;
  }
  demoRender.disabled = true;
  demoMeta.textContent = 'Generando video con la imagen seleccionada...';
  const audioResponse = await fetch(audioUrl);
  const audioBlob = await audioResponse.blob();
  const formData = new FormData();
  if (imageFile) {
    formData.append('image', imageFile);
  } else {
    const imageResponse = await fetch(selectedImageUrl);
    const imageBlob = await imageResponse.blob();
    formData.append('image', new File([imageBlob], 'demo-image.png', { type: 'image/png' }));
  }
  formData.append('audio', new File([audioBlob], 'demo.wav', { type: 'audio/wav' }));
  const response = await fetch('/api/render', { method: 'POST', body: formData });
  const payload = await response.json();
  if (!response.ok) {
    demoMeta.textContent = payload.detail || 'No se pudo generar el video.';
    demoRender.disabled = false;
    return;
  }
  renderProcess.hidden = false;
  renderProcess.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await pollJob(payload.id, true);
  demoRender.disabled = false;
}

function updateProcess(job) {
  if (!renderProcess) return;
  renderProcess.hidden = false;
  renderPhase.textContent = `${job.phase || 'Procesando'} · ${job.progress || 0}%`;
  const progress = job.progress || 0;
  updatePipelineVisual(progress, job.status === 'completed', job.mlEnabled === true);
  const currentStep = progress >= 95 ? 5 : progress >= 40 ? 4 : progress >= 35 ? 3 : progress >= 15 ? 2 : 1;
  document.querySelectorAll('[data-step]').forEach((step) => {
    const stepNumber = Number(step.dataset.step);
    step.classList.toggle('done', stepNumber < currentStep || job.status === 'completed');
    step.classList.toggle('active', stepNumber === currentStep && job.status !== 'completed');
  });
}

async function loadDemo() {
  try {
    const response = await fetch('/api/demo');
    if (!response.ok) throw new Error('demo unavailable');
    const demo = await response.json();
    const demos = demo.demos || [];
    const images = demo.images || [];
    images.forEach((image) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'image-option';
      button.setAttribute('aria-pressed', 'false');
      button.innerHTML = `<img src="${image.imageUrl}" alt="${image.name}" /><span>${image.name}</span>`;
      button.addEventListener('click', () => {
        selectedImageUrl = image.imageUrl;
        document.querySelector('#pipeline-image').src = image.imageUrl;
        updateGridImage(image.imageUrl);
        updatePipelineVisual(0, false);
        demoMeta.textContent = `${image.name} seleccionada · pulsa “Generar con esta imagen”`;
        document.querySelectorAll('.image-option').forEach((item) => {
          item.classList.remove('selected');
          item.setAttribute('aria-pressed', 'false');
        });
        button.classList.add('selected');
        button.setAttribute('aria-pressed', 'true');
        demoImage.value = '';
      });
      demoImageGrid.appendChild(button);
    });
    if (images.length) demoImageGrid.firstElementChild.click();
    demos.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.name;
      demoSelector.appendChild(option);
    });
    if (demos.length) selectDemo(demos[0]);
    demoSelector.addEventListener('change', () => {
      const selected = demos.find((item) => item.id === demoSelector.value);
      if (selected) selectDemo(selected);
    });
  } catch (error) {
    demoMeta.textContent = 'No se pudo cargar la demo.';
  }
}

async function pollJob(jobId, updateDemo = false) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  updateProcess(job);
  feedback.textContent = `${job.status === 'completed' ? 'Listo' : 'Procesando'} · ${job.progress || 0}%`;
  if (job.status === 'completed' && job.outputUrl) {
    const link = `<a href="${job.outputUrl}" target="_blank" rel="noreferrer">Abrir MP4</a>`;
    demoVideo.src = job.outputUrl;
    demoVideo.load();
    loadAnalysis(job.analysisUrl);
    setMappingPreview(job.mappingUrl);
    if (updateDemo) {
      demoMeta.innerHTML = `Video generado con tu imagen · ${link}`;
    } else {
      feedback.innerHTML = `Composición lista. ${link}`;
      demoMeta.innerHTML = `Video generado con tus archivos · ${link}`;
    }
    return;
  }
  if (job.status === 'failed') {
    feedback.textContent = job.error || 'No se pudo generar la composición.';
    return;
  }
  window.setTimeout(() => pollJob(jobId, updateDemo), 1000);
}

demoRender.addEventListener('click', () => renderWithImage(demoImage.files[0], selectedDemo?.audioUrl));
demoImage.addEventListener('change', () => {
  const file = demoImage.files[0];
  if (!file) return;
  selectedImageUrl = null;
  document.querySelector('#pipeline-image').src = URL.createObjectURL(file);
  updateGridImage(document.querySelector('#pipeline-image').src);
  updatePipelineVisual(0, false);
  demoMeta.textContent = 'Imagen cargada · pulsa “Generar con esta imagen”';
  document.querySelectorAll('.image-option').forEach((item) => {
    item.classList.remove('selected');
    item.setAttribute('aria-pressed', 'false');
  });
});

document.querySelector('#render-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  feedback.textContent = 'Subiendo archivos...';
  const response = await fetch('/api/render', { method: 'POST', body: new FormData(event.currentTarget) });
  const payload = await response.json();
  if (!response.ok) {
    feedback.textContent = payload.detail || 'No se pudo iniciar el render.';
    return;
  }
  renderProcess.hidden = false;
  renderProcess.scrollIntoView({ behavior: 'smooth', block: 'center' });
  pollJob(payload.id);
});

loadDemo();
buildPipelineVisuals();
