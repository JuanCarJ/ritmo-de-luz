const feedback = document.querySelector('#render-feedback');
const demoMeta = document.querySelector('#demo-meta');
const demoSelector = document.querySelector('#demo-selector');
const demoVideo = document.querySelector('#demo-video');

function selectDemo(demo) {
  demoVideo.src = demo.videoUrl;
  demoVideo.load();
  demoMeta.textContent = `Video preparado · ${demo.description || 'Audio público'} · ${demo.durationSeconds || 20} s · ${demo.mlEnabled !== false ? 'ML activado' : 'modo determinista'}`;
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

async function pollJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  feedback.textContent = `${job.status === 'completed' ? 'Listo' : 'Procesando'} · ${job.progress || 0}%`;
  if (job.status === 'completed' && job.outputUrl) {
    feedback.innerHTML = `Composición lista. <a href="${job.outputUrl}" target="_blank" rel="noreferrer">Abrir MP4</a>`;
    return;
  }
  if (job.status === 'failed') {
    feedback.textContent = job.error || 'No se pudo generar la composición.';
    return;
  }
  window.setTimeout(() => pollJob(jobId), 1000);
}

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
