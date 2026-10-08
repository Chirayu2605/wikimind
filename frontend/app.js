/* app.js — WikiMind frontend logic */
'use strict';

const API_BASE = '';  // Same origin; change to http://localhost:8000 for dev without Docker

// ── Element refs ─────────────────────────────────────────────────────────────
const searchForm        = document.getElementById('search-form');
const questionInput     = document.getElementById('question-input');
const askBtn            = document.getElementById('ask-btn');
const loadingContainer  = document.getElementById('loading-container');
const errorContainer    = document.getElementById('error-container');
const errorMessage      = document.getElementById('error-message');
const retryBtn          = document.getElementById('retry-btn');
const resultsSection    = document.getElementById('results');
const answerText        = document.getElementById('answer-text');
const extraInfoText     = document.getElementById('extra-info-text');
const sourcesList       = document.getElementById('sources-list');
const relatedTopics     = document.getElementById('related-topics');
const similarQuestions  = document.getElementById('similar-questions');
const pageTitleBadge    = document.getElementById('page-title-badge');
const wikiLink          = document.getElementById('wiki-link');
const cacheBadge        = document.getElementById('cache-badge');
const askAnotherBtn     = document.getElementById('ask-another-btn');
const healthDot         = document.getElementById('health-dot');
const healthLabel       = document.getElementById('health-label');

// ── Particle canvas ──────────────────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [];

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.15,
      vy: (Math.random() - 0.5) * 0.15,
      alpha: Math.random() * 0.6 + 0.1,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(167,139,250,${p.alpha})`;
      ctx.fill();
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Health check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    if (data.status === 'ok') {
      healthDot.className = 'badge-dot online';
      healthLabel.textContent = data.redis ? 'API + Redis online' : 'API online · Redis offline';
    } else {
      throw new Error();
    }
  } catch {
    healthDot.className = 'badge-dot offline';
    healthLabel.textContent = 'API offline';
  }
}
checkHealth();

// ── Loading step animation ────────────────────────────────────────────────────
const STEPS = ['step-1', 'step-2', 'step-3', 'step-4'];
let stepTimer = null;

function startLoadingSteps() {
  STEPS.forEach(id => {
    const el = document.getElementById(id);
    el.className = 'loading-step';
  });
  let i = 0;
  document.getElementById(STEPS[0]).classList.add('active');

  stepTimer = setInterval(() => {
    if (i < STEPS.length - 1) {
      document.getElementById(STEPS[i]).classList.replace('active', 'done');
      i++;
      document.getElementById(STEPS[i]).classList.add('active');
    }
  }, 1800);
}

function stopLoadingSteps() {
  clearInterval(stepTimer);
  STEPS.forEach(id => {
    const el = document.getElementById(id);
    if (el.classList.contains('active')) el.classList.replace('active', 'done');
  });
}

// ── UI state helpers ─────────────────────────────────────────────────────────
function showSection(section) {
  loadingContainer.hidden = true;
  errorContainer.hidden   = true;
  resultsSection.hidden   = true;
  if (section) section.hidden = false;
}

function setFormBusy(busy) {
  askBtn.disabled          = busy;
  questionInput.disabled   = busy;
}

// ── Type-writer effect ────────────────────────────────────────────────────────
function typeWriter(el, text, speed = 12) {
  el.textContent = '';
  let i = 0;
  const tick = () => {
    if (i < text.length) {
      el.textContent += text[i++];
      setTimeout(tick, speed);
    }
  };
  tick();
}

// ── Render results ────────────────────────────────────────────────────────────
function renderResults(data) {
  // Meta bar
  pageTitleBadge.textContent = data.page_title;
  wikiLink.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(data.page_title)}`;
  wikiLink.textContent = `View on Wikipedia ↗`;

  cacheBadge.textContent = data.cached ? '⚡ Cache hit' : '🌐 Fresh fetch';
  cacheBadge.className = `cache-badge ${data.cached ? 'hit' : 'miss'}`;

  // Answer — typewriter
  typeWriter(answerText, data.answer, 10);

  // Extra info
  extraInfoText.textContent = data.extra_info;

  // Sources
  sourcesList.innerHTML = data.sources.map((src, i) => `
    <div class="source-item">
      <div class="source-num">Source ${i + 1}</div>
      <div>${escHtml(src)}</div>
    </div>
  `).join('');

  // Related topics
  relatedTopics.innerHTML = data.related_topics
    .slice(0, 15)
    .map(t => `<a class="tag" href="https://en.wikipedia.org/wiki/${encodeURIComponent(t)}" target="_blank" rel="noopener noreferrer">${escHtml(t)}</a>`)
    .join('');

  // Similar questions — clickable
  similarQuestions.innerHTML = data.similar_questions.map(q => `
    <li class="question-item" data-q="${escHtml(q)}" tabindex="0" role="button">
      <span class="question-arrow">▶</span>
      <span>${escHtml(q)}</span>
    </li>
  `).join('');

  // Wire up click on similar questions
  similarQuestions.querySelectorAll('.question-item').forEach(li => {
    li.addEventListener('click', () => {
      const q = li.dataset.q;
      questionInput.value = q;
      showSection(null);
      submitQuestion(q);
    });
    li.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') li.click(); });
  });

  showSection(resultsSection);

  // Stagger card animations
  resultsSection.querySelectorAll('.card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.07}s`;
  });
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Submit question ──────────────────────────────────────────────────────────
async function submitQuestion(question) {
  setFormBusy(true);
  showSection(loadingContainer);
  startLoadingSteps();

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    stopLoadingSteps();

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    stopLoadingSteps();
    errorMessage.textContent = err.message || 'Could not reach the API. Is the server running?';
    showSection(errorContainer);
  } finally {
    setFormBusy(false);
  }
}

// ── Event listeners ───────────────────────────────────────────────────────────
searchForm.addEventListener('submit', e => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if (q.length < 3) return;
  submitQuestion(q);
});

document.querySelectorAll('.example-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    questionInput.value = chip.dataset.q;
    questionInput.focus();
    submitQuestion(chip.dataset.q);
  });
});

retryBtn.addEventListener('click', () => {
  const q = questionInput.value.trim();
  if (q) submitQuestion(q);
  else showSection(null);
});

askAnotherBtn.addEventListener('click', () => {
  showSection(null);
  questionInput.value = '';
  questionInput.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
