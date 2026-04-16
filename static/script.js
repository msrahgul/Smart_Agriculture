
let SESSION_ID = localStorage.getItem('sf_session') || null;
let activeContext = { district: null, soil: null, season: null, month: null, crop: null };
let isProcessing = false;

const messagesList = document.getElementById('messagesList');
const messagesWrap = document.getElementById('messagesWrap');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const voiceInputBtn = document.getElementById('voiceInputBtn');
const voiceStatus = document.getElementById('voiceStatus');
const languageToggle = document.getElementById('languageToggle');
const clearChatBtn = document.getElementById('clearChat');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.querySelector('.sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const soilImageInput = document.getElementById('soilImageInput');
const soilStrip = document.getElementById('soilPreviewStrip');
const soilPreviewImg = document.getElementById('soilPreviewImg');
const soilPreviewName = document.getElementById('soilPreviewName');
const removeImgBtn = document.getElementById('removeImgBtn');
const ttsBtnGlobal = document.getElementById('ttsBtnGlobal');
const ctxCrop = document.getElementById('ctxCrop');
const ctxDistrict = document.getElementById('ctxDistrict');
const ctxSoil = document.getElementById('ctxSoil');
const ctxMonth = document.getElementById('ctxMonth');
const ctxSeason = document.getElementById('ctxSeason');
const topCtxCrop = document.getElementById('topCtxCrop');
const topCtxDistrict = document.getElementById('topCtxDistrict');
const weatherEmpty = document.getElementById('weatherEmpty');
const weatherContent = document.getElementById('weatherContent');
const weatherDistrict = document.getElementById('weatherDistrict');
const weatherTemp = document.getElementById('weatherTemp');
const weatherCondition = document.getElementById('weatherCondition');
const weatherHumidity = document.getElementById('weatherHumidity');
const weatherRain = document.getElementById('weatherRain');
const weatherWind = document.getElementById('weatherWind');
const weatherHourly = document.getElementById('weatherHourly');
const weatherDaily = document.getElementById('weatherDaily');
const weatherSource = document.querySelector('.weather-source');
const whatifIrrSlider = document.getElementById('whatifIrrSlider');
const whatifRainSlider = document.getElementById('whatifRainSlider');
const whatifIrrVal = document.getElementById('whatifIrrVal');
const whatifRainVal = document.getElementById('whatifRainVal');
const whatifFertSlider = document.getElementById('whatifFertSlider');
const whatifTempSlider = document.getElementById('whatifTempSlider');
const whatifPestSlider = document.getElementById('whatifPestSlider');
const whatifMoistureSlider = document.getElementById('whatifMoistureSlider');
const whatifFertVal = document.getElementById('whatifFertVal');
const whatifTempVal = document.getElementById('whatifTempVal');
const whatifPestVal = document.getElementById('whatifPestVal');
const whatifMoistureVal = document.getElementById('whatifMoistureVal');
const simulateBtn = document.getElementById('simulateBtn');
const manualCrop = document.getElementById('manualCrop');
const manualDistrict = document.getElementById('manualDistrict');
const manualSoil = document.getElementById('manualSoil');
const manualMonth = document.getElementById('manualMonth');
const manualSeason = document.getElementById('manualSeason');
const applyContextBtn = document.getElementById('applyContextBtn');
const resetContextBtn = document.getElementById('resetContextBtn');
const inputCard = document.querySelector('.input-card');
const chatMenuBtn = document.getElementById('chatMenuBtn');
const chatMenuPanel = document.getElementById('chatMenuPanel');
let lastWeatherDistrict = null;
let weatherRequestId = 0;
let latestWeatherData = null;

function setChatMenuOpen(open) {
  if (!chatMenuBtn || !chatMenuPanel) return;
  chatMenuPanel.hidden = !open;
  chatMenuBtn.classList.toggle('menu-open', Boolean(open));
  chatMenuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

let APP_LANGUAGE = localStorage.getItem('sf_language') || 'en';
if (!['en', 'ta'].includes(APP_LANGUAGE)) APP_LANGUAGE = APP_LANGUAGE.startsWith('ta') ? 'ta' : 'en';

const INTRO_MESSAGE = `🤖 I'm your Smart Farming AI for Tamil Nadu, and I'm here to help with agriculture questions.\n\nTry one of these examples:`;
const INTRO_MESSAGE_TA = `🤖 நான் தமிழ்நாட்டிற்கான Smart Farming AI. வேளாண்மை கேள்விகளுக்கு உதவ தயாராக இருக்கிறேன்.\n\nஇந்த மாதிரி கேள்விகளை முயற்சி செய்யலாம்:`;

const WELCOME_QUERIES = [
  'Best crops for Madurai with red soil during Kharif?',
  'How much rainfall does Coimbatore receive?',
  'Pest risks in Dharmapuri?',
  'Overview of Erode district?'
];

const WELCOME_QUERIES_TA = [
  'மதுரையில் சிவப்பு மண்ணில் காரிஃப் பருவத்திற்கு சிறந்த பயிர்கள்?',
  'கோயம்புத்தூர் மழை அளவு என்ன?',
  'தர்மபுரியில் பூச்சி அபாயம் என்ன?',
  'ஈரோடு மாவட்ட விவரம் சொல்லுங்கள்'
];

let ttsEnabled = false;
let currentUtterance = null;
let speechQueue = [];
let preferredVoice = null;
let currentSpeechLang = 'en-IN';
let speechWatchdog = null;
let speechKeepAlive = null;
let speechRunId = 0;
let recognition = null;
let isListening = false;
let stopVoiceRequested = false;
let voiceTranscript = '';
let voiceAutoStopTimer = null;
let recognitionLangInUse = null;
let recognitionFallbackTimer = null;
let recognitionStartTimer = null;

function prettyContextValue(value) {
  if (!value) return '—';
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

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
  if (s === 'autumn') return 'October';
  if (s === 'whole year') return 'April';
  return '';
}

function isMonthInSeason(month, season) {
  if (!month || !season) return true;
  if (season === 'Whole Year') return true;
  return monthToSeason(month) === season;
}

function syncSeasonFromMonth() {
  if (!manualMonth || !manualSeason) return;
  const nextSeason = monthToSeason(manualMonth.value);
  if (nextSeason) manualSeason.value = nextSeason;
}

function syncMonthFromSeason() {
  if (!manualMonth || !manualSeason) return;
  const season = manualSeason.value;
  if (!season) return;
  if (!manualMonth.value || !isMonthInSeason(manualMonth.value, season)) {
    manualMonth.value = seasonToDefaultMonth(season);
  }
}

function syncManualContextInputs() {
  if (manualCrop) manualCrop.value = activeContext.crop || '';
  if (manualDistrict) manualDistrict.value = activeContext.district || '';
  if (manualSoil) manualSoil.value = activeContext.soil || '';
  if (manualMonth) manualMonth.value = activeContext.month || '';
  if (manualSeason) manualSeason.value = activeContext.season || '';
}

function updateContextUI(memory = {}) {
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  const previousDistrict = activeContext.district;
  activeContext = { ...activeContext, ...memory };
  if (ctxCrop) ctxCrop.textContent = prettyContextValue(activeContext.crop);
  if (ctxDistrict) ctxDistrict.textContent = prettyContextValue(activeContext.district);
  if (ctxSoil) ctxSoil.textContent = prettyContextValue(activeContext.soil);
  if (ctxMonth) ctxMonth.textContent = prettyContextValue(activeContext.month);
  if (ctxSeason) ctxSeason.textContent = prettyContextValue(activeContext.season);
  if (topCtxCrop) topCtxCrop.textContent = `${t.cropLabel}: ${prettyContextValue(activeContext.crop)}`;
  if (topCtxDistrict) topCtxDistrict.textContent = `${t.locationLabel}: ${prettyContextValue(activeContext.district)}`;
  syncManualContextInputs();
  updateWhatIfLabels();
  if (activeContext.district && activeContext.district !== previousDistrict) {
    loadWeatherForDistrict(activeContext.district);
  } else if (!activeContext.district) {
    resetWeatherUI();
  }
}

function formatWeatherNumber(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  if (Number.isNaN(number)) return '—';
  return `${Math.round(number)}${suffix}`;
}

function formatWeatherTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(11, 16) || value;
  return date.toLocaleTimeString('en-IN', { hour: 'numeric', hour12: true });
}

function formatWeatherDate(value) {
  if (!value) return '—';
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(APP_LANGUAGE === 'ta' ? 'ta-IN' : 'en-IN', { weekday: 'short' });
}

function localizeWeatherCondition(text) {
  if (APP_LANGUAGE !== 'ta') return text || 'Weather update';
  const value = String(text || '').toLowerCase();
  if (value.includes('rain')) return 'மழை வாய்ப்பு';
  if (value.includes('clear')) return 'தெளிந்த வானம்';
  if (value.includes('cloud')) return 'மேகமூட்டம்';
  if (value.includes('fog')) return 'மூடுபனி';
  if (value.includes('thunder')) return 'இடி மின்னல் வாய்ப்பு';
  if (value.includes('offline')) return 'பருவகால வானிலை மதிப்பீடு';
  return 'வானிலை புதுப்பிப்பு';
}

function resetWeatherUI(message = null) {
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  lastWeatherDistrict = null;
  latestWeatherData = null;
  if (weatherEmpty) {
    weatherEmpty.hidden = false;
    weatherEmpty.textContent = message || t.weatherEmpty;
  }
  if (weatherContent) weatherContent.hidden = true;
}

function renderWeather(data) {
  if (!weatherContent) return;
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  latestWeatherData = data;
  const current = data.current || {};
  if (weatherEmpty) weatherEmpty.hidden = true;
  weatherContent.hidden = false;
  if (weatherDistrict) weatherDistrict.textContent = data.district || 'Weather';
  if (weatherSource) weatherSource.textContent = data.source || 'Open-Meteo';
  if (weatherTemp) weatherTemp.textContent = formatWeatherNumber(current.temp_c, '°C');
  if (weatherCondition) weatherCondition.textContent = localizeWeatherCondition(current.condition);
  if (weatherHumidity) weatherHumidity.textContent = `${t.humidityLabel} ${formatWeatherNumber(current.humidity_pct, '%')}`;
  if (weatherRain) weatherRain.textContent = `${t.rainLabel} ${formatWeatherNumber(current.rain_mm ?? current.precipitation_mm, ' mm')}`;
  if (weatherWind) weatherWind.textContent = `${t.windLabel} ${formatWeatherNumber(current.wind_kmh, ' km/h')}`;
  if (weatherHourly) {
    weatherHourly.innerHTML = '';
    (data.hourly || []).slice(0, 4).forEach(item => {
      const row = document.createElement('div');
      row.className = 'weather-mini-row';
      row.innerHTML = `<span>${formatWeatherTime(item.time)}</span><strong>${formatWeatherNumber(item.temp_c, '°')}</strong><em>${formatWeatherNumber(item.rain_probability_pct, '% rain')}</em>`;
      weatherHourly.appendChild(row);
    });
  }
  if (weatherDaily) {
    weatherDaily.innerHTML = '';
    (data.daily || []).slice(0, 3).forEach(item => {
      const row = document.createElement('div');
      row.className = 'weather-mini-row';
      row.innerHTML = `<span>${formatWeatherDate(item.date)}</span><strong>${formatWeatherNumber(item.temp_min_c, '°')} / ${formatWeatherNumber(item.temp_max_c, '°')}</strong><em>${formatWeatherNumber(item.rain_sum_mm, ' mm')}</em>`;
      weatherDaily.appendChild(row);
    });
  }
}

async function loadWeatherForDistrict(district) {
  if (!district || district === lastWeatherDistrict) return;
  lastWeatherDistrict = district;
  const requestId = ++weatherRequestId;
  if (weatherEmpty) {
    weatherEmpty.hidden = false;
    weatherEmpty.textContent = APP_LANGUAGE === 'ta' ? `${prettyContextValue(district)} வானிலை ஏற்றப்படுகிறது...` : `Loading weather for ${prettyContextValue(district)}...`;
  }
  if (weatherContent) weatherContent.hidden = true;
  try {
    const res = await fetch(`/weather?district=${encodeURIComponent(district)}`);
    const data = await res.json();
    if (requestId !== weatherRequestId) return;
    if (!res.ok || data.error) {
      resetWeatherUI(data.error || 'Weather is unavailable right now.');
      return;
    }
    renderWeather(data);
  } catch (_) {
    if (requestId === weatherRequestId) resetWeatherUI('Weather is unavailable right now.');
  }
}

function clearContextUI() {
  activeContext = { district: null, soil: null, season: null, month: null, crop: null };
  updateContextUI({});
}

async function persistManualContext(nextContext) {
  try {
    const res = await fetch('/set_context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID, memory: nextContext })
    });
    const data = await res.json();
    if (data.session_id) {
      SESSION_ID = data.session_id;
      localStorage.setItem('sf_session', SESSION_ID);
    }
  } catch (_) {}
}

async function applyManualContext() {
  const nextContext = {
    crop: manualCrop.value.trim() || null,
    district: manualDistrict.value.trim() || null,
    soil: manualSoil.value || null,
    month: manualMonth.value || null,
    season: manualSeason.value || null,
  };
  if (nextContext.month && !nextContext.season) nextContext.season = monthToSeason(nextContext.month);
  if (nextContext.season && (!nextContext.month || !isMonthInSeason(nextContext.month, nextContext.season))) {
    nextContext.month = seasonToDefaultMonth(nextContext.season) || nextContext.month;
  }
  updateContextUI(nextContext);
  await persistManualContext(nextContext);
  renderMessage((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).manualUpdated, 'bot');
}

async function resetManualContext() {
  clearContextUI();
  await persistManualContext(activeContext);
}

function extractFollowupChips(text) {
  const match = text.match(/FOLLOWUP_CHIPS:([^\n]+)/);
  return match ? match[1].replace(/\*\*$/, '').split('|').map(x => x.trim().replace(/\*\*$/, '')).filter(Boolean) : [];
}

function removeFollowupMarker(text) {
  return text.replace(/---\s*\*\*FOLLOWUP_CHIPS:[^\n]+\*\*/g, '').replace(/FOLLOWUP_CHIPS:[^\n]+/g, '').trim();
}

function parseMarkdown(text) {
  text = text.replace(/\n(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g, parseTable);
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  for (let line of lines) {
    if (/^### (.+)/.test(line)) { if (inList) { html += '</ul>'; inList = false; } html += `<h3>${line.replace(/^### /, '')}</h3>`; }
    else if (/^## (.+)/.test(line)) { if (inList) { html += '</ul>'; inList = false; } html += `<h2>${line.replace(/^## /, '')}</h2>`; }
    else if (/^# (.+)/.test(line)) { if (inList) { html += '</ul>'; inList = false; } html += `<h1>${line.replace(/^# /, '')}</h1>`; }
    else if (/^[*-] (.+)/.test(line)) { if (!inList) { html += '<ul>'; inList = true; } html += `<li>${inlineFormat(line.replace(/^[*-] /, ''))}</li>`; }
    else if (line.trim().startsWith('<table')) { if (inList) { html += '</ul>'; inList = false; } html += line; }
    else if (line.trim() === '') { if (inList) { html += '</ul>'; inList = false; } html += '<br>'; }
    else { if (inList) { html += '</ul>'; inList = false; } html += `<p>${inlineFormat(line)}</p>`; }
  }
  if (inList) html += '</ul>';
  return html;
}

function inlineFormat(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/`([^`]+)`/g, '<code>$1</code>');
}

function stripTableVisuals(text) {
  return String(text || '')
    .replace(/^[\s\u2600-\u27BF\u{1F300}-\u{1FAFF}\uFE0F]+/u, '')
    .trim();
}

function parseTable(match, header, sep, body) {
  const headers = header.trim().split('|').map(c => stripTableVisuals(c)).filter(Boolean);
  const rows = body.trim().split('\n').filter(r => r.includes('|'));
  let html = '<table><thead><tr>';
  headers.forEach(c => html += `<th>${inlineFormat(c)}</th>`);
  html += '</tr></thead><tbody>';
  rows.forEach(row => {
    const cells = row.trim().split('|').map(c => stripTableVisuals(c)).filter(Boolean);
    html += '<tr>';
    cells.forEach(c => html += `<td>${inlineFormat(c)}</td>`);
    html += '</tr>';
  });
  html += '</tbody></table>';
  return '\n' + html + '\n';
}

function stripMarkdown(text) {
  return String(text || '')
    .replace(/---\s*\*\*FOLLOWUP_CHIPS:[\s\S]*$/g, '')
    .replace(/FOLLOWUP_CHIPS:[^\n]+/g, '')
    .replace(/\|[-| :]+\|/g, ' ')
    .replace(/^\s*\|.*\|\s*$/gm, ' ')
    .replace(/#{1,3}\s*/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/`/g, '')
    .replace(/[₹]/g, ' rupees ')
    .replace(/[–—]/g, ' to ')
    .replace(/[^\S\r\n]+/g, ' ')
    .replace(/\n+/g, '. ')
    .replace(/\s+/g, ' ')
    .trim();
}

function cleanSpeechText(text) {
  return stripMarkdown(removeFollowupMarker(text))
    .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF\uFE0F]/gu, '')
    .replace(/\bRs\.?\s*/gi, 'rupees ')
    .replace(/\bkg\b/gi, 'kilograms')
    .replace(/\b(t\/ha)\b/gi, ' tonnes per hectare')
    .replace(/\bNPK\b/g, 'N P K')
    .replace(/\bmm\b/g, ' millimetres')
    .replace(/\bkm\/h\b/gi, 'kilometres per hour')
    .replace(/%/g, ' percent')
    .replace(/[₹]/g, ' rupees ')
    .replace(/[–—]/g, ' to ')
    .replace(/:/g, '. ')
    .replace(/;/g, '. ')
    .replace(/\bha\b/g, ' hectares')
    .replace(/\s+([,.])/g, '$1')
    .replace(/\.{2,}/g, '.')
    .replace(/\s+/g, ' ')
    .trim();
}

function hasTamilText(text) {
  return /[\u0B80-\u0BFF]/.test(text || '');
}

function getAvailableVoices() {
  return window.speechSynthesis ? speechSynthesis.getVoices() : [];
}

function findTamilVoice(voices = getAvailableVoices()) {
  return voices.find(v => /ta-IN/i.test(v.lang)) ||
    voices.find(v => /^ta/i.test(v.lang)) ||
    voices.find(v => /Tamil/i.test(v.name)) ||
    null;
}

function waitForVoices(timeoutMs = 2800) {
  if (!window.speechSynthesis) return Promise.resolve([]);
  const existing = speechSynthesis.getVoices();
  if (existing.length) return Promise.resolve(existing);
  return new Promise(resolve => {
    const timer = setTimeout(() => resolve(speechSynthesis.getVoices()), timeoutMs);
    speechSynthesis.onvoiceschanged = () => {
      clearTimeout(timer);
      resolve(speechSynthesis.getVoices());
    };
  });
}

function loadPreferredVoice(lang = 'en-IN') {
  if (!window.speechSynthesis) return null;
  const voices = getAvailableVoices();
  if (/ta-IN/i.test(lang)) {
    preferredVoice = findTamilVoice(voices);
    return preferredVoice;
  }
  const naturalVoiceHints = /(natural|neural|online|aria|jenny|guy|sonia|libby|ravi|heera|google|microsoft)/i;
  preferredVoice =
    voices.find(v => /en-IN/i.test(v.lang) && naturalVoiceHints.test(v.name)) ||
    voices.find(v => /en-IN/i.test(v.lang)) ||
    voices.find(v => /India/i.test(v.name) && naturalVoiceHints.test(v.name)) ||
    voices.find(v => /^en-(GB|US|AU)/i.test(v.lang) && naturalVoiceHints.test(v.name)) ||
    voices.find(v => /^en-/i.test(v.lang) && naturalVoiceHints.test(v.name)) ||
    voices.find(v => /^en-/i.test(v.lang)) ||
    voices[0] ||
    null;
  return preferredVoice;
}

function splitSpeechText(text, maxLen = 260) {
  const sentences = text.match(/[^.!?।]+[.!?।]*/g) || [text];
  const chunks = [];
  let current = '';
  sentences.forEach(sentence => {
    const trimmed = sentence.trim();
    if (trimmed.length > maxLen) {
      if (current) {
        chunks.push(current);
        current = '';
      }
      const parts = trimmed.match(new RegExp(`.{1,${maxLen}}(\\s|$)`, 'g')) || [trimmed];
      for (const part of parts) {
        if (part.trim()) chunks.push(part.trim());
      }
      return;
    }
    const next = `${current} ${trimmed}`.trim();
    if (next.length > maxLen && current) {
      chunks.push(current);
      current = trimmed;
    } else {
      current = next;
    }
  });
  if (current) chunks.push(current);
  return chunks;
}

function speakNextChunk() {
  clearTimeout(speechWatchdog);
  clearInterval(speechKeepAlive);
  if (!window.speechSynthesis || !speechQueue.length) {
    currentUtterance = null;
    return;
  }
  const runId = speechRunId;
  const chunk = speechQueue.shift();
  currentUtterance = new SpeechSynthesisUtterance(chunk);
  currentUtterance.lang = currentSpeechLang;
  currentUtterance.voice = preferredVoice || null;
  currentUtterance.rate = currentSpeechLang === 'ta-IN' ? 0.86 : 0.9;
  currentUtterance.pitch = currentSpeechLang === 'ta-IN' ? 1.0 : 0.98;
  currentUtterance.volume = 1;
  currentUtterance.onend = () => {
    if (runId !== speechRunId) return;
    clearInterval(speechKeepAlive);
    currentUtterance = null;
    setTimeout(() => {
      if (runId === speechRunId) speakNextChunk();
    }, currentSpeechLang === 'ta-IN' ? 90 : 70);
  };
  currentUtterance.onerror = () => {
    if (runId !== speechRunId) return;
    clearTimeout(speechWatchdog);
    clearInterval(speechKeepAlive);
    currentUtterance = null;
    speakNextChunk();
  };
  speechSynthesis.speak(currentUtterance);
  speechKeepAlive = setInterval(() => {
    if (runId !== speechRunId || !currentUtterance) {
      clearInterval(speechKeepAlive);
      return;
    }
    if (speechSynthesis.paused) speechSynthesis.resume();
  }, 6000);
}

function getTime() { return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }); }
async function speakText(text) {
  if (!window.speechSynthesis) return;
  const cleaned = cleanSpeechText(text);
  if (!cleaned) return;
  stopSpeaking();
  speechRunId += 1;
  currentSpeechLang = APP_LANGUAGE === 'ta' ? 'ta-IN' : (hasTamilText(cleaned) ? 'ta-IN' : 'en-IN');
  await waitForVoices();
  loadPreferredVoice(currentSpeechLang);
  if (currentSpeechLang === 'ta-IN' && !preferredVoice) {
    setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).tamilVoiceMissing, true);
    return;
  }
  speechQueue = splitSpeechText(cleaned);
  speakNextChunk();
}
function stopSpeaking() {
  speechRunId += 1;
  speechQueue = [];
  clearTimeout(speechWatchdog);
  clearInterval(speechKeepAlive);
  if (window.speechSynthesis) speechSynthesis.cancel();
  currentUtterance = null;
}
function updateTTSButton() {
  if (!ttsBtnGlobal) return;
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  if (!ttsBtnGlobal.querySelector('.tts-label')) {
    const label = document.createElement('span');
    label.className = 'tts-label';
    ttsBtnGlobal.appendChild(label);
  }
  ttsBtnGlobal.classList.toggle('tts-active', ttsEnabled);
  ttsBtnGlobal.title = ttsEnabled ? t.disableTTS : t.enableTTS;
  ttsBtnGlobal.querySelector('.tts-icon').textContent = ttsEnabled ? t.soundOnLabel : t.audioLabel;
  ttsBtnGlobal.querySelector('.tts-label').textContent = ttsEnabled ? t.ttsOn : t.ttsOff;
}
function toggleGlobalTTS() { ttsEnabled = !ttsEnabled; updateTTSButton(); if (!ttsEnabled) stopSpeaking(); }

function languageCode() {
  return APP_LANGUAGE === 'ta' ? 'ta-IN' : 'en-IN';
}

const UI_TEXT = {
  en: {
    documentTitle: 'Smart Farming AI - Tamil Nadu Agricultural Assistant',
    logoTitle: 'SmartFarm AI',
    logoSub: 'Tamil Nadu Agricultural Intelligence',
    topbarTitle: 'Smart Farming AI',
    topbarSub: 'Professional agricultural assistant for Tamil Nadu farming insights',
    soilLabel: 'Soil Identification',
    soilHelp: 'Upload a soil photo to identify soil type and use it in follow-up queries.',
    uploadSoil: '📎 Upload Soil Image',
    manualLabel: 'Manual Context',
    cropLabel: 'Crop',
    locationLabel: 'Location',
    soilFieldLabel: 'Soil',
    monthLabel: 'Month',
    seasonLabel: 'Season',
    applyContext: 'Apply Context',
    resetContext: 'Reset',
    activeLabel: 'Active Context',
    contextHelp: 'Current stored values used for follow-up questions.',
    whatifLabel: 'What-If Simulator',
    scenarioTitle: '🔬 Scenario Simulator',
    irrigationChange: '💧 Irrigation Change',
    rainfallChange: '🌧️ Rainfall Change',
    simulate: '▶ Run Simulation',
    simulateFor: district => `▶ Simulate for ${district}`,
    selectSoil: 'Select soil',
    alluvialSoil: 'Alluvial soil',
    blackSoil: 'Black soil',
    claySoil: 'Clay soil',
    redSoil: 'Red soil',
    selectMonth: 'Select month',
    selectSeason: 'Select season',
    winter: 'Winter',
    summer: 'Summer',
    kharifRainy: 'Kharif / Rainy',
    rabi: 'Rabi',
    autumn: 'Autumn',
    wholeYear: 'Whole Year / Perennial',
    months: ['January', 'February', 'December', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November'],
    enableTTS: 'Enable auto voice replies',
    disableTTS: 'Disable auto voice replies',
    clearTitle: 'Clear conversation',
    micTitle: 'Speak your question',
    micStopTitle: 'Stop listening',
    sendTitle: 'Send message',
    sidebarTitle: 'Toggle sidebar',
    removeImageTitle: 'Remove image',
    listening: 'Listening... speak your farming question.',
    voiceUnsupported: 'Voice input is not supported in this browser.',
    heard: text => `Heard: ${text}`,
    micPermission: 'Microphone permission was blocked. Please allow microphone access.',
    voiceTryAgain: 'Voice input stopped. Please try again.',
    voiceStarting: 'Starting microphone...',
    voiceSending: 'Sending voice question...',
    noSpeech: 'No speech detected. Tap the mic and try again.',
    voiceStopped: 'Voice input stopped.',
    tamilVoiceMissing: 'Tamil voice is not available in this browser/OS. Please install or enable a Tamil voice; English fallback is blocked.',
    manualUpdated: '✅ Manual context updated.',
    noDistrictSimulation: '⚠️ Please set a district in Manual Context or ask a district-specific question first, then run the simulation again.',
    inputFooter: 'Tamil Nadu Smart Farming • Context-aware follow-up support',
    cropPlaceholder: 'e.g. Rice',
    districtPlaceholder: 'e.g. Madurai',
    chatPlaceholder: 'Ask about crops, rainfall, fertilizer, irrigation, pest risks...',
  },
  ta: {
    documentTitle: 'ஸ்மார்ட் வேளாண்மை AI - தமிழ்நாடு வேளாண்மை உதவியாளர்',
    logoTitle: 'SmartFarm AI',
    logoSub: 'தமிழ்நாடு வேளாண்மை நுண்ணறிவு',
    topbarTitle: 'ஸ்மார்ட் வேளாண்மை AI',
    topbarSub: 'தமிழ்நாடு வேளாண்மை தகவல்களுக்கான உதவியாளர்',
    soilLabel: 'மண் அடையாளம்',
    soilHelp: 'மண் வகையை அறிய புகைப்படத்தை பதிவேற்றவும்.',
    uploadSoil: '📎 மண் படத்தை பதிவேற்று',
    manualLabel: 'கையேடு சூழல்',
    cropLabel: 'பயிர்',
    locationLabel: 'மாவட்டம்',
    soilFieldLabel: 'மண்',
    monthLabel: 'மாதம்',
    seasonLabel: 'பருவம்',
    applyContext: 'சூழலை பயன்படுத்து',
    resetContext: 'மீட்டமை',
    activeLabel: 'செயலில் உள்ள சூழல்',
    contextHelp: 'அடுத்த கேள்விகளுக்கு பயன்படுத்தப்படும் தற்போதைய மதிப்புகள்.',
    whatifLabel: 'என்ன ஆகும்? சோதனை',
    scenarioTitle: '🔬 சூழ்நிலை சோதனை',
    irrigationChange: '💧 பாசன மாற்றம்',
    rainfallChange: '🌧️ மழை மாற்றம்',
    simulate: '▶ சோதனை இயக்கு',
    simulateFor: district => `▶ ${district} க்கு சோதனை`,
    selectSoil: 'மண் தேர்வு',
    alluvialSoil: 'வண்டல் மண்',
    blackSoil: 'கரிசல் மண்',
    claySoil: 'களிமண்',
    redSoil: 'சிவப்பு மண்',
    selectMonth: 'மாதம் தேர்வு',
    selectSeason: 'பருவம் தேர்வு',
    winter: 'குளிர்காலம்',
    summer: 'கோடைகாலம்',
    kharifRainy: 'காரிஃப் / மழைக்காலம்',
    rabi: 'ரபி',
    autumn: 'இலையுதிர் காலம்',
    wholeYear: 'முழு ஆண்டு / நிரந்தர பயிர்',
    months: ['ஜனவரி', 'பிப்ரவரி', 'டிசம்பர்', 'மார்ச்', 'ஏப்ரல்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆகஸ்ட்', 'செப்டம்பர்', 'அக்டோபர்', 'நவம்பர்'],
    enableTTS: 'குரல் பதில்களை இயக்கு',
    disableTTS: 'குரல் பதில்களை நிறுத்து',
    clearTitle: 'உரையாடலை அழி',
    micTitle: 'உங்கள் கேள்வியை பேசுங்கள்',
    micStopTitle: 'கேட்பதை நிறுத்து',
    sendTitle: 'செய்தி அனுப்பு',
    sidebarTitle: 'பக்கப்பட்டியை திற/மூடு',
    removeImageTitle: 'படத்தை அகற்று',
    listening: 'கேட்கிறது... உங்கள் வேளாண்மை கேள்வியை பேசுங்கள்.',
    voiceUnsupported: 'இந்த உலாவியில் குரல் உள்ளீடு ஆதரிக்கப்படவில்லை.',
    heard: text => `கேட்டது: ${text}`,
    micPermission: 'மைக்ரோஃபோன் அனுமதி தடுக்கப்பட்டுள்ளது. மைக்ரோஃபோன் அணுகலை அனுமதிக்கவும்.',
    voiceTryAgain: 'குரல் உள்ளீடு நிறுத்தப்பட்டது. மீண்டும் முயற்சிக்கவும்.',
    voiceStarting: 'குரல் உள்ளீடு தொடங்குகிறது. சிறிது காத்திருக்கவும்.',
    voiceSending: 'குரல் கேள்வி அனுப்பப்படுகிறது...',
    noSpeech: 'பேச்சு கண்டறியப்படவில்லை. மைக் அழுத்தி மீண்டும் முயற்சிக்கவும்.',
    voiceStopped: 'குரல் உள்ளீடு நிறுத்தப்பட்டது.',
    tamilVoiceMissing: 'இந்த உலாவி/சாதனத்தில் தமிழ் குரல் இல்லை. தமிழ் voice ஐ நிறுவவும் அல்லது இயக்கு; English fallback தடுக்கப்பட்டுள்ளது.',
    manualUpdated: '✅ கையேடு சூழல் புதுப்பிக்கப்பட்டது.',
    noDistrictSimulation: '⚠️ முதலில் கையேடு சூழலில் மாவட்டத்தை அமைக்கவும் அல்லது மாவட்டம் சார்ந்த கேள்வி கேட்கவும். பிறகு சோதனையை மீண்டும் இயக்கவும்.',
    inputFooter: 'தமிழ்நாடு ஸ்மார்ட் வேளாண்மை • சூழல் சார்ந்த உதவி',
    cropPlaceholder: 'உ.தா. நெல்',
    districtPlaceholder: 'உ.தா. மதுரை',
    chatPlaceholder: 'பயிர், மழை, உரம், பாசனம், பூச்சி அபாயம் பற்றி கேளுங்கள்...',
  }
};

Object.assign(UI_TEXT.en, {
  logoTitle: 'SmartFarm AI',
  logoSub: 'Tamil Nadu Agricultural Intelligence',
  uploadSoil: 'Upload Soil Image',
  scenarioTitle: 'Scenario Simulator',
  irrigationChange: 'Irrigation Change',
  rainfallChange: 'Rainfall Change',
  fertilizerChange: 'Fertilizer',
  temperatureChange: 'Temperature',
  pestIntensity: 'Pest Intensity',
  soilMoisture: 'Soil Moisture',
  simulate: 'Run Simulation',
  simulateFor: district => `Simulate for ${district}`,
  weatherLabel: 'Weather Updates',
  weatherEmpty: 'Select or ask about a district to load live weather.',
  nextHours: 'Next hours',
  nextDays: 'Next days',
  humidityLabel: 'Humidity',
  rainLabel: 'Rain',
  windLabel: 'Wind',
  toolsLabel: 'Tools',
  soilOption: 'Soil Identification',
  languageButton: 'English',
  audioLabel: 'Audio',
  soundOnLabel: 'Sound on',
  ttsOn: 'On',
  ttsOff: 'Off',
  resetLabel: 'Reset',
  skipLink: 'Skip to chat input',
  inputFooter: 'Tamil Nadu Smart Farming • Context-aware follow-up support',
  manualUpdated: 'Manual context updated.',
  noDistrictSimulation: 'Please set a district first, then run the simulation again.',
});

Object.assign(UI_TEXT.ta, {
  documentTitle: 'ஸ்மார்ட் வேளாண்மை AI - தமிழ்நாடு வேளாண்மை உதவியாளர்',
  logoTitle: 'ஸ்மார்ட் ஃபார்ம் AI',
  logoSub: 'தமிழ்நாடு வேளாண்மை நுண்ணறிவு',
  topbarTitle: 'ஸ்மார்ட் வேளாண்மை AI',
  topbarSub: 'தமிழ்நாடு விவசாய தகவல்களுக்கான தொழில்முறை உதவியாளர்',
  soilLabel: 'மண் அடையாளம்',
  soilHelp: 'மண் வகையை அறிய மண் புகைப்படத்தை பதிவேற்றவும்.',
  uploadSoil: 'மண் படத்தை பதிவேற்றவும்',
  manualLabel: 'கையேடு சூழல்',
  cropLabel: 'பயிர்',
  locationLabel: 'இடம்',
  soilFieldLabel: 'மண்',
  monthLabel: 'மாதம்',
  seasonLabel: 'பருவம்',
  applyContext: 'சூழலை பயன்படுத்து',
  resetContext: 'மீட்டமை',
  activeLabel: 'செயலில் உள்ள சூழல்',
  contextHelp: 'அடுத்த கேள்விகளுக்குப் பயன்படுத்தப்படும் தற்போதைய மதிப்புகள்.',
  whatifLabel: 'என்ன ஆகும்? சோதனை',
  scenarioTitle: 'சூழ்நிலை சோதனை',
  irrigationChange: 'பாசன மாற்றம்',
  rainfallChange: 'மழை மாற்றம்',
  fertilizerChange: 'உரம்',
  temperatureChange: 'வெப்பநிலை',
  pestIntensity: 'பூச்சி தீவிரம்',
  soilMoisture: 'மண் ஈரப்பதம்',
  simulate: 'சோதனையை இயக்கு',
  simulateFor: district => `${district} க்கான சோதனை`,
  weatherLabel: 'வானிலை புதுப்பிப்புகள்',
  weatherEmpty: 'நேரடி வானிலையை காண மாவட்டத்தை தேர்ந்தெடுக்கவும் அல்லது கேள்வியில் குறிப்பிடவும்.',
  nextHours: 'அடுத்த மணிநேரங்கள்',
  nextDays: 'அடுத்த நாட்கள்',
  humidityLabel: 'ஈரப்பதம்',
  rainLabel: 'மழை',
  windLabel: 'காற்று',
  toolsLabel: 'கருவிகள்',
  soilOption: 'மண் அடையாளம்',
  languageButton: 'தமிழ்',
  audioLabel: 'ஒலி',
  soundOnLabel: 'ஒலி இயக்கு',
  ttsOn: 'இயக்கம்',
  ttsOff: 'நிறுத்தம்',
  resetLabel: 'மீட்டமை',
  skipLink: 'உரை உள்ளீட்டுக்கு செல்லவும்',
  selectSoil: 'மண் தேர்வு',
  alluvialSoil: 'வண்டல் மண்',
  blackSoil: 'கரிசல் மண்',
  claySoil: 'களிமண்',
  redSoil: 'சிவப்பு மண்',
  selectMonth: 'மாதம் தேர்வு',
  selectSeason: 'பருவம் தேர்வு',
  winter: 'குளிர்காலம்',
  summer: 'கோடைக்காலம்',
  kharifRainy: 'காரிஃப் / மழைக்காலம்',
  rabi: 'ரபி',
  autumn: 'இலையுதிர் காலம்',
  wholeYear: 'முழு ஆண்டு / நிரந்தர பயிர்',
  months: ['ஜனவரி', 'பிப்ரவரி', 'டிசம்பர்', 'மார்ச்', 'ஏப்ரல்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆகஸ்ட்', 'செப்டம்பர்', 'அக்டோபர்', 'நவம்பர்'],
  enableTTS: 'குரல் பதில்களை இயக்கு',
  disableTTS: 'குரல் பதில்களை நிறுத்து',
  clearTitle: 'உரையாடலை அழிக்கவும்',
  micTitle: 'உங்கள் கேள்வியை பேசுங்கள்',
  micStopTitle: 'கேட்பதை நிறுத்து',
  sendTitle: 'செய்தி அனுப்பு',
  sidebarTitle: 'பக்கப்பட்டியை திற/மூடு',
  removeImageTitle: 'படத்தை அகற்று',
  listening: 'கேட்கிறது... உங்கள் விவசாய கேள்வியை பேசுங்கள்.',
  voiceUnsupported: 'இந்த உலாவியில் குரல் உள்ளீடு ஆதரிக்கப்படவில்லை.',
  heard: text => `கேட்டது: ${text}`,
  micPermission: 'மைக்ரோஃபோன் அனுமதி தடுக்கப்பட்டுள்ளது. மைக்ரோஃபோன் அணுகலை அனுமதிக்கவும்.',
  voiceTryAgain: 'குரல் உள்ளீடு நிறுத்தப்பட்டது. மீண்டும் முயற்சிக்கவும்.',
  voiceStarting: 'மைக்ரோஃபோன் தொடங்குகிறது...',
  voiceSending: 'குரல் கேள்வி அனுப்பப்படுகிறது...',
  noSpeech: 'பேச்சு கண்டறியப்படவில்லை. மைக் அழுத்தி மீண்டும் முயற்சிக்கவும்.',
  voiceStopped: 'குரல் உள்ளீடு நிறுத்தப்பட்டது.',
  tamilVoiceMissing: 'இந்த உலாவி அல்லது சாதனத்தில் தமிழ் குரல் இல்லை. தமிழ் குரலை நிறுவவும் அல்லது இயக்கு.',
  manualUpdated: 'கையேடு சூழல் புதுப்பிக்கப்பட்டது.',
  noDistrictSimulation: 'முதலில் ஒரு மாவட்டத்தை அமைத்து பின்னர் சோதனையை மீண்டும் இயக்கவும்.',
  inputFooter: 'தமிழ்நாடு ஸ்மார்ட் வேளாண்மை • சூழல் சார்ந்த தொடர்ச்சி உதவி',
  cropPlaceholder: 'உ.தா. நெல்',
  districtPlaceholder: 'உ.தா. மதுரை',
  chatPlaceholder: 'பயிர், மழை, உரம், பாசனம், பூச்சி அபாயம் பற்றி கேளுங்கள்...',
});

function setText(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.textContent = value;
}

function setPlaceholder(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.placeholder = value;
}

function setTitle(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.title = value;
}

function setSelectText(select, updates) {
  if (!select) return;
  updates.forEach(({ value, text }, index) => {
    const option = value === undefined ? select.options[index] : Array.from(select.options).find(opt => opt.value === value);
    if (option) textContentPreservingValue(option, text, value);
  });
}

function textContentPreservingValue(option, text, value) {
  if (value !== undefined) option.value = value;
  option.textContent = text;
}

function applyPageLanguage() {
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  document.documentElement.lang = APP_LANGUAGE === 'ta' ? 'ta' : 'en';
  document.title = t.documentTitle;
  setText('.skip-link', t.skipLink);
  setText('.logo-title', t.logoTitle);
  setText('.logo-sub', t.logoSub);
  setText('.topbar-title', UI_TEXT.en.topbarTitle);
  setText('.topbar-sub', UI_TEXT.en.topbarSub);
  setText('.sidebar-section:has(#contextPanel) .sidebar-label', t.activeLabel);
  setText('.weather-section .sidebar-label', t.weatherLabel);
  setText('#whatifPanel .sidebar-label', t.whatifLabel);
  setText('.sidebar-section:has(.tool-card) .sidebar-label', t.soilLabel);
  setText('.tool-help', t.soilHelp);
  setText('.sidebar-upload-btn span', t.uploadSoil);
  setText('#weatherEmpty', t.weatherEmpty);
  const weatherSubtitles = document.querySelectorAll('.weather-subtitle');
  if (weatherSubtitles[0]) weatherSubtitles[0].textContent = t.nextHours;
  if (weatherSubtitles[1]) weatherSubtitles[1].textContent = t.nextDays;
  if (weatherHumidity && weatherHumidity.textContent.includes('-')) weatherHumidity.textContent = `${t.humidityLabel} -`;
  if (weatherRain && weatherRain.textContent.includes('-')) weatherRain.textContent = `${t.rainLabel} -`;
  if (weatherWind && weatherWind.textContent.includes('-')) weatherWind.textContent = `${t.windLabel} -`;
  const labels = document.querySelectorAll('.manual-field label');
  if (labels[0]) labels[0].textContent = t.cropLabel;
  if (labels[1]) labels[1].textContent = t.locationLabel;
  if (labels[2]) labels[2].textContent = t.soilFieldLabel;
  if (labels[3]) labels[3].textContent = t.monthLabel;
  if (labels[4]) labels[4].textContent = t.seasonLabel;
  setText('#applyContextBtn', t.applyContext);
  setText('#resetContextBtn', t.resetContext);
  setText('.context-help', t.contextHelp);
  setText('.topbar-context-label', t.activeLabel);
  const contextKeys = document.querySelectorAll('.context-key');
  if (contextKeys[0]) contextKeys[0].textContent = t.cropLabel;
  if (contextKeys[1]) contextKeys[1].textContent = t.locationLabel;
  if (contextKeys[2]) contextKeys[2].textContent = t.soilFieldLabel;
  if (contextKeys[3]) contextKeys[3].textContent = t.monthLabel;
  if (contextKeys[4]) contextKeys[4].textContent = t.seasonLabel;
  setText('.whatif-panel h4', t.scenarioTitle);
  const whatifSpans = document.querySelectorAll('.whatif-label span');
  if (whatifSpans[0]) whatifSpans[0].textContent = t.irrigationChange;
  if (whatifSpans[1]) whatifSpans[1].textContent = t.rainfallChange;
  if (whatifSpans[2]) whatifSpans[2].textContent = t.fertilizerChange;
  if (whatifSpans[3]) whatifSpans[3].textContent = t.temperatureChange;
  if (whatifSpans[4]) whatifSpans[4].textContent = t.pestIntensity;
  if (whatifSpans[5]) whatifSpans[5].textContent = t.soilMoisture;
  if (manualSoil) {
    setSelectText(manualSoil, [
      { value: '', text: t.selectSoil },
      { value: 'alluvial soil', text: t.alluvialSoil },
      { value: 'black soil', text: t.blackSoil },
      { value: 'clay soil', text: t.claySoil },
      { value: 'red soil', text: t.redSoil },
    ]);
  }
  if (manualMonth) {
    const monthValues = ['January', 'February', 'December', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November'];
    if (manualMonth.options[0]) textContentPreservingValue(manualMonth.options[0], t.selectMonth, '');
    monthValues.forEach((month, index) => {
      const option = Array.from(manualMonth.options).find(opt => opt.value === month || opt.textContent === month || opt.textContent === (UI_TEXT.ta.months[index]));
      if (option) textContentPreservingValue(option, t.months[index], month);
    });
    const monthGroups = manualMonth.querySelectorAll('optgroup');
    if (monthGroups[0]) monthGroups[0].label = t.winter;
    if (monthGroups[1]) monthGroups[1].label = t.summer;
    if (monthGroups[2]) monthGroups[2].label = t.kharifRainy;
    if (monthGroups[3]) monthGroups[3].label = t.rabi;
  }
  if (manualSeason) {
    setSelectText(manualSeason, [
      { value: '', text: t.selectSeason },
      { value: 'Winter', text: t.winter },
      { value: 'Summer', text: t.summer },
      { value: 'Kharif', text: t.kharifRainy },
      { value: 'Rabi', text: t.rabi },
      { value: 'Autumn', text: t.autumn },
      { value: 'Whole Year', text: t.wholeYear },
    ]);
  }
  if (simulateBtn) simulateBtn.textContent = activeContext.district ? t.simulateFor(activeContext.district) : t.simulate;
  if (clearChatBtn) clearChatBtn.textContent = APP_LANGUAGE === 'ta' ? 'Reset' : 'Reset';
  if (clearChatBtn) clearChatBtn.textContent = t.resetLabel;
  setText('#chatMenuBtn', t.toolsLabel);
  setText('.chat-menu-option', t.soilOption);
  setText('.lang-en', 'English');
  setText('.lang-divider', '/');
  setText('.lang-ta', 'தமிழ்');
  setTitle('#clearChat', t.clearTitle);
  setTitle('#voiceInputBtn', isListening ? t.micStopTitle : t.micTitle);
  setTitle('#sendBtn', t.sendTitle);
  setTitle('#sidebarToggle', t.sidebarTitle);
  setTitle('#removeImgBtn', t.removeImageTitle);
  if (voiceInputBtn) voiceInputBtn.setAttribute('aria-label', isListening ? t.micStopTitle : t.micTitle);
  if (sendBtn) sendBtn.setAttribute('aria-label', t.sendTitle);
  if (sidebarToggle) sidebarToggle.setAttribute('aria-label', t.sidebarTitle);
  setPlaceholder('#manualCrop', t.cropPlaceholder);
  setPlaceholder('#manualDistrict', t.districtPlaceholder);
  setPlaceholder('#chatInput', t.chatPlaceholder);
  if (latestWeatherData && weatherContent && !weatherContent.hidden) renderWeather(latestWeatherData);
  setVoiceStatus(t.inputFooter);
  updateTTSButton();
}

function updateLanguageUI() {
  if (!languageToggle) return;
  languageToggle.classList.toggle('tamil-mode', APP_LANGUAGE === 'ta');
  languageToggle.title = APP_LANGUAGE === 'ta' ? 'தமிழ் மொழி இயக்கத்தில் உள்ளது' : 'English mode is active';
  applyPageLanguage();
  if (recognition) recognition.lang = languageCode();
}

function toggleLanguage() {
  APP_LANGUAGE = APP_LANGUAGE === 'ta' ? 'en' : 'ta';
  localStorage.setItem('sf_language', APP_LANGUAGE);
  stopSpeaking();
  updateLanguageUI();
  renderWelcome();
}

function setVoiceStatus(message, isError = false) {
  if (!voiceStatus) return;
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  voiceStatus.textContent = message || t.inputFooter;
  voiceStatus.classList.toggle('voice-error', Boolean(isError));
}

function updateVoiceButton() {
  if (!voiceInputBtn) return;
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  voiceInputBtn.classList.toggle('listening', isListening);
  voiceInputBtn.title = isListening ? t.micStopTitle : t.micTitle;
  voiceInputBtn.setAttribute('aria-label', isListening ? t.micStopTitle : t.micTitle);
}

function createSpeechRecognition(langOverride = null) {
  if (!voiceInputBtn) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
    voiceInputBtn.disabled = true;
    voiceInputBtn.title = t.voiceUnsupported;
    setVoiceStatus(t.voiceUnsupported, true);
    return null;
  }

  const recognizer = new SpeechRecognition();
  recognizer.lang = langOverride || languageCode();
  recognitionLangInUse = recognizer.lang;
  recognizer.interimResults = true;
  recognizer.continuous = false;
  recognizer.maxAlternatives = 1;

  recognizer.onstart = () => {
    const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
    clearTimeout(recognitionStartTimer);
    isListening = true;
    stopVoiceRequested = false;
    voiceTranscript = '';
    clearTimeout(recognitionFallbackTimer);
    if (APP_LANGUAGE === 'ta' && recognitionLangInUse === 'ta-IN') {
      recognitionFallbackTimer = setTimeout(() => {
        if (isListening && !voiceTranscript && !chatInput.value.trim()) {
          try {
            stopVoiceRequested = true;
            recognition.stop();
          } catch (_) {}
          setTimeout(() => {
            try {
              stopVoiceRequested = false;
              startRecognition('en-IN');
              setVoiceStatus('தமிழ் குரல் உள்ளீடு கிடைக்கவில்லை. English recognition மூலம் மீண்டும் கேட்கிறது...');
            } catch (_) {
              setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).voiceTryAgain, true);
            }
          }, 250);
        }
      }, 3500);
    }
    stopSpeaking();
    updateVoiceButton();
    setVoiceStatus(t.listening);
  };

  recognizer.onresult = event => {
    clearTimeout(voiceAutoStopTimer);
    clearTimeout(recognitionFallbackTimer);
    let finalText = voiceTranscript;
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal) finalText = `${finalText} ${transcript}`.trim();
      else interimText = `${interimText} ${transcript}`.trim();
    }
    voiceTranscript = finalText;
    const spokenText = (finalText || interimText).trim();
    if (spokenText) chatInput.value = spokenText;
    chatInput.focus();
    chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
    if (spokenText) {
      setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).heard(spokenText));
    }
  };

  recognizer.onspeechend = () => {
    clearTimeout(voiceAutoStopTimer);
    voiceAutoStopTimer = setTimeout(() => {
      if (recognition && isListening) {
        try { recognition.stop(); } catch (_) {}
      }
    }, 900);
  };

  recognizer.onerror = event => {
    clearTimeout(voiceAutoStopTimer);
    clearTimeout(recognitionFallbackTimer);
    const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
    clearTimeout(recognitionStartTimer);
    const isPermissionError = event.error === 'not-allowed' || event.error === 'service-not-allowed';
    const canRetryInEnglish = APP_LANGUAGE === 'ta' && recognitionLangInUse === 'ta-IN' && !voiceTranscript && !isPermissionError;
    if (canRetryInEnglish) {
      try {
        recognition = createSpeechRecognition('en-IN');
        recognition.start();
        setVoiceStatus('தமிழ் குரல் உள்ளீடு கிடைக்கவில்லை. English recognition மூலம் மீண்டும் கேட்கிறது...');
        return;
      } catch (_) {}
    }
    const msg = isPermissionError ? t.micPermission : t.voiceTryAgain;
    isListening = false;
    stopVoiceRequested = true;
    updateVoiceButton();
    setVoiceStatus(msg, true);
  };

  recognizer.onend = () => {
    clearTimeout(voiceAutoStopTimer);
    clearTimeout(recognitionFallbackTimer);
    clearTimeout(recognitionStartTimer);
    const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
    const text = (voiceTranscript || chatInput.value).trim();
    const shouldSend = isListening && !stopVoiceRequested && text;
    isListening = false;
    updateVoiceButton();
    if (shouldSend) {
      setVoiceStatus(t.voiceSending);
      sendMessage(text);
    } else if (!text && !stopVoiceRequested) {
      setVoiceStatus(t.noSpeech, true);
    } else {
      setVoiceStatus(t.voiceStopped);
    }
  };

  return recognizer;
}

function initVoiceInput() {
  recognition = createSpeechRecognition();
}

function startRecognition(langOverride = null) {
  recognition = createSpeechRecognition(langOverride);
  if (!recognition) return;
  recognition.lang = langOverride || languageCode();
  recognitionLangInUse = recognition.lang;
  recognition.start();
  clearTimeout(recognitionStartTimer);
  recognitionStartTimer = setTimeout(() => {
    if (!isListening) {
      try { recognition.abort(); } catch (_) {}
      recognition = createSpeechRecognition();
      updateVoiceButton();
      setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).voiceTryAgain, true);
    }
  }, 2500);
}

async function toggleVoiceInput() {
  if (!recognition || isProcessing) return;
  if (isListening) {
    stopVoiceRequested = true;
    clearTimeout(voiceAutoStopTimer);
    clearTimeout(recognitionFallbackTimer);
    clearTimeout(recognitionStartTimer);
    recognition.stop();
    return;
  }
  try {
    const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
    setVoiceStatus(t.voiceStarting);
    stopVoiceRequested = false;
    voiceTranscript = '';
    clearTimeout(voiceAutoStopTimer);
    clearTimeout(recognitionFallbackTimer);
    clearTimeout(recognitionStartTimer);
    chatInput.value = '';
    startRecognition();
  } catch (err) {
    if (err && err.name === 'InvalidStateError' && recognition) {
      try { recognition.stop(); } catch (_) {}
      setTimeout(() => {
        try {
          stopVoiceRequested = false;
          startRecognition(APP_LANGUAGE === 'ta' ? 'en-IN' : null);
        } catch (_) {
          setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).voiceTryAgain, true);
        }
      }, 250);
      return;
    }
    updateVoiceButton();
    setVoiceStatus((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).voiceTryAgain, true);
  }
}

function createWelcomeChips() {
  const wrap = document.createElement('div');
  wrap.className = 'welcome-chips';
  const queries = APP_LANGUAGE === 'ta' ? WELCOME_QUERIES_TA : WELCOME_QUERIES;
  queries.forEach(query => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'welcome-chip';
    btn.textContent = query;
    btn.addEventListener('click', () => { chatInput.value = query; chatInput.focus(); });
    wrap.appendChild(btn);
  });
  return wrap;
}

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
  bubble.innerHTML = role === 'user' ? text : parseMarkdown(removeFollowupMarker(text));
  const bottomBar = document.createElement('div');
  bottomBar.className = 'msg-bottom';
  bottomBar.innerHTML = `<span class="msg-time">${getTime()}</span>`;
  if (role === 'bot') {
    const speakBtn = document.createElement('button');
    speakBtn.className = 'msg-tts-btn';
    speakBtn.type = 'button';
    speakBtn.title = 'Read this reply aloud';
    speakBtn.textContent = '🔈';
    speakBtn.addEventListener('click', () => {
      if (currentUtterance || speechQueue.length) stopSpeaking();
      else speakText(text);
    });
    bottomBar.appendChild(speakBtn);
  }
  content.appendChild(bubble);
  if (role === 'bot' && isWelcome) content.appendChild(createWelcomeChips());
  if (role === 'bot') {
    const chips = extractFollowupChips(text);
    if (chips.length) {
      const chipContainer = document.createElement('div');
      chipContainer.className = 'followup-chips';
      chips.forEach(chip => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'followup-chip';
        btn.textContent = chip;
        btn.addEventListener('click', () => { chatInput.value = chip; chatInput.focus(); });
        chipContainer.appendChild(btn);
      });
      content.appendChild(chipContainer);
    }
  }
  content.appendChild(bottomBar);
  row.appendChild(avatar);
  row.appendChild(content);
  messagesList.appendChild(row);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
  if (role === 'bot' && ttsEnabled) speakText(text);
}

let typingEl = null;
function showTyping() {
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'msg-row typing-row bot-row';
  typingEl.innerHTML = `<div class="msg-avatar bot-avatar">🌿</div><div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div><span class="typing-label">Thinking...</span></div>`;
  messagesList.appendChild(typingEl);
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
}
function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

async function sendMessage(text) {
  if (isProcessing || !text.trim()) return;
  isProcessing = true;
  renderMessage(text, 'user');
  chatInput.value = '';
  sendBtn.disabled = true;
  showTyping();
  try {
    const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, session_id: SESSION_ID, language: APP_LANGUAGE }) });
    const data = await res.json();
    if (data.session_id) { SESSION_ID = data.session_id; localStorage.setItem('sf_session', SESSION_ID); }
    if (data.memory) updateContextUI(data.memory);
    hideTyping();
    renderMessage(data.text || (APP_LANGUAGE === 'ta' ? 'பதில் கிடைக்கவில்லை.' : 'No response received.'), 'bot');
  } catch (_) {
    hideTyping();
    renderMessage(APP_LANGUAGE === 'ta' ? 'இணைப்பு பிழை. சேவையகம் இயங்குகிறதா என சரிபார்க்கவும்.' : 'Connection error. Please check if the server is running.', 'bot');
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

async function analyzeSoilImage(file) {
  if (!file || isProcessing) return;
  isProcessing = true;
  renderMessage(`📸 Uploaded: ${file.name}`, 'user');
  showTyping();
  if (soilPreviewName) soilPreviewName.textContent = `Analyzing ${file.name}...`;
  if (soilStrip) soilStrip.style.display = 'flex';
  const form = new FormData();
  form.append('image', file);
  form.append('session_id', SESSION_ID || '');
  form.append('language', APP_LANGUAGE);
  if (activeContext.district) form.append('district', activeContext.district);
  try {
    const res = await fetch('/soil', { method: 'POST', body: form });
    const data = await res.json();
    if (data.session_id) { SESSION_ID = data.session_id; localStorage.setItem('sf_session', SESSION_ID); }
    if (data.memory) updateContextUI(data.memory);
    if (soilPreviewName) soilPreviewName.textContent = data.soil_type ? `Detected: ${data.soil_type}` : `Could not analyze ${file.name}`;
    hideTyping();
    renderMessage(data.error ? `❌ ${data.error}` : data.text, 'bot');
  } catch (_) {
    if (soilPreviewName) soilPreviewName.textContent = `Upload failed: ${file.name}`;
    hideTyping();
    renderMessage(APP_LANGUAGE === 'ta' ? 'மண் படத்தை பதிவேற்ற முடியவில்லை.' : 'Soil image upload failed.', 'bot');
  } finally {
    isProcessing = false;
    soilImageInput.value = '';
    sendBtn.disabled = false;
  }
}

function updateWhatIfLabels() {
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  if (whatifIrrVal && whatifIrrSlider) whatifIrrVal.textContent = `${parseInt(whatifIrrSlider.value)}%`;
  if (whatifRainVal && whatifRainSlider) whatifRainVal.textContent = `${parseInt(whatifRainSlider.value)} mm`;
  if (whatifFertVal && whatifFertSlider) whatifFertVal.textContent = `${parseInt(whatifFertSlider.value)}%`;
  if (whatifTempVal && whatifTempSlider) whatifTempVal.textContent = `${parseInt(whatifTempSlider.value)} C`;
  if (whatifPestVal && whatifPestSlider) whatifPestVal.textContent = `${parseInt(whatifPestSlider.value)}%`;
  if (whatifMoistureVal && whatifMoistureSlider) whatifMoistureVal.textContent = `${parseInt(whatifMoistureSlider.value)}%`;
  if (simulateBtn) simulateBtn.textContent = activeContext.district ? t.simulateFor(activeContext.district) : t.simulate;
}

function formatSimulationResponse(data, payload) {
  const crop = data.crop || payload.crop || 'Current crop';
  const district = data.district || payload.district;
  const yieldImpact = Number(data.yield_impact_pct || 0);
  const pestChange = Number(data.pest_risk_change_pct || 0);
  const yieldDirection = yieldImpact > 0 ? 'increase' : (yieldImpact < 0 ? 'decrease' : 'stay nearly stable');
  const pestDirection = pestChange > 0 ? 'increase' : (pestChange < 0 ? 'decrease' : 'stay nearly stable');
  return `## What-If Simulation: ${crop} in ${district}

### Scenario Inputs
- Rainfall change: **${payload.rainfall_delta_mm} mm**
- Irrigation change: **${payload.irrigation_delta_pct}%**
- Fertilizer change: **${payload.fertilizer_delta_pct}%**
- Temperature change: **${payload.temperature_delta_c} C**
- Pest intensity: **${payload.pest_intensity_pct}%**
- Soil moisture: **${payload.soil_moisture_pct}%**

### Expected Result
- Expected yield impact: **${yieldImpact}%**. Yield may **${yieldDirection}** under this scenario.
- Pest risk change: **${pestChange}%**. Pest pressure may **${pestDirection}**.

### Recommended Action
${data.recommended_action || 'Monitor field conditions and adjust irrigation, fertilizer, and pest scouting based on local observations.'}`;
}

async function sendSimulation() {
  const district = activeContext.district;
  if (!district) {
    renderMessage((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).noDistrictSimulation, 'bot');
    return;
  }
  const payload = {
    district,
    crop: activeContext.crop,
    soil: activeContext.soil,
    season: activeContext.season,
    irrigation_delta_pct: parseInt(whatifIrrSlider.value || 0),
    rainfall_delta_mm: parseInt(whatifRainSlider.value || 0),
    fertilizer_delta_pct: parseInt(whatifFertSlider.value || 0),
    temperature_delta_c: parseInt(whatifTempSlider.value || 0),
    pest_intensity_pct: parseInt(whatifPestSlider.value || 0),
    soil_moisture_pct: parseInt(whatifMoistureSlider.value || 55),
    language: APP_LANGUAGE,
  };
  const scenarioText = APP_LANGUAGE === 'ta'
    ? `${district} மாவட்டத்தில் ${payload.crop || 'தேர்ந்தெடுத்த பயிர்'} பயிருக்கு என்ன ஆகும்? சோதனை: மழை ${payload.rainfall_delta_mm} மில்லிமீட்டர், பாசனம் ${payload.irrigation_delta_pct}%, உரம் ${payload.fertilizer_delta_pct}%, வெப்பநிலை ${payload.temperature_delta_c} C, பூச்சி தீவிரம் ${payload.pest_intensity_pct}%, மண் ஈரப்பதம் ${payload.soil_moisture_pct}%.`
    : `Run what-if simulation for ${payload.crop || 'current crop'} in ${district}: rainfall ${payload.rainfall_delta_mm} mm, irrigation ${payload.irrigation_delta_pct}%, fertilizer ${payload.fertilizer_delta_pct}%, temperature ${payload.temperature_delta_c} C, pest intensity ${payload.pest_intensity_pct}%, soil moisture ${payload.soil_moisture_pct}%.`;
  renderMessage(scenarioText, 'user');
  showTyping();
  if (simulateBtn) simulateBtn.disabled = true;
  try {
    const res = await fetch('/simulate_advanced', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Simulation failed');
    hideTyping();
    renderMessage(data.text || formatSimulationResponse(data, payload), 'bot');
  } catch (err) {
    hideTyping();
    renderMessage(APP_LANGUAGE === 'ta' ? 'சோதனை இப்போது கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும்.' : `Simulation unavailable: ${err.message || 'Please try again.'}`, 'bot');
  } finally {
    if (simulateBtn) simulateBtn.disabled = false;
  }
}

async function resetAllOnLoad() {
  const oldSession = localStorage.getItem('sf_session');
  if (oldSession) {
    try { await fetch('/reset_session', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ session_id: oldSession })}); } catch (_) {}
  }
  localStorage.removeItem('sf_session');
  SESSION_ID = null;
  clearContextUI();
  if (chatInput) chatInput.value = '';
  if (soilStrip) soilStrip.style.display = 'none';
  if (soilPreviewImg) soilPreviewImg.src = '';
  if (soilPreviewName) soilPreviewName.textContent = '';
  if (soilImageInput) soilImageInput.value = '';
  if (whatifIrrSlider) whatifIrrSlider.value = '0';
  if (whatifRainSlider) whatifRainSlider.value = '0';
  messagesList.innerHTML = '';
}

async function clearChat() {
  messagesList.innerHTML = '';
  const oldSession = SESSION_ID;
  SESSION_ID = null;
  localStorage.removeItem('sf_session');
  clearContextUI();
  if (oldSession) { try { await fetch('/reset_session', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ session_id: oldSession })}); } catch (_) {} }
  renderWelcome();
}

function renderWelcome() {
  messagesList.innerHTML = '';
  renderMessage(APP_LANGUAGE === 'ta' ? INTRO_MESSAGE_TA : INTRO_MESSAGE, 'bot', true, true);
}

function setSidebarOpen(open) {
  if (!sidebar) return;
  sidebar.classList.toggle('open', Boolean(open));
  if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
}

sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(chatInput.value.trim()); } });
if (voiceInputBtn) voiceInputBtn.addEventListener('click', toggleVoiceInput);
if (languageToggle) languageToggle.addEventListener('click', toggleLanguage);
clearChatBtn.addEventListener('click', clearChat);
sidebarToggle.addEventListener('click', () => setSidebarOpen(!sidebar.classList.contains('open')));
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', () => setSidebarOpen(false));
if (chatMenuBtn) chatMenuBtn.addEventListener('click', e => {
  e.stopPropagation();
  setChatMenuOpen(chatMenuPanel.hidden);
});
if (chatMenuPanel) chatMenuPanel.addEventListener('click', () => setChatMenuOpen(false));
if (ttsBtnGlobal) ttsBtnGlobal.addEventListener('click', toggleGlobalTTS);
if (soilImageInput) soilImageInput.addEventListener('change', () => { const file = soilImageInput.files[0]; if (file) analyzeSoilImage(file); });
if (removeImgBtn) removeImgBtn.addEventListener('click', () => {
  soilStrip.style.display = 'none';
  if (soilPreviewImg) soilPreviewImg.src = '';
  soilImageInput.value = '';
});
if (whatifIrrSlider) whatifIrrSlider.addEventListener('input', updateWhatIfLabels);
if (whatifRainSlider) whatifRainSlider.addEventListener('input', updateWhatIfLabels);
if (whatifFertSlider) whatifFertSlider.addEventListener('input', updateWhatIfLabels);
if (whatifTempSlider) whatifTempSlider.addEventListener('input', updateWhatIfLabels);
if (whatifPestSlider) whatifPestSlider.addEventListener('input', updateWhatIfLabels);
if (whatifMoistureSlider) whatifMoistureSlider.addEventListener('input', updateWhatIfLabels);
if (simulateBtn) simulateBtn.addEventListener('click', sendSimulation);
if (applyContextBtn) applyContextBtn.addEventListener('click', applyManualContext);
if (resetContextBtn) resetContextBtn.addEventListener('click', resetManualContext);
if (manualMonth) manualMonth.addEventListener('change', syncSeasonFromMonth);
if (manualSeason) manualSeason.addEventListener('change', syncMonthFromSeason);
if (window.speechSynthesis) {
  loadPreferredVoice();
  speechSynthesis.onvoiceschanged = () => loadPreferredVoice(currentSpeechLang || languageCode());
}
initVoiceInput();

document.addEventListener('click', e => {
  if (chatMenuPanel && !chatMenuPanel.hidden && !e.target.closest('.chat-menu')) {
    setChatMenuOpen(false);
  }
  if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) setSidebarOpen(false);
  }
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') setChatMenuOpen(false);
  if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) setSidebarOpen(false);
});

(async function init() {
  await resetAllOnLoad();
  updateLanguageUI();
  updateTTSButton();
  updateWhatIfLabels();
  renderWelcome();
  chatInput.focus();
})();
