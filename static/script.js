/* ═══════════════════════════════════════════════════════════════════
   Smart-Agri AI — Main Script (Clean, Professional, Active Context Synced)
   ═══════════════════════════════════════════════════════════════════ */

'use strict';

// ── State ─────────────────────────────────────────────────────────────
let SESSION_ID  = localStorage.getItem('sf_session') || null;
let activeContext = { district: null, soil: null, season: null, month: null, crop: null };
let isProcessing  = false;
let APP_LANGUAGE  = localStorage.getItem('sf_language') || 'en';
if (!['en', 'ta'].includes(APP_LANGUAGE)) APP_LANGUAGE = APP_LANGUAGE.startsWith('ta') ? 'ta' : 'en';

// ── DOM refs ──────────────────────────────────────────────────────────
const messagesList   = document.getElementById('messagesList');
const messagesWrap   = document.getElementById('messagesWrap');
const chatInput      = document.getElementById('chatInput');
const sendBtn        = document.getElementById('sendBtn');
const voiceInputBtn  = document.getElementById('voiceInputBtn');
const voiceStatus    = document.getElementById('voiceStatus');
const languageToggle = document.getElementById('languageToggle');
const clearChatBtn   = document.getElementById('clearChat');
const sidebarToggle  = document.getElementById('sidebarToggle');
const sidebar        = document.querySelector('.sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const soilImageInput = document.getElementById('soilImageInput');
const soilStrip      = document.getElementById('soilPreviewStrip');
const soilPreviewName = document.getElementById('soilPreviewName');
const removeImgBtn   = document.getElementById('removeImgBtn');

// Context display
const ctxCrop     = document.getElementById('ctxCrop');
const ctxDistrict = document.getElementById('ctxDistrict');
const ctxSoil     = document.getElementById('ctxSoil');
const ctxMonth    = document.getElementById('ctxMonth');
const ctxSeason   = document.getElementById('ctxSeason');
const topCtxCropLabel     = document.getElementById('topCtxCropLabel');
const topCtxDistrictLabel = document.getElementById('topCtxDistrictLabel');

// Weather
const weatherEmpty    = document.getElementById('weatherEmpty');
const weatherContent  = document.getElementById('weatherContent');
const weatherDistrict = document.getElementById('weatherDistrict');
const weatherTemp     = document.getElementById('weatherTemp');
const weatherCondition = document.getElementById('weatherCondition');
const weatherHumidity = document.getElementById('weatherHumidity');
const weatherRain     = document.getElementById('weatherRain');
const weatherWind     = document.getElementById('weatherWind');
const weatherHourly   = document.getElementById('weatherHourly');
const weatherDaily    = document.getElementById('weatherDaily');
const weatherSource   = document.querySelector('.weather-source');

// What-if
const whatifIrrSlider      = document.getElementById('whatifIrrSlider');
const whatifRainSlider     = document.getElementById('whatifRainSlider');
const whatifFertSlider     = document.getElementById('whatifFertSlider');
const whatifTempSlider     = document.getElementById('whatifTempSlider');
const whatifPestSlider     = document.getElementById('whatifPestSlider');
const whatifMoistureSlider = document.getElementById('whatifMoistureSlider');
const whatifIrrVal         = document.getElementById('whatifIrrVal');
const whatifRainVal        = document.getElementById('whatifRainVal');
const whatifFertVal        = document.getElementById('whatifFertVal');
const whatifTempVal        = document.getElementById('whatifTempVal');
const whatifPestVal        = document.getElementById('whatifPestVal');
const whatifMoistureVal    = document.getElementById('whatifMoistureVal');
const simulateBtn          = document.getElementById('simulateBtn');

// Manual context
const manualCrop      = document.getElementById('manualCrop');
const manualDistrict  = document.getElementById('manualDistrict');
const manualSoil      = document.getElementById('manualSoil');
const manualMonth     = document.getElementById('manualMonth');
const manualSeason    = document.getElementById('manualSeason');
const applyContextBtn = document.getElementById('applyContextBtn');
const resetContextBtn = document.getElementById('resetContextBtn');

// Weather state
let lastWeatherDistrict = null;
let weatherRequestId    = 0;
let latestWeatherData   = null;

// Voice input state
let recognition          = null;
let isListening          = false;
let stopVoiceRequested   = false;
let voiceTranscript      = '';
let voiceAutoStopTimer   = null;
let recognitionLangInUse = null;
let recognitionFallbackTimer = null;
let recognitionStartTimer    = null;

// ── Welcome Content ────────────────────────────────────────────────────
const INTRO_MESSAGE = `I'm your **Smart Farming AI** for Tamil Nadu — ask me anything about crops, soil, pest risks, rainfall, or farm economics.\n\nTry one of these:`;
const INTRO_MESSAGE_TA = `நான் தமிழ்நாட்டிற்கான **Smart Farming AI** — பயிர்கள், மண், பூச்சி அபாயம், மழை அல்லது வேளாண் பொருளாதாரம் பற்றி கேளுங்கள்.\n\nமுயற்சி செய்யலாம்:`;

const WELCOME_QUERIES = [
  'Best crops for Madurai with red soil during Kharif?',
  'How much rainfall does Coimbatore receive?',
  'Pest risk for rice in Dharmapuri?',
  'Overview of Erode district agriculture',
];
const WELCOME_QUERIES_TA = [
  'மதுரையில் சிவப்பு மண்ணில் காரிஃப் பருவத்திற்கு சிறந்த பயிர்கள்?',
  'கோயம்புத்தூர் மழை அளவு என்ன?',
  'தர்மபுரியில் நெல்லுக்கு பூச்சி அபாயம் என்ன?',
  'ஈரோடு மாவட்ட வேளாண்மை விவரம்',
];

// ── UI Text ────────────────────────────────────────────────────────────
const UI_TEXT = {
  en: {
    chatPlaceholder: 'Ask about crops, rainfall, fertilizer, pest risks...',
    voiceFooter:     'Smart Farming AI · Tamil Nadu · Context-aware agricultural assistant',
    manualUpdated:   '✅ Context updated.',
    noDistrict:      '⚠️ Set a district first, then run the simulation.',
    noSpeech:        'No speech detected. Tap the mic and try again.',
    listening:       'Listening… speak your question.',
    voiceSending:    'Sending voice input…',
    voiceStopped:    'Voice input stopped.',
    voiceTryAgain:   'Could not start voice input. Please try again.',
    micPermission:   'Microphone access was blocked.',
    heard:           t => `Heard: ${t}`,
    weatherEmpty:    'Ask about a district to load weather.',
  },
  ta: {
    chatPlaceholder: 'பயிர், மழை, உரம், பூச்சி அபாயம் பற்றி கேளுங்கள்...',
    voiceFooter:     'தமிழ்நாடு ஸ்மார்ட் வேளாண்மை AI · சூழல் சார்ந்த உதவியாளர்',
    manualUpdated:   '✅ சூழல் புதுப்பிக்கப்பட்டது.',
    noDistrict:      '⚠️ முதலில் மாவட்டத்தை அமைக்கவும்.',
    noSpeech:        'பேச்சு கண்டறியப்படவில்லை. மீண்டும் முயற்சிக்கவும்.',
    listening:       'கேட்கிறது… உங்கள் கேள்வியை பேசுங்கள்.',
    voiceSending:    'குரல் கேள்வி அனுப்பப்படுகிறது…',
    voiceStopped:    'குரல் உள்ளீடு நிறுத்தப்பட்டது.',
    voiceTryAgain:   'குரல் உள்ளீடு தொடங்க முடியவில்லை.',
    micPermission:   'மைக்ரோஃபோன் அனுமதி தடுக்கப்பட்டுள்ளது.',
    heard:           t => `கேட்டது: ${t}`,
    weatherEmpty:    'மாவட்டத்தைப் பற்றி கேட்டு வானிலை ஏற்றவும்.',
  }
};

function t(key) { return (UI_TEXT[APP_LANGUAGE] || UI_TEXT.en)[key] || UI_TEXT.en[key] || key; }

// ── Helpers ────────────────────────────────────────────────────────────
function getTime() {
  return new Date().toLocaleTimeString(APP_LANGUAGE === 'ta' ? 'ta-IN' : 'en-IN', { hour: '2-digit', minute: '2-digit' });
}

function prettyValue(v) {
  if (!v) return '—';
  return String(v).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function setVoiceStatus(msg, isError = false) {
  if (!voiceStatus) return;
  voiceStatus.textContent = msg || t('voiceFooter');
  voiceStatus.classList.toggle('voice-error', Boolean(isError));
}

// ── Season/Month sync ──────────────────────────────────────────────────
function monthToSeason(month) {
  const m = String(month || '').toLowerCase();
  if (['june','july','august','september'].includes(m)) return 'Kharif';
  if (['october','november'].includes(m)) return 'Rabi';
  if (['march','april','may'].includes(m)) return 'Summer';
  if (['december','january','february'].includes(m)) return 'Winter';
  return '';
}
function seasonToDefaultMonth(season) {
  const s = String(season || '').toLowerCase();
  if (s === 'winter') return 'January';
  if (s === 'summer') return 'April';
  if (s === 'kharif') return 'July';
  if (s === 'rabi') return 'November';
  return '';
}
function isMonthInSeason(month, season) {
  if (!month || !season || season === 'Whole Year') return true;
  return monthToSeason(month) === season;
}
function syncSeasonFromMonth() {
  if (!manualMonth || !manualSeason) return;
  const s = monthToSeason(manualMonth.value);
  if (s) manualSeason.value = s;
}
function syncMonthFromSeason() {
  if (!manualMonth || !manualSeason) return;
  const season = manualSeason.value;
  if (!season) return;
  if (!manualMonth.value || !isMonthInSeason(manualMonth.value, season))
    manualMonth.value = seasonToDefaultMonth(season);
}
function syncManualContextInputs() {
  if (manualCrop)     manualCrop.value     = activeContext.crop     || '';
  if (manualDistrict) manualDistrict.value = activeContext.district || '';
  if (manualSoil)     manualSoil.value     = activeContext.soil     || '';
  if (manualMonth)    manualMonth.value    = activeContext.month    || '';
  if (manualSeason)   manualSeason.value   = activeContext.season   || '';
}

// ── Context UI Updates (Triggered automatically whenever context changes) ──
function updateContextUI(memory = {}) {
  const prevDistrict = activeContext.district;
  activeContext = { ...activeContext, ...memory };

  // Update Sidebar Active Context cards
  if (ctxCrop)     ctxCrop.textContent     = prettyValue(activeContext.crop);
  if (ctxDistrict) ctxDistrict.textContent = prettyValue(activeContext.district);
  if (ctxSoil)     ctxSoil.textContent     = prettyValue(activeContext.soil);
  if (ctxMonth)    ctxMonth.textContent    = prettyValue(activeContext.month);
  if (ctxSeason)   ctxSeason.textContent   = prettyValue(activeContext.season);

  // Update Topbar Context chips
  if (topCtxCropLabel)     topCtxCropLabel.textContent     = activeContext.crop     ? prettyValue(activeContext.crop)     : (APP_LANGUAGE === 'ta' ? 'பயிர் அமைக்கப்படவில்லை' : 'No crop set');
  if (topCtxDistrictLabel) topCtxDistrictLabel.textContent = activeContext.district ? prettyValue(activeContext.district) : (APP_LANGUAGE === 'ta' ? 'மாவட்டம் அமைக்கப்படவில்லை' : 'No district set');

  syncManualContextInputs();
  updateWhatIfLabels();

  // Auto-fetch weather if district changed in conversation
  if (activeContext.district && activeContext.district !== prevDistrict) {
    loadWeatherForDistrict(activeContext.district);
  } else if (!activeContext.district) {
    resetWeatherUI();
  }
}

function clearContextUI() {
  activeContext = { district: null, soil: null, season: null, month: null, crop: null };
  updateContextUI({});
}

// ── Weather ────────────────────────────────────────────────────────────
const WEATHER_CODES = {
  0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',
  45:'Fog',51:'Light drizzle',53:'Moderate drizzle',55:'Heavy drizzle',
  61:'Slight rain',63:'Moderate rain',65:'Heavy rain',
  80:'Slight showers',81:'Moderate showers',82:'Heavy showers',
  95:'Thunderstorm',96:'Thunderstorm + hail',99:'Severe thunderstorm'
};
function weatherCodeText(code) { return WEATHER_CODES[parseInt(code)] || 'Weather update'; }

function formatNum(v, suffix = '') {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  return isNaN(n) ? '—' : `${Math.round(n)}${suffix}`;
}
function formatTime(v) {
  if (!v) return '—';
  const d = new Date(v);
  return isNaN(d) ? String(v).slice(11, 16) : d.toLocaleTimeString('en-IN', { hour: 'numeric', hour12: true });
}
function formatDate(v) {
  if (!v) return '—';
  const d = new Date(`${v}T00:00:00`);
  return isNaN(d) ? v : d.toLocaleDateString(APP_LANGUAGE === 'ta' ? 'ta-IN' : 'en-IN', { weekday: 'short' });
}

function resetWeatherUI(msg = null) {
  lastWeatherDistrict = null; latestWeatherData = null;
  if (weatherEmpty)  { weatherEmpty.hidden = false; weatherEmpty.textContent = msg || t('weatherEmpty'); }
  if (weatherContent)  weatherContent.hidden = true;
}

function renderWeather(data) {
  if (!weatherContent) return;
  latestWeatherData = data;
  const cur = data.current || {};
  if (weatherEmpty)    weatherEmpty.hidden = true;
  weatherContent.hidden = false;
  if (weatherDistrict)  weatherDistrict.textContent  = data.district || '—';
  if (weatherSource)    weatherSource.textContent     = data.source   || '';
  if (weatherTemp)      weatherTemp.textContent       = formatNum(cur.temp_c, '°C');
  if (weatherCondition) weatherCondition.textContent  = weatherCodeText(cur.weather_code ?? cur.condition);
  if (weatherHumidity)  weatherHumidity.textContent   = `💧 ${formatNum(cur.humidity_pct, '%')}`;
  if (weatherRain)      weatherRain.textContent       = `🌧 ${formatNum(cur.rain_mm ?? cur.precipitation_mm, ' mm')}`;
  if (weatherWind)      weatherWind.textContent       = `💨 ${formatNum(cur.wind_kmh, ' km/h')}`;
  if (weatherHourly) {
    weatherHourly.innerHTML = '';
    (data.hourly || []).slice(0, 4).forEach(item => {
      const row = document.createElement('div');
      row.className = 'weather-mini-row';
      row.innerHTML = `<span>${formatTime(item.time)}</span><strong>${formatNum(item.temp_c, '°')}</strong><em>${formatNum(item.rain_probability_pct, '% rain')}</em>`;
      weatherHourly.appendChild(row);
    });
  }
  if (weatherDaily) {
    weatherDaily.innerHTML = '';
    (data.daily || []).slice(0, 3).forEach(item => {
      const row = document.createElement('div');
      row.className = 'weather-mini-row';
      row.innerHTML = `<span>${formatDate(item.date)}</span><strong>${formatNum(item.temp_min_c, '°')} / ${formatNum(item.temp_max_c, '°')}</strong><em>${formatNum(item.rain_sum_mm, ' mm')}</em>`;
      weatherDaily.appendChild(row);
    });
  }
}

async function loadWeatherForDistrict(district) {
  if (!district || district === lastWeatherDistrict) return;
  lastWeatherDistrict = district;
  const reqId = ++weatherRequestId;
  if (weatherEmpty)  { weatherEmpty.hidden = false; weatherEmpty.textContent = `Loading weather for ${district}…`; }
  if (weatherContent)  weatherContent.hidden = true;
  try {
    const res  = await fetch(`/weather?district=${encodeURIComponent(district)}`);
    const data = await res.json();
    if (reqId !== weatherRequestId) return;
    if (!res.ok || data.error) { resetWeatherUI(data.error || 'Weather unavailable.'); return; }
    renderWeather(data);
  } catch (_) {
    if (reqId === weatherRequestId) resetWeatherUI('Weather unavailable right now.');
  }
}

// ── Manual Context Actions ─────────────────────────────────────────────
async function persistManualContext(ctx) {
  try {
    const res  = await fetch('/set_context', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: SESSION_ID, memory: ctx }) });
    const data = await res.json();
    if (data.session_id) { SESSION_ID = data.session_id; localStorage.setItem('sf_session', SESSION_ID); }
  } catch (_) {}
}

async function applyManualContext() {
  const ctx = {
    crop:     manualCrop.value.trim()     || null,
    district: manualDistrict.value.trim() || null,
    soil:     manualSoil.value             || null,
    month:    manualMonth.value            || null,
    season:   manualSeason.value           || null,
  };
  if (ctx.month && !ctx.season) ctx.season = monthToSeason(ctx.month);
  if (ctx.season && !isMonthInSeason(ctx.month, ctx.season)) ctx.month = seasonToDefaultMonth(ctx.season) || ctx.month;
  updateContextUI(ctx);
  await persistManualContext(ctx);
  renderMessage(t('manualUpdated'), 'bot');
}

async function resetManualContext() {
  clearContextUI();
  await persistManualContext(activeContext);
}

// ── Markdown Parser ────────────────────────────────────────────────────
function inlineFormat(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`([^`]+)`/g,     '<code>$1</code>');
}

function parseTable(match, header, sep, body) {
  const headers = header.trim().split('|').map(c => c.trim()).filter(Boolean);
  const rows    = body.trim().split('\n').filter(r => r.includes('|'));
  let html = '<table><thead><tr>';
  headers.forEach(c => html += `<th>${inlineFormat(c)}</th>`);
  html += '</tr></thead><tbody>';
  rows.forEach(row => {
    const cells = row.trim().split('|').map(c => c.trim()).filter(Boolean);
    html += '<tr>' + cells.map(c => `<td>${inlineFormat(c)}</td>`).join('') + '</tr>';
  });
  html += '</tbody></table>';
  return '\n' + html + '\n';
}

function parseMarkdown(text) {
  text = text.replace(/\n(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g, parseTable);
  const lines = text.split('\n');
  let html = '', inList = false;
  for (const line of lines) {
    if      (/^### (.+)/.test(line))  { if (inList) { html += '</ul>'; inList = false; } html += `<h3>${inlineFormat(line.slice(4))}</h3>`; }
    else if (/^## (.+)/.test(line))   { if (inList) { html += '</ul>'; inList = false; } html += `<h2>${inlineFormat(line.slice(3))}</h2>`; }
    else if (/^# (.+)/.test(line))    { if (inList) { html += '</ul>'; inList = false; } html += `<h1>${inlineFormat(line.slice(2))}</h1>`; }
    else if (/^[*\-] (.+)/.test(line)){ if (!inList) { html += '<ul>'; inList = true; } html += `<li>${inlineFormat(line.replace(/^[*\-] /, ''))}</li>`; }
    else if (line.trim().startsWith('<table')) { if (inList) { html += '</ul>'; inList = false; } html += line; }
    else if (line.trim() === '')       { if (inList) { html += '</ul>'; inList = false; } html += '<br>'; }
    else                               { if (inList) { html += '</ul>'; inList = false; } html += `<p>${inlineFormat(line)}</p>`; }
  }
  if (inList) html += '</ul>';
  return html;
}

// ── Follow-up Chips ────────────────────────────────────────────────────
function generateContextChips(ctx, lang) {
  const d = ctx.district ? prettyValue(ctx.district) : null;
  const c = ctx.crop ? prettyValue(ctx.crop) : null;
  const isTa = lang === 'ta';

  if (isTa) {
    if (d && c) return [`${d}-இல் ${c}-க்கு உரம் என்ன?`, `${d}-இல் ${c}-க்கு பூச்சி அபாயம் என்ன?`, `${d}-இல் ${c} லாப மதிப்பீடு?`];
    if (d)      return [`${d}-இல் சிறந்த பயிர்கள்?`, `${d} மழை அளவு என்ன?`, `${d} மாவட்ட விவரம்?`];
    if (c)      return [`${c}-க்கு உரம் என்ன?`, `${c}-க்கு பூச்சி அபாயம் என்ன?`, `${c} பயிரிட சரியான நேரம்?`];
    return ['மதுரையில் காரிஃப் சிறந்த பயிர்கள்?', 'கோயம்புத்தூர் மழை அளவு என்ன?', 'தஞ்சாவூரில் நெல்லுக்கு பூச்சி அபாயம்?'];
  } else {
    if (d && c) return [`Fertilizer recommendation for ${c} in ${d}?`, `Pest risk for ${c} in ${d}?`, `Estimate profit for ${c} in ${d}?`];
    if (d)      return [`Best crops for ${d}?`, `${d} rainfall stats?`, `${d} district overview?`];
    if (c)      return [`Fertilizer recommendation for ${c}?`, `Pest risk for ${c}?`, `Planting time for ${c}?`];
    return ['Best crops for Madurai during Kharif?', 'Coimbatore rainfall stats?', 'Pest risk for rice in Thanjavur?'];
  }
}

function extractFollowupChips(text) {
  if (!text) return generateContextChips(activeContext, APP_LANGUAGE);
  const m = text.match(/FOLLOWUP_CHIPS:\s*([^\n]+)/i);
  if (!m) return generateContextChips(activeContext, APP_LANGUAGE);

  const raw = m[1].replace(/\*\*$/,'').trim();
  const parts = raw.split('|').map(x => x.replace(/^[\s*"-]+|[\s*"-]+$/g, '').trim()).filter(Boolean);

  const valid = parts.filter(chip => {
    if (chip.length < 3 || chip.length > 65 || chip.split(/\s+/).length > 10) return false;
    const lower = chip.toLowerCase();
    return chip.endsWith('?') ||
      /^(what|how|which|best|pest|fertilizer|profit|yield|rainfall|overview|wage|irrigation|planting|மழை|உரம்|பூச்சி|பயிர்|விவரம்|லாபம்)/.test(lower);
  });

  return valid.length >= 2 ? valid : generateContextChips(activeContext, APP_LANGUAGE);
}

function removeFollowupMarker(text) {
  if (!text) return '';
  return text
    .replace(/---\s*\*\*FOLLOWUP_CHIPS:[^\n]*\*\*/gi, '')
    .replace(/FOLLOWUP_CHIPS:[^\n]*/gi, '')
    .trim();
}

// ── Message Rendering ─────────────────────────────────────────────────
function renderMessage(text, role, animate = true, isWelcome = false) {
  const row = document.createElement('div');
  row.className = `msg-row ${role === 'user' ? 'user-row' : 'bot-row'}`;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar ${role === 'user' ? 'user-avatar' : 'bot-avatar'}`;
  avatar.textContent = role === 'user' ? '👤' : '🌿';

  const content = document.createElement('div');
  content.className = 'msg-content';

  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role === 'user' ? 'user-bubble' : 'bot-bubble'}`;
  bubble.innerHTML  = role === 'user' ? text.replace(/</g,'&lt;') : parseMarkdown(removeFollowupMarker(text));

  content.appendChild(bubble);

  if (role === 'bot' && isWelcome) content.appendChild(createWelcomeChips());

  if (role === 'bot') {
    const chips = extractFollowupChips(text);
    if (chips.length) content.appendChild(buildChips(chips));
  }

  const bottomBar = document.createElement('div');
  bottomBar.className = 'msg-bottom';
  bottomBar.innerHTML = `<span class="msg-time">${getTime()}</span>`;
  content.appendChild(bottomBar);

  row.appendChild(avatar);
  row.appendChild(content);
  messagesList.appendChild(row);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
}

function buildChips(chips) {
  const wrap = document.createElement('div');
  wrap.className = 'followup-chips';
  chips.forEach(chip => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'followup-chip';
    btn.textContent = chip;
    btn.addEventListener('click', () => sendMessage(chip));
    wrap.appendChild(btn);
  });
  return wrap;
}

function createWelcomeChips() {
  const wrap    = document.createElement('div');
  wrap.className = 'welcome-chips';
  const queries = APP_LANGUAGE === 'ta' ? WELCOME_QUERIES_TA : WELCOME_QUERIES;
  queries.forEach(q => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'welcome-chip';
    btn.textContent = q;
    btn.addEventListener('click', () => { chatInput.value = q; chatInput.focus(); });
    wrap.appendChild(btn);
  });
  return wrap;
}

// ── Typing Indicator ──────────────────────────────────────────────────
let typingEl = null;
function showTyping() {
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'msg-row typing-row bot-row';
  typingEl.innerHTML = `<div class="msg-avatar bot-avatar">🌿</div><div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div><span class="typing-label">Thinking…</span></div>`;
  messagesList.appendChild(typingEl);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
}
function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

// ── Streaming Bubble ──────────────────────────────────────────────────
function createStreamingBubble() {
  const row = document.createElement('div');
  row.className = 'msg-row bot-row';
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar bot-avatar';
  avatar.textContent = '🌿';
  const content = document.createElement('div');
  content.className = 'msg-content';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble bot-bubble streaming-bubble';
  content.appendChild(bubble);
  row.appendChild(avatar);
  row.appendChild(content);
  messagesList.appendChild(row);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
  return { row, bubble, content };
}

function finaliseStreamingBubble(bubble, content, fullText) {
  bubble.classList.remove('streaming-bubble', 'streaming-active');
  bubble.innerHTML = parseMarkdown(removeFollowupMarker(fullText));

  const chips = extractFollowupChips(fullText);
  if (chips.length) content.appendChild(buildChips(chips));

  const bottomBar = document.createElement('div');
  bottomBar.className = 'msg-bottom';
  bottomBar.innerHTML = `<span class="msg-time">${getTime()}</span>`;
  content.appendChild(bottomBar);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
}

// ── Send Message & Receive Memory Updates ──────────────────────────────
async function sendMessage(text) {
  text = (text || '').trim();
  if (isProcessing || !text) return;

  // ── /price command shortcut ──────────────────────────────────────────
  const priceMatch = text.match(/^\/price\s+(.+)/i);
  if (priceMatch) {
    const commodity = priceMatch[1].trim();
    renderMessage(text, 'user');
    chatInput.value = '';
    showTyping();
    try {
      const txt = window._fetchPriceFor ? await window._fetchPriceFor(commodity, activeContext.district) : null;
      hideTyping();
      if (txt) renderMessage(txt, 'bot');
      else renderMessage(`❌ No price data found for "${commodity}". Try selecting from the Market Price tool.`, 'bot');
    } catch (e) {
      hideTyping();
      renderMessage(`❌ Could not fetch price for "${commodity}": ${e.message}`, 'bot');
    }
    return;
  }

  isProcessing = true;
  renderMessage(text, 'user');
  chatInput.value = '';
  sendBtn.disabled = true;
  showTyping();

  let fullText = '', streamBubble = null, streamContent = null;

  try {
    const res = await fetch('/chat_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: SESSION_ID, language: APP_LANGUAGE })
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data:')) continue;
        let evt;
        try { evt = JSON.parse(line.slice(5).trim()); } catch { continue; }

        if (evt.type === 'token') {
          if (!streamBubble) {
            hideTyping();
            const c = createStreamingBubble();
            streamBubble = c.bubble; streamContent = c.content;
          }
          fullText += evt.token;
          streamBubble.textContent = removeFollowupMarker(fullText);
          streamBubble.classList.add('streaming-active');
          messagesWrap.scrollTop = messagesWrap.scrollHeight;

        } else if (evt.type === 'done') {
          if (evt.session_id) { SESSION_ID = evt.session_id; localStorage.setItem('sf_session', SESSION_ID); }
          // CRITICAL: Update active context automatically whenever memory changes!
          if (evt.memory) updateContextUI(evt.memory);

        } else if (evt.type === 'error') {
          throw new Error(evt.message || 'Stream error');
        }
      }
    }

    if (streamBubble) {
      finaliseStreamingBubble(streamBubble, streamContent, fullText);
    } else {
      hideTyping();
      renderMessage(fullText || (APP_LANGUAGE === 'ta' ? 'பதில் கிடைக்கவில்லை.' : 'No response received.'), 'bot');
    }

  } catch (err) {
    hideTyping();
    if (streamBubble && fullText) {
      finaliseStreamingBubble(streamBubble, streamContent, fullText + '\n\n⚠️ *Response may be incomplete.*');
    } else {
      renderMessage(
        APP_LANGUAGE === 'ta'
          ? '⚠️ இணைப்பு பிழை. சேவையகம் இயங்குகிறதா என சரிபார்க்கவும்.'
          : '⚠️ Connection error. Please check if the server is running.',
        'bot'
      );
    }
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// ── Typewriter Animation Stream for Non-SSE Endpoints ─────────────────
async function typeStreamMessage(text) {
  if (!text) return;
  hideTyping();
  const { bubble, content } = createStreamingBubble();
  bubble.classList.add('streaming-active');

  const tokens = text.match(/\S+|\s+/g) || [text];
  let accumulated = '';

  for (const token of tokens) {
    accumulated += token;
    bubble.textContent = removeFollowupMarker(accumulated);
    messagesWrap.scrollTop = messagesWrap.scrollHeight;
    await new Promise(resolve => setTimeout(resolve, 16));
  }

  finaliseStreamingBubble(bubble, content, accumulated);
}

// ── Soil Image Upload ─────────────────────────────────────────────────
async function analyzeSoilImage(file) {
  if (!file || isProcessing) return;
  isProcessing = true;
  renderMessage(`📸 Uploaded: ${file.name}`, 'user');
  showTyping();
  if (soilPreviewName) soilPreviewName.textContent = `Analyzing ${file.name}…`;
  if (soilStrip) soilStrip.style.display = 'flex';
  const form = new FormData();
  form.append('image', file);
  form.append('session_id', SESSION_ID || '');
  form.append('language', APP_LANGUAGE);
  if (activeContext.district) form.append('district', activeContext.district);
  try {
    const res  = await fetch('/soil', { method: 'POST', body: form });
    const data = await res.json();
    if (data.session_id) { SESSION_ID = data.session_id; localStorage.setItem('sf_session', SESSION_ID); }
    if (data.memory)     updateContextUI(data.memory);
    if (soilPreviewName) soilPreviewName.textContent = data.soil_type ? `Detected: ${data.soil_type}` : `Could not analyze`;
    await typeStreamMessage(data.error ? `❌ ${data.error}` : data.text);
  } catch (_) {
    if (soilPreviewName) soilPreviewName.textContent = 'Upload failed';
    hideTyping();
    renderMessage(APP_LANGUAGE === 'ta' ? 'மண் படம் பதிவேற்ற முடியவில்லை.' : 'Soil image upload failed.', 'bot');
  } finally {
    isProcessing = false;
    if (soilImageInput) soilImageInput.value = '';
    sendBtn.disabled = false;
  }
}

// ── What-If Simulator ─────────────────────────────────────────────────
function updateWhatIfLabels() {
  if (whatifIrrVal && whatifIrrSlider)           whatifIrrVal.textContent      = `${whatifIrrSlider.value}%`;
  if (whatifRainVal && whatifRainSlider)          whatifRainVal.textContent     = `${whatifRainSlider.value} mm`;
  if (whatifFertVal && whatifFertSlider)          whatifFertVal.textContent     = `${whatifFertSlider.value}%`;
  if (whatifTempVal && whatifTempSlider)          whatifTempVal.textContent     = `${whatifTempSlider.value}°C`;
  if (whatifPestVal && whatifPestSlider)          whatifPestVal.textContent     = `${whatifPestSlider.value}%`;
  if (whatifMoistureVal && whatifMoistureSlider)  whatifMoistureVal.textContent = `${whatifMoistureSlider.value}%`;
  if (simulateBtn) simulateBtn.textContent = activeContext.district ? `▶ Simulate for ${activeContext.district}` : '▶ Run Simulation';
}

async function sendSimulation() {
  if (!activeContext.district) {
    renderMessage(t('noDistrict'), 'bot'); return;
  }
  const payload = {
    district:             activeContext.district,
    crop:                 activeContext.crop,
    soil:                 activeContext.soil,
    season:               activeContext.season,
    irrigation_delta_pct: parseInt(whatifIrrSlider?.value  || 0),
    rainfall_delta_mm:    parseInt(whatifRainSlider?.value  || 0),
    fertilizer_delta_pct: parseInt(whatifFertSlider?.value  || 0),
    temperature_delta_c:  parseInt(whatifTempSlider?.value  || 0),
    pest_intensity_pct:   parseInt(whatifPestSlider?.value  || 0),
    soil_moisture_pct:    parseInt(whatifMoistureSlider?.value || 55),
    language: APP_LANGUAGE,
  };
  const scenarioText = APP_LANGUAGE === 'ta'
    ? `${activeContext.district} மாவட்டத்தில் ${payload.crop || 'பயிர்'} பயிருக்கு சோதனை: மழை ${payload.rainfall_delta_mm} மி.மீ, பாசனம் ${payload.irrigation_delta_pct}%`
    : `Running simulation for ${payload.crop || 'current crop'} in ${activeContext.district}`;
  renderMessage(scenarioText, 'user');
  showTyping();
  if (simulateBtn) simulateBtn.disabled = true;
  try {
    const res  = await fetch('/simulate_advanced', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Simulation failed');
    await typeStreamMessage(data.text || 'Simulation complete.');
  } catch (err) {
    hideTyping();
    renderMessage(APP_LANGUAGE === 'ta' ? 'சோதனை இப்போது கிடைக்கவில்லை.' : `Simulation unavailable: ${err.message}`, 'bot');
  } finally {
    if (simulateBtn) simulateBtn.disabled = false;
  }
}

// ── Voice Input ────────────────────────────────────────────────────────
function languageCode() { return APP_LANGUAGE === 'ta' ? 'ta-IN' : 'en-IN'; }

function updateVoiceButton() {
  if (!voiceInputBtn) return;
  voiceInputBtn.classList.toggle('listening', isListening);
  voiceInputBtn.title = isListening ? 'Stop listening' : 'Voice input';
  voiceInputBtn.setAttribute('aria-label', isListening ? 'Stop listening' : 'Start voice input');
}

function createSpeechRecognition(langOverride = null) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (voiceInputBtn) { voiceInputBtn.disabled = true; voiceInputBtn.title = 'Voice not supported'; }
    return null;
  }
  const rec = new SpeechRecognition();
  rec.lang = langOverride || languageCode();
  recognitionLangInUse = rec.lang;
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    clearTimeout(recognitionStartTimer);
    isListening = true; stopVoiceRequested = false; voiceTranscript = '';
    clearTimeout(recognitionFallbackTimer);
    if (APP_LANGUAGE === 'ta' && recognitionLangInUse === 'ta-IN') {
      recognitionFallbackTimer = setTimeout(() => {
        if (isListening && !voiceTranscript && !chatInput.value.trim()) {
          try { stopVoiceRequested = true; recognition.stop(); } catch(_) {}
          setTimeout(() => {
            try { stopVoiceRequested = false; startRecognition('en-IN'); setVoiceStatus('Tamil voice unavailable — retrying in English…'); } catch(_) {}
          }, 250);
        }
      }, 3500);
    }
    updateVoiceButton();
    setVoiceStatus(t('listening'));
  };

  rec.onresult = event => {
    clearTimeout(voiceAutoStopTimer); clearTimeout(recognitionFallbackTimer);
    let finalText = voiceTranscript, interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const tr = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal) finalText = `${finalText} ${tr}`.trim();
      else interimText = `${interimText} ${tr}`.trim();
    }
    voiceTranscript = finalText;
    const spoken = (finalText || interimText).trim();
    if (spoken) { chatInput.value = spoken; chatInput.focus(); setVoiceStatus(t('heard')(spoken)); }
  };

  rec.onspeechend = () => {
    clearTimeout(voiceAutoStopTimer);
    voiceAutoStopTimer = setTimeout(() => { if (recognition && isListening) { try { recognition.stop(); } catch(_) {} } }, 900);
  };

  rec.onerror = event => {
    clearTimeout(voiceAutoStopTimer); clearTimeout(recognitionFallbackTimer); clearTimeout(recognitionStartTimer);
    const isPermission = event.error === 'not-allowed' || event.error === 'service-not-allowed';
    const canRetry = APP_LANGUAGE === 'ta' && recognitionLangInUse === 'ta-IN' && !voiceTranscript && !isPermission;
    if (canRetry) {
      try { recognition = createSpeechRecognition('en-IN'); recognition.start(); setVoiceStatus('Retrying in English…'); return; } catch(_) {}
    }
    isListening = false; stopVoiceRequested = true;
    updateVoiceButton();
    setVoiceStatus(isPermission ? t('micPermission') : t('voiceTryAgain'), true);
  };

  rec.onend = () => {
    clearTimeout(voiceAutoStopTimer); clearTimeout(recognitionFallbackTimer); clearTimeout(recognitionStartTimer);
    const text = (voiceTranscript || chatInput.value).trim();
    const shouldSend = isListening && !stopVoiceRequested && text;
    isListening = false; updateVoiceButton();
    if (shouldSend)         { setVoiceStatus(t('voiceSending')); sendMessage(text); }
    else if (!text && !stopVoiceRequested) setVoiceStatus(t('noSpeech'), true);
    else                    setVoiceStatus(t('voiceStopped'));
  };

  return rec;
}

function initVoiceInput() { recognition = createSpeechRecognition(); }

function startRecognition(langOverride = null) {
  recognition = createSpeechRecognition(langOverride);
  if (!recognition) return;
  recognition.lang = langOverride || languageCode();
  recognitionLangInUse = recognition.lang;
  recognition.start();
  clearTimeout(recognitionStartTimer);
  recognitionStartTimer = setTimeout(() => {
    if (!isListening) {
      try { recognition.abort(); } catch(_) {}
      recognition = createSpeechRecognition();
      updateVoiceButton();
      setVoiceStatus(t('voiceTryAgain'), true);
    }
  }, 2500);
}

async function toggleVoiceInput() {
  if (!recognition || isProcessing) return;
  if (isListening) {
    stopVoiceRequested = true;
    clearTimeout(voiceAutoStopTimer); clearTimeout(recognitionFallbackTimer); clearTimeout(recognitionStartTimer);
    recognition.stop(); return;
  }
  try {
    setVoiceStatus('Starting microphone…');
    stopVoiceRequested = false; voiceTranscript = '';
    clearTimeout(voiceAutoStopTimer); clearTimeout(recognitionFallbackTimer); clearTimeout(recognitionStartTimer);
    chatInput.value = '';
    startRecognition();
  } catch(err) {
    if (err?.name === 'InvalidStateError' && recognition) {
      try { recognition.stop(); } catch(_) {}
      setTimeout(() => { try { stopVoiceRequested = false; startRecognition(); } catch(_) { setVoiceStatus(t('voiceTryAgain'), true); } }, 250);
      return;
    }
    updateVoiceButton(); setVoiceStatus(t('voiceTryAgain'), true);
  }
}

// ── Language Toggle ────────────────────────────────────────────────────
function applyPageLanguage() {
  document.documentElement.lang = APP_LANGUAGE;
  if (languageToggle) languageToggle.classList.toggle('tamil-mode', APP_LANGUAGE === 'ta');
  if (chatInput)     chatInput.placeholder = t('chatPlaceholder');
  setVoiceStatus(t('voiceFooter'));
  if (weatherEmpty && weatherContent?.hidden) weatherEmpty.textContent = t('weatherEmpty');
  if (latestWeatherData && weatherContent && !weatherContent.hidden) renderWeather(latestWeatherData);
  if (recognition) recognition.lang = languageCode();
}

function toggleLanguage() {
  APP_LANGUAGE = APP_LANGUAGE === 'ta' ? 'en' : 'ta';
  localStorage.setItem('sf_language', APP_LANGUAGE);
  applyPageLanguage();
  renderWelcome();
}

// ── Session / Reset ────────────────────────────────────────────────────
async function clearChat() {
  messagesList.innerHTML = '';
  const old = SESSION_ID;
  SESSION_ID = null; localStorage.removeItem('sf_session');
  clearContextUI();
  if (old) { try { await fetch('/reset_session', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ session_id: old }) }); } catch(_) {} }
  renderWelcome();
}

function renderWelcome() {
  messagesList.innerHTML = '';
  renderMessage(APP_LANGUAGE === 'ta' ? INTRO_MESSAGE_TA : INTRO_MESSAGE, 'bot', true, true);
}

async function restoreSessionOnLoad() {
  chatInput.value = '';
  if (soilStrip) soilStrip.style.display = 'none';
  if (soilImageInput) soilImageInput.value = '';
  updateWhatIfLabels();
  if (!SESSION_ID) { clearContextUI(); return false; }
  try {
    const res  = await fetch(`/session?session_id=${encodeURIComponent(SESSION_ID)}`);
    const data = await res.json();
    if (data?.memory) updateContextUI(data.memory);
    if (Array.isArray(data.messages) && data.messages.length) {
      messagesList.innerHTML = '';
      data.messages.forEach(item => {
        if (item?.text && (item.role === 'user' || item.role === 'bot'))
          renderMessage(item.text, item.role, false, false);
      });
      return true;
    }
  } catch (_) { updateContextUI(activeContext); }
  return false;
}

// ── Sidebar Toggle ─────────────────────────────────────────────────────
function setSidebarOpen(open) {
  if (!sidebar) return;
  sidebar.classList.toggle('open', Boolean(open));
  if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  if (sidebarBackdrop) sidebarBackdrop.style.opacity = open ? '1' : '0';
  if (sidebarBackdrop) sidebarBackdrop.style.pointerEvents = open ? 'auto' : 'none';
}

// ── Event Listeners ────────────────────────────────────────────────────
sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(chatInput.value.trim()); }
});
if (voiceInputBtn)  voiceInputBtn.addEventListener('click', toggleVoiceInput);
if (languageToggle) languageToggle.addEventListener('click', toggleLanguage);
clearChatBtn.addEventListener('click', clearChat);
sidebarToggle.addEventListener('click', () => setSidebarOpen(!sidebar.classList.contains('open')));
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', () => setSidebarOpen(false));
if (removeImgBtn) removeImgBtn.addEventListener('click', () => {
  if (soilStrip) soilStrip.style.display = 'none';
  if (soilImageInput) soilImageInput.value = '';
});
if (soilImageInput) soilImageInput.addEventListener('change', () => {
  const file = soilImageInput.files[0];
  if (file) analyzeSoilImage(file);
});
if (whatifIrrSlider)      whatifIrrSlider.addEventListener('input', updateWhatIfLabels);
if (whatifRainSlider)     whatifRainSlider.addEventListener('input', updateWhatIfLabels);
if (whatifFertSlider)     whatifFertSlider.addEventListener('input', updateWhatIfLabels);
if (whatifTempSlider)     whatifTempSlider.addEventListener('input', updateWhatIfLabels);
if (whatifPestSlider)     whatifPestSlider.addEventListener('input', updateWhatIfLabels);
if (whatifMoistureSlider) whatifMoistureSlider.addEventListener('input', updateWhatIfLabels);
if (simulateBtn)      simulateBtn.addEventListener('click', sendSimulation);
if (applyContextBtn)  applyContextBtn.addEventListener('click', applyManualContext);
if (resetContextBtn)  resetContextBtn.addEventListener('click', resetManualContext);
if (manualMonth)      manualMonth.addEventListener('change', syncSeasonFromMonth);
if (manualSeason)     manualSeason.addEventListener('change', syncMonthFromSeason);

document.addEventListener('click', e => {
  if (window.innerWidth <= 768 && sidebar?.classList.contains('open')) {
    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) setSidebarOpen(false);
  }
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && sidebar?.classList.contains('open')) setSidebarOpen(false);
});

// ── Init ──────────────────────────────────────────────────────────────
(async function init() {
  applyPageLanguage();
  initVoiceInput();
  const restored = await restoreSessionOnLoad();
  if (!restored) renderWelcome();
  chatInput.focus();
  initPriceModal();
  initSoilModal();
  initChatMenu();
})();

// ── Chat Menu (tools icon in input area) ─────────────────────────────
function initChatMenu() {
  const menuBtn     = document.getElementById('chatMenuBtn');
  const menuPanel   = document.getElementById('chatMenuPanel');
  const priceToolBtn = document.getElementById('chatToolPriceBtn');
  const soilToolBtn  = document.getElementById('chatToolSoilBtn');

  if (!menuBtn || !menuPanel) return;

  function openMenu() {
    menuPanel.hidden = false;
    menuBtn.setAttribute('aria-expanded', 'true');
    menuPanel.classList.add('menu-visible');
  }
  function closeMenu() {
    menuPanel.hidden = true;
    menuBtn.setAttribute('aria-expanded', 'false');
    menuPanel.classList.remove('menu-visible');
  }

  menuBtn.addEventListener('click', e => {
    e.stopPropagation();
    menuPanel.hidden ? openMenu() : closeMenu();
  });

  // Close on outside click
  document.addEventListener('click', e => {
    if (!menuPanel.hidden && !menuPanel.contains(e.target) && e.target !== menuBtn) {
      closeMenu();
    }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !menuPanel.hidden) closeMenu(); });

  priceToolBtn?.addEventListener('click', () => {
    closeMenu();
    if (window._openPriceModal) window._openPriceModal();
  });
  soilToolBtn?.addEventListener('click', () => {
    closeMenu();
    if (window._openSoilModal) window._openSoilModal();
  });
}

// ════════════════════════════════════════════════════════════════════════
// MARKET PRICE MODAL
// ════════════════════════════════════════════════════════════════════════
let _priceLastData = null;

function initPriceModal() {
  const overlay       = document.getElementById('priceModalOverlay');
  const openBtn       = document.getElementById('openPriceModal');
  const closeBtn      = document.getElementById('closePriceModal');
  const commoditySel  = document.getElementById('priceCommoditySelect');
  const districtSel   = document.getElementById('priceDistrictSelect');
  const fetchBtn      = document.getElementById('priceFetchBtn');
  const resultArea    = document.getElementById('priceResultArea');
  const cardsGrid     = document.getElementById('priceCardsGrid');
  const dateBadge     = document.getElementById('priceDateBadge');
  const emptyEl       = document.getElementById('priceEmpty');
  const errorEl       = document.getElementById('priceError');
  const loadingEl     = document.getElementById('priceLoading');
  const addChatBtn    = document.getElementById('priceAddChatBtn');

  // openBtn is optional (no longer in topbar; opened via chat-menu tool cards)
  if (!overlay) return;

  // ── Open / Close ─────────────────────────────────────────────────────
  function openPriceModal() {
    overlay.hidden = false;
    document.body.style.overflow = 'hidden';
    populatePriceDropdowns();
    // Pre-fill commodity from active context (crop)
    if (activeContext.crop && commoditySel) {
      const val = activeContext.crop;
      [...commoditySel.options].forEach(opt => {
        if (opt.value.toLowerCase().includes(val.toLowerCase())) commoditySel.value = opt.value;
      });
    }
  }
  function closePriceModal() {
    overlay.hidden = true;
    document.body.style.overflow = '';
  }
  openBtn?.addEventListener('click', openPriceModal);
  closeBtn?.addEventListener('click', closePriceModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closePriceModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !overlay.hidden) closePriceModal(); });
  document.querySelectorAll('.trigger-price-modal').forEach(btn => {
    btn.addEventListener('click', openPriceModal);
  });

  // ── Populate Dropdowns ───────────────────────────────────────────────
  let _dropdownsLoaded = false;
  async function populatePriceDropdowns() {
    if (_dropdownsLoaded) return;
    try {
      const res  = await fetch('/api/price_commodities');
      const data = await res.json();
      if (data.commodities && commoditySel) {
        data.commodities.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c;
          commoditySel.appendChild(opt);
        });
      }
      if (data.districts && districtSel) {
        data.districts.forEach(d => {
          const opt = document.createElement('option');
          opt.value = d;
          opt.textContent = d;
          districtSel.appendChild(opt);
        });
      }
      _dropdownsLoaded = true;
    } catch (e) {
      console.warn('Could not load price commodities:', e);
    }
  }

  // ── Fetch Prices ─────────────────────────────────────────────────────
  async function fetchPrices() {
    const commodity = commoditySel?.value || '';
    if (!commodity) {
      showPriceError('Please select a commodity first.');
      return;
    }
    const district = districtSel?.value || '';
    let url = `/api/price?commodity=${encodeURIComponent(commodity)}`;
    if (district) url += `&district=${encodeURIComponent(district)}`;

    setPriceState('loading');
    try {
      const res  = await fetch(url);
      const data = await res.json();
      if (!res.ok || data.error) {
        showPriceError(data.error || 'Failed to fetch price data.');
        return;
      }
      _priceLastData = data;
      renderPriceCards(data);
    } catch (e) {
      showPriceError('Network error. Is the server running?');
    }
  }

  function setPriceState(state) {
    emptyEl.hidden    = (state !== 'empty');
    errorEl.hidden    = (state !== 'error');
    loadingEl.hidden  = (state !== 'loading');
    resultArea.hidden = (state !== 'result');
    if (state === 'empty') emptyEl.hidden = false;
  }
  function showPriceError(msg) {
    setPriceState('error');
    if (errorEl) { errorEl.hidden = false; errorEl.textContent = '❌ ' + msg; }
  }

  function renderPriceCards(data) {
    setPriceState('result');
    if (dateBadge) dateBadge.textContent = `Prices as of ${data.arrival_date || 'latest'}`;
    if (cardsGrid) {
      cardsGrid.innerHTML = '';
      (data.records || []).forEach((r, i) => {
        const card = document.createElement('div');
        card.className = 'price-card';
        card.style.animationDelay = `${i * 0.05}s`;
        card.innerHTML = `
          <div class="price-card-market" title="${r.market}">${r.market || '—'}</div>
          <div class="price-card-commodity">${r.commodity}</div>
          <div class="price-card-variety">${[r.variety, r.grade].filter(Boolean).join(' · ')}</div>
          <div class="price-card-prices">
            <div class="price-badge min">
              <span class="price-badge-label">Min</span>
              <span class="price-badge-value">₹${(r.min_price||0).toLocaleString('en-IN')}</span>
              <span class="price-badge-unit">per quintal</span>
            </div>
            <div class="price-badge modal">
              <span class="price-badge-label">Modal</span>
              <span class="price-badge-value">₹${(r.modal_price||0).toLocaleString('en-IN')}</span>
              <span class="price-badge-unit">per quintal</span>
            </div>
            <div class="price-badge max">
              <span class="price-badge-label">Max</span>
              <span class="price-badge-value">₹${(r.max_price||0).toLocaleString('en-IN')}</span>
              <span class="price-badge-unit">per quintal</span>
            </div>
          </div>
        `;
        cardsGrid.appendChild(card);
      });
    }
  }

  fetchBtn?.addEventListener('click', fetchPrices);
  commoditySel?.addEventListener('keydown', e => { if (e.key === 'Enter') fetchPrices(); });

  // ── Add to Chat ──────────────────────────────────────────────────────
  function buildPriceChatText(data) {
    if (!data || !data.records?.length) return '';
    const commodity = data.records[0]?.commodity || 'Commodity';
    const date      = data.arrival_date || 'today';
    let text = `### 📊 Market Prices: **${commodity}** (${date})\n\n`;
    data.records.forEach(r => {
      text += `**${r.market}** — Min: ₹${Number(r.min_price).toLocaleString('en-IN')} · Modal: ₹${Number(r.modal_price).toLocaleString('en-IN')} · Max: ₹${Number(r.max_price).toLocaleString('en-IN')} /quintal\n`;
    });
    text += `\n*Source: Agmarknet data.gov.in · Tamil Nadu*`;
    return text;
  }

  addChatBtn?.addEventListener('click', () => {
    const txt = buildPriceChatText(_priceLastData);
    if (txt) {
      renderMessage(txt, 'bot');
      if (SESSION_ID) {
        const hist = conversation_store_local_append({
          role: 'bot', text: txt
        });
      }
      closePriceModal();
    }
  });

  // ── Expose openPriceModal so chat commands can call it ───────────────
  window._openPriceModal   = openPriceModal;
  window._fetchPriceFor    = async (commodity, district) => {
    await populatePriceDropdowns();
    if (commoditySel) {
      [...commoditySel.options].forEach(opt => {
        if (opt.value.toLowerCase().includes(commodity.toLowerCase())) commoditySel.value = opt.value;
      });
    }
    if (district && districtSel) {
      [...districtSel.options].forEach(opt => {
        if (opt.value.toLowerCase().includes(district.toLowerCase())) districtSel.value = opt.value;
      });
    }
    await fetchPrices();
    return buildPriceChatText(_priceLastData);
  };
}

// Helper: append to local conversation store without server
function conversation_store_local_append(item) {
  // We don't have direct JS access to server conversation_store,
  // but the user can see the result in chat. This is intentional.
}

// ── Chat command shortcut handled inside sendMessage above ───────────

// ════════════════════════════════════════════════════════════════════════
// SOIL ID MODAL
// ════════════════════════════════════════════════════════════════════════
function initSoilModal() {
  const overlay       = document.getElementById('soilModalOverlay');
  const openBtn       = document.getElementById('openSoilModal');
  const closeBtn      = document.getElementById('closeSoilModal');
  const dropZone      = document.getElementById('soilDropZone');
  const fileInput     = document.getElementById('soilModalFileInput');
  const uploadInner   = document.getElementById('soilUploadInner');
  const previewWrap   = document.getElementById('soilModalPreviewWrap');
  const previewImg    = document.getElementById('soilModalPreviewImg');
  const removeBtn     = document.getElementById('soilModalRemoveBtn');
  const classifyBtn   = document.getElementById('soilClassifyBtn');
  const resultArea    = document.getElementById('soilModalResultArea');
  const loadingEl     = document.getElementById('soilModalLoading');

  // openBtn is optional (no longer in topbar; opened via chat-menu tool cards)
  if (!overlay) return;

  let _soilFile = null;

  function openSoilModal() {
    overlay.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeSoilModal() {
    overlay.hidden = true;
    document.body.style.overflow = '';
  }
  openBtn?.addEventListener('click', openSoilModal);
  closeBtn?.addEventListener('click', closeSoilModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeSoilModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !overlay.hidden) closeSoilModal(); });
  document.querySelectorAll('.trigger-soil-modal').forEach(btn => {
    btn.addEventListener('click', openSoilModal);
  });

  // Expose for chat-menu
  window._openSoilModal = openSoilModal;

  // ── File Selection ───────────────────────────────────────────────────
  function setSoilFile(file) {
    if (!file) return;
    _soilFile = file;
    if (previewImg && previewWrap && uploadInner && classifyBtn) {
      const url = URL.createObjectURL(file);
      previewImg.src = url;
      previewWrap.hidden = false;
      uploadInner.style.display = 'none';
      classifyBtn.disabled = false;
    }
    if (resultArea) { resultArea.hidden = true; resultArea.innerHTML = ''; }
    if (loadingEl) loadingEl.hidden = true;
  }

  function clearSoilFile() {
    _soilFile = null;
    if (fileInput) fileInput.value = '';
    if (previewImg) previewImg.src = '';
    if (previewWrap) previewWrap.hidden = true;
    if (uploadInner) uploadInner.style.display = '';
    if (classifyBtn) classifyBtn.disabled = true;
    if (resultArea) { resultArea.hidden = true; resultArea.innerHTML = ''; }
    if (loadingEl) loadingEl.hidden = true;
  }

  fileInput?.addEventListener('change', () => { if (fileInput.files[0]) setSoilFile(fileInput.files[0]); });
  removeBtn?.addEventListener('click', clearSoilFile);

  // ── Drag & Drop ──────────────────────────────────────────────────────
  dropZone?.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone?.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) setSoilFile(file);
  });

  // ── Classify ─────────────────────────────────────────────────────────
  async function classifySoil() {
    if (!_soilFile) return;
    if (loadingEl) loadingEl.hidden = false;
    if (resultArea) { resultArea.hidden = true; resultArea.innerHTML = ''; }
    if (classifyBtn) classifyBtn.disabled = true;

    const form = new FormData();
    form.append('image', _soilFile);
    form.append('session_id', SESSION_ID || '');
    form.append('language', APP_LANGUAGE);
    if (activeContext.district) form.append('district', activeContext.district);

    try {
      const res  = await fetch('/soil', { method: 'POST', body: form });
      const data = await res.json();
      if (data.session_id) { SESSION_ID = data.session_id; localStorage.setItem('sf_session', SESSION_ID); }
      if (data.memory)     updateContextUI(data.memory);

      if (loadingEl) loadingEl.hidden = true;
      if (classifyBtn) classifyBtn.disabled = false;

      if (data.error) {
        if (resultArea) {
          resultArea.innerHTML = `<div class="price-error">❌ ${data.error}${data.detail ? '<br><small>' + data.detail + '</small>' : ''}</div>`;
          resultArea.hidden = false;
        }
        return;
      }

      renderSoilResult(data);
    } catch (e) {
      if (loadingEl) loadingEl.hidden = true;
      if (classifyBtn) classifyBtn.disabled = false;
      if (resultArea) {
        resultArea.innerHTML = `<div class="price-error">❌ Network error: ${e.message}</div>`;
        resultArea.hidden = false;
      }
    }
  }

  function renderSoilResult(data) {
    if (!resultArea) return;
    const soilType = data.soil_type || 'Unknown';
    const fullText = data.text || '';
    // Extract characteristics line from text (between ** ... ** pairs)
    const charMatch = fullText.match(/\*\*Characteristics:\*\* (.+?)(?:\n|$)/);
    const charText  = charMatch ? charMatch[1] : '';
    const cropMatch = fullText.match(/\*\*Best matching crops[^:]*:\*\* (.+?)(?:\n|$)/);
    const cropText  = cropMatch ? cropMatch[1] : '';

    resultArea.innerHTML = `
      <div class="soil-result-type">🌱 ${soilType}</div>
      ${charText ? `<div class="soil-result-char">${charText}</div>` : ''}
      ${cropText ? `<div class="soil-result-crops"><strong>Best crops:</strong> ${cropText}</div>` : ''}
      <button class="soil-add-chat-btn" id="soilAddChatBtnResult" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Add to Chat
      </button>
    `;
    resultArea.hidden = false;

    document.getElementById('soilAddChatBtnResult')?.addEventListener('click', () => {
      renderMessage(fullText, 'bot');
      closeSoilModal();
    });
  }

  classifyBtn?.addEventListener('click', classifySoil);
}
