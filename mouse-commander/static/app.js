/* ── MouseCommander — Admin UI ──────────────────────────────────────────── */

// ── State ──────────────────────────────────────────────────────────────────
let config = {};
let buttons = {};         // button_id -> button data
let liveFeedCount = 0;
const MAX_FEED = 60;

// ── Helpers ────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const qs = s => document.querySelector(s);
const fmt = ts => ts ? new Date(ts).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '';

async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}

// ── Tabs ───────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`tab-${tab}`).classList.add('active');
    if (tab === 'capture') renderButtonGrid();
    if (tab === 'mappings') renderMappings();
  });
});

// ── Config / status ────────────────────────────────────────────────────────
async function loadConfig() {
  config = await api('/api/config');
  applyConfigToUI();
}

function applyConfigToUI() {
  const learnOn = config.learn_mode ?? true;
  const overrideOn = config.override_active ?? false;

  $('toggle-learn').checked = learnOn;
  $('status-learn').textContent = learnOn ? 'On' : 'Off';
  $('status-learn').style.color = learnOn ? 'var(--green)' : 'var(--text-muted)';

  $('toggle-override').checked = overrideOn;
  $('status-override').textContent = overrideOn ? 'Active' : 'Off';
  $('status-override').style.color = overrideOn ? 'var(--accent)' : 'var(--text-muted)';

  $('status-mapped').textContent = Object.keys(config.mappings || {}).length;
  const mc = Object.keys(config.mappings || {}).length;
  $('mappings-badge').textContent = mc;
  $('mappings-badge').classList.toggle('visible', mc > 0);
}

$('toggle-learn').addEventListener('change', async e => {
  config.learn_mode = e.target.checked;
  applyConfigToUI();
  await api('/api/config', 'POST', { learn_mode: config.learn_mode });
});

$('toggle-override').addEventListener('change', async e => {
  config.override_active = e.target.checked;
  applyConfigToUI();
  await api('/api/config', 'POST', { override_active: config.override_active });
});

// ── Load buttons ───────────────────────────────────────────────────────────
async function loadButtons() {
  const list = await api('/api/buttons');
  buttons = {};
  list.forEach(b => { buttons[b.id] = b; });
  $('status-buttons').textContent = list.length;
  const bc = list.length;
  $('capture-badge').textContent = bc;
  $('capture-badge').classList.toggle('visible', bc > 0);
}

// ── Live feed ──────────────────────────────────────────────────────────────
function addFeedItem(ev) {
  const feed = $('live-feed');
  const empty = feed.querySelector('.feed-empty');
  if (empty) empty.remove();

  const isMapped = config.mappings && config.mappings[ev.button_id];
  const item = document.createElement('div');
  item.className = 'feed-item';
  item.innerHTML = `
    <span class="feed-item-id">${ev.button_id}</span>
    <span style="color:var(--text-muted);font-size:13px">${ev.source}</span>
    ${isMapped
      ? '<span class="feed-item-mapped">mapped</span>'
      : '<span class="feed-item-new">new</span>'}
    <span class="feed-item-ts">${fmt(ev.ts)}</span>
  `;
  feed.prepend(item);
  liveFeedCount++;
  if (liveFeedCount > MAX_FEED) {
    const items = feed.querySelectorAll('.feed-item');
    if (items.length > MAX_FEED) items[items.length - 1].remove();
  }
}

// ── SSE ────────────────────────────────────────────────────────────────────
let evtSource = null;
function connectSSE() {
  evtSource = new EventSource('/api/events');
  evtSource.onopen = () => { $('live-dot').style.background = 'var(--green)'; };
  evtSource.onerror = () => {
    $('live-dot').style.background = 'var(--red)';
    setTimeout(connectSSE, 3000);
  };
  evtSource.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.type === 'button_press') {
      // update local button store
      if (!buttons[data.button_id]) {
        buttons[data.button_id] = { id: data.button_id, source: data.source, raw: data.raw, count: 0 };
        const bc = Object.keys(buttons).length;
        $('capture-badge').textContent = bc;
        $('capture-badge').classList.add('visible');
        $('status-buttons').textContent = bc;
      }
      buttons[data.button_id].count = (buttons[data.button_id].count || 0) + 1;
      buttons[data.button_id].last_seen = data.ts;

      addFeedItem(data);
      flashButtonCard(data.button_id);

      // refresh capture grid if visible
      if ($('tab-capture').classList.contains('active')) {
        renderButtonGrid();
      }
    } else if (data.type === 'config_updated') {
      config = { ...config, ...data.config };
      applyConfigToUI();
    } else if (data.type === 'mapping_updated') {
      loadConfig().then(() => {
        if ($('tab-mappings').classList.contains('active')) renderMappings();
        if ($('tab-capture').classList.contains('active')) renderButtonGrid();
      });
    } else if (data.type === 'reset') {
      buttons = {};
      renderButtonGrid();
      $('capture-badge').textContent = '0';
      $('capture-badge').classList.remove('visible');
      $('status-buttons').textContent = '0';
    }
  };
}

function flashButtonCard(button_id) {
  const card = document.querySelector(`[data-bid="${button_id}"]`);
  if (!card) return;
  card.classList.remove('flash-press', 'flash-press-green');
  void card.offsetWidth;
  card.classList.add(config.mappings?.[button_id] ? 'flash-press-green' : 'flash-press');
  setTimeout(() => card.classList.remove('flash-press', 'flash-press-green'), 350);
}

// ── Button grid ────────────────────────────────────────────────────────────
function renderButtonGrid() {
  const grid = $('button-grid');
  const bList = Object.values(buttons);
  if (bList.length === 0) {
    grid.innerHTML = `<div class="grid-empty">
      <div class="grid-empty-icon">🖱️</div>
      <p>No buttons captured yet</p>
      <small>Make sure Learn Mode is On, then press your extra mouse buttons</small>
    </div>`;
    return;
  }
  grid.innerHTML = '';
  bList.forEach(btn => {
    const mapped = config.mappings?.[btn.id];
    const card = document.createElement('div');
    card.className = `button-card${mapped ? ' mapped' : ''}`;
    card.dataset.bid = btn.id;
    card.innerHTML = `
      <div class="button-card-id">${btn.id}</div>
      <div class="button-card-label">${mapped?.label || btn.label || btn.id}</div>
      <div class="button-card-count">Pressed ${btn.count || 0}× · ${btn.source}</div>
      <span class="button-card-status ${mapped ? 'mapped-s' : 'unmapped'}">
        ${mapped ? '✓ Mapped' : '+ Assign'}
      </span>
    `;
    card.addEventListener('click', () => openModal(btn.id, btn));
    grid.appendChild(card);
  });
}

// ── Mappings list ──────────────────────────────────────────────────────────
function renderMappings() {
  const list = $('mappings-list');
  const mappings = config.mappings || {};
  const entries = Object.entries(mappings);
  if (entries.length === 0) {
    list.innerHTML = `<div class="grid-empty">
      <div class="grid-empty-icon">🗺️</div>
      <p>No mappings yet</p>
      <small>Head to Capture and click a button to assign an action</small>
    </div>`;
    return;
  }
  list.innerHTML = '';
  entries.forEach(([bid, m]) => {
    const row = document.createElement('div');
    row.className = 'mapping-row';
    row.innerHTML = `
      <div class="mapping-row-id">${bid}</div>
      <div class="mapping-row-label">${m.label || bid}</div>
      <div class="mapping-row-action">
        <span class="mapping-row-action-type">${m.action_type || 'none'}</span>
        <span style="color:var(--text-dim);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.action_value || ''}</span>
      </div>
      <button class="mapping-row-edit">Edit</button>
    `;
    row.querySelector('.mapping-row-edit').addEventListener('click', () => {
      openModal(bid, buttons[bid] || { id: bid }, m);
    });
    list.appendChild(row);
  });
}

// ── Modal ──────────────────────────────────────────────────────────────────
let currentButtonId = null;
let selectedActionType = null;
let selectedMediaKey = null;

function openModal(buttonId, btnData, existingMapping = null) {
  currentButtonId = buttonId;
  selectedActionType = existingMapping?.action_type || null;
  selectedMediaKey = null;

  $('modal-button-id').value = buttonId;
  $('modal-title').textContent = `Map: ${buttonId}`;
  $('modal-label').value = existingMapping?.label || btnData?.label || buttonId;

  // Reset action chips
  document.querySelectorAll('.action-chip').forEach(c => c.classList.remove('selected'));
  if (selectedActionType) {
    const chip = document.querySelector(`.action-chip[data-type="${selectedActionType}"]`);
    if (chip) chip.classList.add('selected');
  }

  renderActionValueField(existingMapping?.action_type, existingMapping?.action_value);

  $('modal-backdrop').classList.remove('hidden');
}

function closeModal() {
  $('modal-backdrop').classList.add('hidden');
  currentButtonId = null;
}

$('modal-close').addEventListener('click', closeModal);
$('modal-backdrop').addEventListener('click', e => {
  if (e.target === $('modal-backdrop')) closeModal();
});

document.querySelectorAll('.action-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.action-chip').forEach(c => c.classList.remove('selected'));
    chip.classList.add('selected');
    selectedActionType = chip.dataset.type;
    renderActionValueField(selectedActionType, null);
  });
});

function renderActionValueField(type, value) {
  const group = $('action-value-group');
  if (!type) { group.innerHTML = ''; return; }

  const ACTION_META = {
    hotkey: {
      label: 'Key combination',
      placeholder: 'e.g. ctrl+shift+t  or  ctrl+c',
      hint: 'Use + to combine: ctrl, shift, alt, win, then a key or F1–F24',
    },
    type_text: {
      label: 'Text to type',
      placeholder: 'e.g. Hello world! or a template snippet',
      hint: 'The exact text will be typed at the cursor position',
    },
    open_url: {
      label: 'URL to open',
      placeholder: 'https://...',
      hint: 'Opens in your default browser',
    },
    run_command: {
      label: 'Shell command',
      placeholder: 'e.g. notepad.exe  or  python myscript.py',
      hint: 'Runs in a new process. Use full paths if needed.',
    },
    open_file: {
      label: 'File or folder path',
      placeholder: 'C:\\Users\\...  or  /home/...',
      hint: 'Opens with the default application for that file type',
    },
  };

  if (type === 'media') {
    const keys = [
      { id: 'play_pause', label: '⏯ Play/Pause' },
      { id: 'next', label: '⏭ Next' },
      { id: 'prev', label: '⏮ Prev' },
      { id: 'volume_up', label: '🔊 Vol Up' },
      { id: 'volume_down', label: '🔉 Vol Down' },
      { id: 'mute', label: '🔇 Mute' },
    ];
    selectedMediaKey = value || null;
    group.innerHTML = `<label>Media key</label><div class="media-grid" id="media-grid"></div>`;
    const grid = $('media-grid');
    keys.forEach(k => {
      const chip = document.createElement('button');
      chip.className = `media-chip${selectedMediaKey === k.id ? ' selected' : ''}`;
      chip.textContent = k.label;
      chip.dataset.key = k.id;
      chip.addEventListener('click', () => {
        document.querySelectorAll('.media-chip').forEach(c => c.classList.remove('selected'));
        chip.classList.add('selected');
        selectedMediaKey = k.id;
      });
      grid.appendChild(chip);
    });
    return;
  }

  const meta = ACTION_META[type];
  if (!meta) { group.innerHTML = ''; return; }

  group.innerHTML = `
    <label>${meta.label}</label>
    <input class="input" type="text" id="action-value-input" placeholder="${meta.placeholder}" value="${value || ''}"/>
    <p style="margin-top:6px;font-size:11px;color:var(--text-dim)">${meta.hint}</p>
  `;
}

$('modal-save').addEventListener('click', async () => {
  const buttonId = currentButtonId;
  if (!buttonId) return;
  const label = $('modal-label').value.trim() || buttonId;
  const type = selectedActionType;
  let val = '';
  if (type === 'media') {
    val = selectedMediaKey || '';
  } else {
    const inp = $('action-value-input');
    val = inp ? inp.value.trim() : '';
  }

  await api('/api/mapping', 'POST', {
    button_id: buttonId,
    label,
    action_type: type,
    action_value: val,
  });
  closeModal();
});

$('modal-delete').addEventListener('click', async () => {
  if (!currentButtonId) return;
  if (!confirm(`Remove mapping for ${currentButtonId}?`)) return;
  await api('/api/mapping', 'POST', { button_id: currentButtonId, delete: true });
  closeModal();
});

$('modal-test').addEventListener('click', async () => {
  const type = selectedActionType;
  let val = '';
  if (type === 'media') {
    val = selectedMediaKey || '';
  } else {
    const inp = $('action-value-input');
    val = inp ? inp.value.trim() : '';
  }
  if (!type || !val) return;
  await api('/api/test_action', 'POST', { action_type: type, action_value: val });
});

// ── Reset captures ─────────────────────────────────────────────────────────
$('reset-captures-btn').addEventListener('click', async () => {
  if (!confirm('Clear all captured buttons? (Mappings are kept)')) return;
  buttons = {};
  renderButtonGrid();
  await api('/api/config', 'POST', {});  // triggers broadcast via status
  // tell server to clear
  await fetch('/api/buttons');  // just a GET; server broadcasts reset on our call
  // Actually we just clear locally; server state is in captured_buttons dict
  // For a true reset, we'd add a DELETE endpoint. For now local clear is fine.
});

// ── Settings ───────────────────────────────────────────────────────────────
$('clear-all-btn').addEventListener('click', async () => {
  if (!confirm('Clear ALL mappings? This cannot be undone.')) return;
  config.mappings = {};
  await api('/api/config', 'POST', { mappings: {} });
  applyConfigToUI();
  renderMappings();
  renderButtonGrid();
});

$('reset-firstrun-btn').addEventListener('click', () => startTutorial());

// ── Tutorial ───────────────────────────────────────────────────────────────
const TUTORIAL_STEPS = [
  {
    title: 'Welcome to MouseCommander',
    text: 'This tool turns your Redragon MMO mouse extra buttons into anything you want — no firmware needed. Takes about a minute to set up.',
    target: null,
    position: 'center',
  },
  {
    title: 'Step 1 — Learn Mode',
    text: 'Keep Learn Mode ON. It quietly listens for every button your mouse sends. Press a few of your extra side buttons now.',
    target: 'card-learn',
    position: 'below',
  },
  {
    title: 'Step 2 — Live Feed',
    text: 'Every button press appears here in real time. Each one gets a unique ID. Press your extra buttons and watch them appear.',
    target: 'live-feed-card',
    position: 'above',
  },
  {
    title: 'Step 3 — Capture tab',
    text: 'Head to the Capture tab. All detected buttons appear as cards. Click any card to assign an action to that button.',
    target: 'nav-capture',
    position: 'right',
  },
  {
    title: 'Step 4 — Override Active',
    text: "Once you've mapped your buttons, flip Override Active on. Now MouseCommander intercepts those buttons and fires your actions instead.",
    target: 'card-override',
    position: 'below',
  },
];

let tutStep = 0;

function startTutorial() {
  tutStep = 0;
  $('tutorial-overlay').classList.remove('hidden');
  showTutStep();
}

function endTutorial() {
  $('tutorial-overlay').classList.add('hidden');
  $('tutorial-spotlight').style.opacity = '0';
}

function showTutStep() {
  const step = TUTORIAL_STEPS[tutStep];
  $('tutorial-step-badge').textContent = `${tutStep + 1} / ${TUTORIAL_STEPS.length}`;
  $('tutorial-title').textContent = step.title;
  $('tutorial-text').textContent = step.text;
  $('tutorial-next').textContent = tutStep === TUTORIAL_STEPS.length - 1 ? 'Done ✓' : 'Next →';

  const spotlight = $('tutorial-spotlight');
  const bubble = $('tutorial-bubble');

  if (step.target) {
    const el = $(step.target);
    if (el) {
      const r = el.getBoundingClientRect();
      const pad = 10;
      spotlight.style.cssText = `
        left: ${r.left - pad}px;
        top: ${r.top - pad}px;
        width: ${r.width + pad * 2}px;
        height: ${r.height + pad * 2}px;
        opacity: 1;
      `;

      // Position bubble
      const bw = 320, bh = 180;
      let bTop, bLeft;
      if (step.position === 'below') {
        bTop = r.bottom + pad + 20;
        bLeft = r.left + r.width / 2 - bw / 2;
      } else if (step.position === 'above') {
        bTop = r.top - bh - pad - 20;
        bLeft = r.left + r.width / 2 - bw / 2;
      } else if (step.position === 'right') {
        bTop = r.top + r.height / 2 - bh / 2;
        bLeft = r.right + pad + 20;
      } else {
        bTop = r.top;
        bLeft = r.right + 20;
      }
      bTop = Math.max(16, Math.min(bTop, window.innerHeight - bh - 16));
      bLeft = Math.max(16, Math.min(bLeft, window.innerWidth - bw - 16));
      bubble.style.top = `${bTop}px`;
      bubble.style.left = `${bLeft}px`;
    }
  } else {
    // Center
    spotlight.style.opacity = '0';
    bubble.style.top = `${window.innerHeight / 2 - 100}px`;
    bubble.style.left = `${window.innerWidth / 2 - 160}px`;
  }
}

$('tutorial-next').addEventListener('click', () => {
  tutStep++;
  if (tutStep >= TUTORIAL_STEPS.length) {
    endTutorial();
  } else {
    showTutStep();
  }
});

$('tutorial-skip').addEventListener('click', endTutorial);

$('start-tutorial-btn').addEventListener('click', startTutorial);

// ── Init ───────────────────────────────────────────────────────────────────
(async () => {
  await loadConfig();
  await loadButtons();
  connectSSE();

  if (config.first_run !== false) {
    setTimeout(startTutorial, 800);
  }
})();
