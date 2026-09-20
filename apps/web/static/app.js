const feedback = document.querySelector('#render-feedback');
const demoMeta = document.querySelector('#demo-meta');
const demoSelector = document.querySelector('#demo-selector');
const demoVideo = document.querySelector('#demo-video');
const demoImage = document.querySelector('#demo-image');
const demoRender = document.querySelector('#demo-render');
let selectedDemo = null;

function selectDemo(demo) {
  selectedDemo = demo;
  demoVideo.src = demo.videoUrl;
  demoVideo.load();
  demoMeta.textContent = `Video preparado · ${demo.description || 'Audio público'} · ${demo.durationSeconds || 20} s · ${demo.mlEnabled !== false ? 'ML activado' : 'modo determinista'}`;
}

async function renderWithImage(imageFile, audioUrl) {
  if (!imageFile || !audioUrl) {
    demoMeta.textContent = 'Selecciona una imagen y un audio de prueba.';
    return;
  }
  demoRender.disabled = true;
  demoMeta.textContent = 'Generando video con la imagen seleccionada...';
  const audioResponse = await fetch(audioUrl);
  const audioBlob = await audioResponse.blob();
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('audio', new File([audioBlob], 'demo.wav', { type: 'audio/wav' }));
  const response = await fetch('/api/render', { method: 'POST', body: formData });
  const payload = await response.json();
  if (!response.ok) {
    demoMeta.textContent = payload.detail || 'No se pudo generar el video.';
    demoRender.disabled = false;
    return;
  }
  await pollJob(payload.id, true);
  demoRender.disabled = false;
}

async function loadDemo() {
  try {
    const response = await fetch('/api/demo');
    if (!response.ok) throw new Error('demo unavailable');
    const demo = await response.json();
    const demos = demo.demos || [];
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
  pollJob(payload.id);
});

loadDemo();
