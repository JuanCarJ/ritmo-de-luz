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

function buildPipelineVisuals() {
  for (let index = 0; index < 20; index += 1) {
    const waveBar = document.createElement('span');
    waveBar.style.height = `${20 + ((index * 17) % 70)}%`;
    document.querySelector('#pipeline-wave').appendChild(waveBar);
  }
  for (let index = 0; index < 12; index += 1) {
    const band = document.createElement('span');
    band.style.height = `${25 + ((index * 23) % 65)}%`;
    document.querySelector('#pipeline-bands').appendChild(band);
  }
  for (const containerId of ['raw-bars', 'normalized-bars']) {
    for (let index = 0; index < 12; index += 1) {
      const bar = document.createElement('span');
      bar.style.height = `${20 + ((index * (containerId === 'raw-bars' ? 31 : 19)) % 70)}%`;
      document.querySelector(`#${containerId}`).appendChild(bar);
    }
  }
  for (let index = 0; index < 24; index += 1) {
    const tile = document.createElement('span');
    tile.style.setProperty('--tile-index', index);
    document.querySelector('#pipeline-grid').appendChild(tile);
  }
}

function updatePipelineVisual(progress = 0, complete = false) {
  const currentStage = complete ? 5 : progress >= 95 ? 5 : progress >= 40 ? 4 : progress >= 35 ? 3 : progress >= 15 ? 2 : 1;
  document.querySelectorAll('[data-visual-stage]').forEach((stage) => {
    const stageNumber = Number(stage.dataset.visualStage);
    stage.classList.toggle('visual-active', stageNumber === currentStage && !complete);
    stage.classList.toggle('visual-done', stageNumber <= currentStage && complete);
  });
  const outputState = document.querySelector('#output-state');
  outputState.textContent = complete ? 'MP4 listo' : progress ? `${progress}% en proceso` : 'Esperando render';
}

async function loadAnalysis(analysisUrl) {
  if (!analysisUrl) return;
  const response = await fetch(analysisUrl);
  if (!response.ok) return;
  const analysis = await response.json();
  const rms = analysis.rms || [];
  const melBands = analysis.melBands || [];
  document.querySelectorAll('#pipeline-wave span').forEach((bar, index, bars) => {
    const sourceIndex = Math.floor(index * rms.length / bars.length);
    bar.style.height = `${18 + (rms[sourceIndex] || 0) * 80}%`;
  });
  const bandValues = melBands.reduce((totals, frame) => frame.map((value, index) => totals[index] + value), new Array(12).fill(0));
  document.querySelectorAll('#pipeline-bands span').forEach((bar, index) => {
    const value = bandValues[index] / Math.max(1, melBands.length);
    bar.style.height = `${18 + value * 80}%`;
  });
  document.querySelectorAll('#raw-bars span').forEach((bar, index) => {
    bar.style.height = `${18 + (rms[index % Math.max(1, rms.length)] || 0) * 80}%`;
  });
}

function selectDemo(demo) {
  selectedDemo = demo;
  demoVideo.src = demo.videoUrl;
  demoVideo.load();
  updatePipelineVisual(0, true);
  loadAnalysis(demo.analysisUrl);
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
  updatePipelineVisual(progress, job.status === 'completed');
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
      button.innerHTML = `<img src="${image.imageUrl}" alt="${image.name}" /><span>${image.name}</span>`;
      button.addEventListener('click', () => {
        selectedImageUrl = image.imageUrl;
        document.querySelector('#pipeline-image').src = image.imageUrl;
        updatePipelineVisual(0, false);
        demoMeta.textContent = `${image.name} seleccionada · pulsa “Generar con esta imagen”`;
        document.querySelectorAll('.image-option').forEach((item) => item.classList.remove('selected'));
        button.classList.add('selected');
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
    if (updateDemo) {
      demoVideo.src = job.outputUrl;
      demoVideo.load();
      demoMeta.innerHTML = `Video generado con tu imagen · ${link}`;
    } else {
      feedback.innerHTML = `Composición lista. ${link}`;
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
  updatePipelineVisual(0, false);
  demoMeta.textContent = 'Imagen cargada · pulsa “Generar con esta imagen”';
  document.querySelectorAll('.image-option').forEach((item) => item.classList.remove('selected'));
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
