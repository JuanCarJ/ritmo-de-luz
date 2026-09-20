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

function selectDemo(demo) {
  selectedDemo = demo;
  demoVideo.src = demo.videoUrl;
  demoVideo.load();
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
