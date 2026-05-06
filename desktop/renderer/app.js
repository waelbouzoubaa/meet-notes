/* KaptNotes Desktop — Renderer logic */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
  phase: 'upload',
  audioFile: null,
  audioBlob: null,
  audioStem: '',
  docs: [],
  transcript: '',
  report: '',
  speakers: [],
  speakerMap: {},
  mediaRecorder: null,
  recordChunks: [],
  timerInterval: null,
  timerSeconds: 0,
  apiUrl: 'http://localhost:8000',
};

// ── Init ───────────────────────────────────────────────────────────────────────
(async () => {
  state.apiUrl = await window.kaptnotes.getApiUrl();
  await loadTemplates();
  await loadAudioSources();
  bindEvents();
})();

// ── Templates ─────────────────────────────────────────────────────────────────
const TEMPLATE_META = {
  commercial: '💼 Commercial', chantier: '🏗️ Chantier', securite: '🦺 Sécurité',
  direction: '🎯 Direction', suivi_projet: '📊 Suivi projet', socle_commun: '📋 Socle commun',
  general: '📝 Général', brainstorm: '💡 Brainstorm', tech_review: '⚙️ Tech review',
  sales: '💼 Sales', custom: '✏️ Custom',
};

async function loadTemplates() {
  try {
    const res = await fetch(`${state.apiUrl}/api/templates`);
    const { templates } = await res.json();
    const sel = document.getElementById('template');
    sel.innerHTML = templates.map(t =>
      `<option value="${t}">${TEMPLATE_META[t] || t}</option>`
    ).join('');
  } catch (e) {
    console.error('Templates load error', e);
  }
}

// ── Audio sources (system audio) ──────────────────────────────────────────────
async function loadAudioSources() {
  try {
    const sources = await window.kaptnotes.getAudioSources();
    const sel = document.getElementById('audio-source');
    sel.innerHTML = sources.map(s =>
      `<option value="${s.id}">${s.name}</option>`
    ).join('');
  } catch (e) {
    console.error('Audio sources error', e);
  }
}

// ── Events ────────────────────────────────────────────────────────────────────
function bindEvents() {
  // Tab switching (upload/record)
  document.querySelectorAll('.tab[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab[data-tab]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
      document.getElementById(`tab-${btn.dataset.tab}`).style.display = 'block';
    });
  });

  // Result tab switching
  document.querySelectorAll('.tab[data-rtab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab[data-rtab]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('rtab-report').style.display = btn.dataset.rtab === 'report' ? 'block' : 'none';
      document.getElementById('rtab-transcript').style.display = btn.dataset.rtab === 'transcript' ? 'block' : 'none';
    });
  });

  // File input
  document.getElementById('file-input').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) setAudioFile(file);
  });

  // Drag & drop
  const dz = document.getElementById('dropzone');
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('over');
    const file = e.dataTransfer.files[0];
    if (file) setAudioFile(file);
  });

  // Doc input
  document.getElementById('doc-input').addEventListener('change', e => {
    Array.from(e.target.files).forEach(addDoc);
    e.target.value = '';
  });

  // Record button
  document.getElementById('btn-record').addEventListener('click', toggleRecording);

  // Launch
  document.getElementById('btn-launch').addEventListener('click', launchAnalysis);

  // Generate report
  document.getElementById('btn-generate').addEventListener('click', generateReport);

  // Reset
  document.getElementById('btn-reset').addEventListener('click', resetAll);

  // Re-run
  document.getElementById('btn-rerun').addEventListener('click', () => setPhase('transcribed'));

  // Downloads
  document.getElementById('dl-md').addEventListener('click', () => downloadText(state.report, `${state.audioStem}_report.md`, 'text/markdown'));
  document.getElementById('dl-txt').addEventListener('click', () => downloadText(state.transcript, `${state.audioStem}_transcript.txt`, 'text/plain'));
  document.getElementById('dl-pdf').addEventListener('click', () => downloadText(state.report, `${state.audioStem}_report.md`, 'text/markdown'));
}

// ── Audio file ────────────────────────────────────────────────────────────────
function setAudioFile(file) {
  state.audioFile = file;
  state.audioStem = file.name.replace(/\.[^.]+$/, '');
  const mb = (file.size / 1024 / 1024).toFixed(1);
  const info = document.getElementById('file-info');
  info.style.display = 'block';
  info.textContent = `📎 ${file.name} · ${mb} Mo`;
  document.getElementById('btn-launch').disabled = false;
}

// ── Documents ─────────────────────────────────────────────────────────────────
function addDoc(file) {
  state.docs.push(file);
  renderDocList();
}

function renderDocList() {
  const list = document.getElementById('doc-list');
  list.innerHTML = state.docs.map((d, i) => `
    <div class="doc-item">
      <span>📄 ${d.name}</span>
      <button class="doc-remove" onclick="removeDoc(${i})">✕</button>
    </div>`).join('');
}

window.removeDoc = function(i) {
  state.docs.splice(i, 1);
  renderDocList();
};

// ── Recording (system audio + mic) ────────────────────────────────────────────
async function toggleRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  await window.kaptnotes.requestMicPermission();

  const sourceId = document.getElementById('audio-source').value;
  const constraints = {
    audio: {
      mandatory: {
        chromeMediaSource: 'desktop',
        chromeMediaSourceId: sourceId,
      }
    },
    video: { mandatory: { chromeMediaSource: 'desktop', chromeMediaSourceId: sourceId } }
  };

  try {
    const systemStream = await navigator.mediaDevices.getUserMedia(constraints);
    const micStream    = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });

    // Stop video track — we only want audio
    systemStream.getVideoTracks().forEach(t => t.stop());

    // Mix system audio + mic via AudioContext
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination();
    ctx.createMediaStreamSource(systemStream).connect(dest);
    ctx.createMediaStreamSource(micStream).connect(dest);

    state.recordChunks = [];
    state.mediaRecorder = new MediaRecorder(dest.stream);
    state.mediaRecorder.ondataavailable = e => { if (e.data.size > 0) state.recordChunks.push(e.data); };
    state.mediaRecorder.onstop = () => finishRecording(ctx);
    state.mediaRecorder.start();

    // UI
    const btn = document.getElementById('btn-record');
    btn.textContent = '⏹ Arrêter';
    btn.classList.add('recording');
    startTimer();
    document.getElementById('record-info').style.display = 'block';
    document.getElementById('record-info').textContent = '🔴 Enregistrement en cours — système + micro';

  } catch (err) {
    alert(`Erreur capture audio : ${err.message}`);
  }
}

function stopRecording() {
  if (state.mediaRecorder) state.mediaRecorder.stop();
  clearInterval(state.timerInterval);
  document.getElementById('btn-record').textContent = '🔴 Démarrer';
  document.getElementById('btn-record').classList.remove('recording');
  document.getElementById('record-timer').style.display = 'none';
}

function finishRecording(ctx) {
  ctx.close();
  const blob = new Blob(state.recordChunks, { type: 'audio/webm' });
  state.audioBlob = blob;
  state.audioStem = `enregistrement_${new Date().toISOString().slice(0,19).replace(/[T:]/g, '-')}`;

  // Auto-download
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.audioStem}.webm`;
  a.click();
  URL.revokeObjectURL(url);

  document.getElementById('record-info').textContent = `✅ Enregistrement prêt : ${state.audioStem}.webm`;
  document.getElementById('btn-launch').disabled = false;
}

function startTimer() {
  state.timerSeconds = 0;
  const el = document.getElementById('record-timer');
  el.style.display = 'block';
  state.timerInterval = setInterval(() => {
    state.timerSeconds++;
    const m = String(Math.floor(state.timerSeconds / 60)).padStart(2, '0');
    const s = String(state.timerSeconds % 60).padStart(2, '0');
    el.textContent = `${m}:${s}`;
  }, 1000);
}

// ── Launch analysis ───────────────────────────────────────────────────────────
async function launchAnalysis() {
  setPhase('transcribing');

  const form = new FormData();
  if (state.audioFile) {
    form.append('audio', state.audioFile);
  } else if (state.audioBlob) {
    form.append('audio', state.audioBlob, `${state.audioStem}.webm`);
  }
  form.append('language', document.getElementById('language').value);
  form.append('engine', 'assemblyai');

  document.getElementById('transcribing-label').textContent = 'Envoi vers AssemblyAI…';

  try {
    const res = await fetch(`${state.apiUrl}/api/transcribe`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    const { transcript, elapsed } = await res.json();

    state.transcript = transcript;
    state.speakers = extractSpeakers(transcript);
    setPhase('transcribed');
    renderTranscribed(elapsed);

    // Auto-download transcript
    downloadText(transcript, `${state.audioStem}_transcript.txt`, 'text/plain');

  } catch (e) {
    alert(`Erreur transcription : ${e.message}`);
    setPhase('upload');
  }
}

// ── Participants + generate report ────────────────────────────────────────────
function extractSpeakers(transcript) {
  const re = /\[[\d:]+\]\s+(Speaker \d+)\s*[:\-]/g;
  const seen = new Set();
  let m;
  while ((m = re.exec(transcript)) !== null) seen.add(m[1]);
  return [...seen];
}

function renderTranscribed(elapsed) {
  // Metrics
  const words = state.transcript.split(/\s+/).length;
  document.getElementById('metrics').innerHTML = [
    [state.speakers.length, 'Locuteurs'],
    [words.toLocaleString(), 'Mots transcrits'],
    [`${elapsed.toFixed(0)} s`, 'Durée analyse'],
    [document.getElementById('template').value.replace('_', ' '), 'Template'],
  ].map(([v, l]) => `<div class="metric"><div class="metric-val">${v}</div><div class="metric-lbl">${l}</div></div>`).join('');

  // Speakers table
  document.getElementById('speakers-table').innerHTML = `
    <table class="speakers-table">
      <thead><tr><th>Identifiant</th><th>Vrai nom</th></tr></thead>
      <tbody>${state.speakers.map(s => `
        <tr>
          <td>${s}</td>
          <td><input type="text" placeholder="${s}" data-speaker="${s}" /></td>
        </tr>`).join('')}
      </tbody>
    </table>`;

  // Transcript preview
  document.getElementById('transcript-preview').value = state.transcript;
}

async function generateReport() {
  setPhase('reporting');

  // Build speaker map
  state.speakerMap = {};
  document.querySelectorAll('[data-speaker]').forEach(input => {
    if (input.value.trim()) state.speakerMap[input.dataset.speaker] = input.value.trim();
  });

  // Apply speaker names
  let namedTranscript = state.transcript;
  Object.entries(state.speakerMap).forEach(([id, name]) => {
    namedTranscript = namedTranscript.replaceAll(id, name);
  });
  state.transcript = namedTranscript;

  const transcriptOnly = document.getElementById('transcript-only').checked;
  if (transcriptOnly) {
    state.report = '';
    setPhase('reported');
    renderReported();
    return;
  }

  try {
    let res, data;
    if (state.docs.length > 0) {
      const form = new FormData();
      form.append('transcript', state.transcript);
      form.append('template', document.getElementById('template').value);
      form.append('extra_context', document.getElementById('extra-context').value);
      state.docs.forEach(d => form.append('documents', d));
      res = await fetch(`${state.apiUrl}/api/summarize-with-docs`, { method: 'POST', body: form });
    } else {
      res = await fetch(`${state.apiUrl}/api/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: state.transcript,
          template: document.getElementById('template').value,
          extra_context: document.getElementById('extra-context').value,
        }),
      });
    }
    if (!res.ok) throw new Error(await res.text());
    data = await res.json();
    state.report = data.report;
    setPhase('reported');
    renderReported();
  } catch (e) {
    alert(`Erreur génération rapport : ${e.message}`);
    setPhase('transcribed');
  }
}

function renderReported() {
  document.getElementById('success-banner').textContent = `✅ Analyse terminée pour ${state.audioStem}`;
  document.getElementById('report-content').innerHTML = markdownToHtml(state.report);
  document.getElementById('transcript-final').value = state.transcript;
}

// ── Phase management ──────────────────────────────────────────────────────────
const PHASES = ['upload', 'transcribing', 'transcribed', 'reporting', 'reported'];
const PHASE_LABELS = { upload: 'Upload', transcribing: 'Transcription', transcribed: 'Participants', reporting: 'Rapport', reported: 'Rapport' };
const STEP_ORDER = ['upload', 'transcribing', 'transcribed', 'reporting'];

function setPhase(phase) {
  state.phase = phase;
  PHASES.forEach(p => {
    const el = document.getElementById(`phase-${p}`);
    if (el) el.style.display = p === phase ? 'block' : 'none';
  });
  document.getElementById('phase-label').textContent = PHASE_LABELS[phase] || phase;
  document.getElementById('btn-reset').style.display = phase !== 'upload' ? 'block' : 'none';
  updateStepper(phase);
}

function updateStepper(phase) {
  const cur = STEP_ORDER.indexOf(phase === 'reported' ? 'reporting' : phase);
  document.querySelectorAll('.step[data-step]').forEach(el => {
    const i = parseInt(el.dataset.step);
    el.classList.remove('active', 'done', 'pending');
    if (i < cur) el.classList.add('done');
    else if (i === cur) el.classList.add('active');
    else el.classList.add('pending');
  });
}

function resetAll() {
  state.audioFile = null; state.audioBlob = null; state.transcript = ''; state.report = '';
  state.speakers = []; state.speakerMap = {}; state.docs = []; state.audioStem = '';
  document.getElementById('file-info').style.display = 'none';
  document.getElementById('btn-launch').disabled = true;
  renderDocList();
  setPhase('upload');
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function downloadText(content, filename, mime) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: mime }));
  a.download = filename;
  a.click();
}

function markdownToHtml(md) {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/^---$/gm, '<hr>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/^(?!<[hul]|<hr)(.+)$/gm, '<p>$1</p>');
}
