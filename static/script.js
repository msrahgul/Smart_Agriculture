
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
const whatifIrrSlider = document.getElementById('whatifIrrSlider');
const whatifRainSlider = document.getElementById('whatifRainSlider');
const whatifIrrVal = document.getElementById('whatifIrrVal');
const whatifRainVal = document.getElementById('whatifRainVal');
const simulateBtn = document.getElementById('simulateBtn');
const manualCrop = document.getElementById('manualCrop');
const manualDistrict = document.getElementById('manualDistrict');
const manualSoil = document.getElementById('manualSoil');
const manualMonth = document.getElementById('manualMonth');
const manualSeason = document.getElementById('manualSeason');
const applyContextBtn = document.getElementById('applyContextBtn');
const resetContextBtn = document.getElementById('resetContextBtn');

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
  activeContext = { ...activeContext, ...memory };
  if (ctxCrop) ctxCrop.textContent = prettyContextValue(activeContext.crop);
  if (ctxDistrict) ctxDistrict.textContent = prettyContextValue(activeContext.district);
  if (ctxSoil) ctxSoil.textContent = prettyContextValue(activeContext.soil);
  if (ctxMonth) ctxMonth.textContent = prettyContextValue(activeContext.month);
  if (ctxSeason) ctxSeason.textContent = prettyContextValue(activeContext.season);
  syncManualContextInputs();
  updateWhatIfLabels();
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
    .replace(/\b(t\/ha)\b/gi, ' tonnes per hectare')
    .replace(/\bNPK\b/g, 'N P K')
    .replace(/\bmm\b/g, ' millimetres')
    .replace(/\bha\b/g, ' hectares')
    .replace(/\s+([,.])/g, '$1')
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

function waitForVoices(timeoutMs = 1800) {
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
  preferredVoice =
    voices.find(v => /en-IN/i.test(v.lang)) ||
    voices.find(v => /India/i.test(v.name)) ||
    voices.find(v => /^en-/i.test(v.lang)) ||
    voices[0] ||
    null;
  return preferredVoice;
}

function splitSpeechText(text, maxLen = 180) {
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
      for (let i = 0; i < trimmed.length; i += maxLen) {
        chunks.push(trimmed.slice(i, i + maxLen));
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
  currentUtterance.rate = currentSpeechLang === 'ta-IN' ? 0.86 : 0.94;
  currentUtterance.pitch = currentSpeechLang === 'ta-IN' ? 1.0 : 1.02;
  currentUtterance.volume = 1;
  currentUtterance.onend = () => {
    if (runId !== speechRunId) return;
    clearInterval(speechKeepAlive);
    currentUtterance = null;
    speakNextChunk();
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
  ttsBtnGlobal.classList.toggle('tts-active', ttsEnabled);
  ttsBtnGlobal.title = ttsEnabled ? t.disableTTS : t.enableTTS;
  ttsBtnGlobal.querySelector('.tts-icon').textContent = ttsEnabled ? '🔊' : '🔇';
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
  setText('.logo-title', t.logoTitle);
  setText('.logo-sub', t.logoSub);
  setText('.topbar-title', t.topbarTitle);
  setText('.topbar-sub', t.topbarSub);
  const sidebarLabels = document.querySelectorAll('.sidebar-label');
  if (sidebarLabels[0]) sidebarLabels[0].textContent = t.soilLabel;
  if (sidebarLabels[1]) sidebarLabels[1].textContent = t.manualLabel;
  if (sidebarLabels[2]) sidebarLabels[2].textContent = t.activeLabel;
  if (sidebarLabels[3]) sidebarLabels[3].textContent = t.whatifLabel;
  setText('.tool-help', t.soilHelp);
  setText('.sidebar-upload-btn span', t.uploadSoil);
  const labels = document.querySelectorAll('.manual-field label');
  if (labels[0]) labels[0].textContent = t.cropLabel;
  if (labels[1]) labels[1].textContent = t.locationLabel;
  if (labels[2]) labels[2].textContent = t.soilFieldLabel;
  if (labels[3]) labels[3].textContent = t.monthLabel;
  if (labels[4]) labels[4].textContent = t.seasonLabel;
  setText('#applyContextBtn', t.applyContext);
  setText('#resetContextBtn', t.resetContext);
  setText('.context-help', t.contextHelp);
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
  setTitle('#clearChat', t.clearTitle);
  setTitle('#voiceInputBtn', isListening ? t.micStopTitle : t.micTitle);
  setTitle('#sendBtn', t.sendTitle);
  setTitle('#sidebarToggle', t.sidebarTitle);
  setTitle('#removeImgBtn', t.removeImageTitle);
  setPlaceholder('#manualCrop', t.cropPlaceholder);
  setPlaceholder('#manualDistrict', t.districtPlaceholder);
  setPlaceholder('#chatInput', t.chatPlaceholder);
  setVoiceStatus(t.inputFooter);
  updateTTSButton();
}

function updateLanguageUI() {
  if (!languageToggle) return;
  languageToggle.classList.toggle('tamil-mode', APP_LANGUAGE === 'ta');
  languageToggle.title = APP_LANGUAGE === 'ta' ? 'தமிழில் உள்ளது. English க்கு மாற்ற' : 'English mode. Switch to Tamil';
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
  voiceInputBtn.textContent = isListening ? '■' : '🎙';
  voiceInputBtn.title = isListening ? t.micStopTitle : t.micTitle;
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
    renderMessage(data.text || 'No response received.', 'bot');
  } catch (_) {
    hideTyping();
    renderMessage('❌ Connection error. Please check if the server is running.', 'bot');
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
    renderMessage('❌ Soil image upload failed.', 'bot');
  } finally {
    isProcessing = false;
    soilImageInput.value = '';
    sendBtn.disabled = false;
  }
}

function updateWhatIfLabels() {
  const t = UI_TEXT[APP_LANGUAGE] || UI_TEXT.en;
  if (whatifIrrVal) whatifIrrVal.textContent = `${parseInt(whatifIrrSlider.value)}%`;
  if (whatifRainVal) whatifRainVal.textContent = `${parseInt(whatifRainSlider.value)} mm`;
  if (simulateBtn) simulateBtn.textContent = activeContext.district ? t.simulateFor(activeContext.district) : t.simulate;
}

function sendSimulation() {
  const district = activeContext.district;
  if (!district) { renderMessage((UI_TEXT[APP_LANGUAGE] || UI_TEXT.en).noDistrictSimulation, 'bot'); return; }
  const irrDelta = parseInt(whatifIrrSlider.value);
  const rainDelta = parseInt(whatifRainSlider.value);
  let query = 'What if';
  if (irrDelta !== 0) query += irrDelta > 0 ? ` irrigation improved by ${irrDelta}%` : ` irrigation reduced by ${Math.abs(irrDelta)}%`;
  if (rainDelta !== 0) query += `${irrDelta !== 0 ? ' and' : ''} rainfall ${rainDelta > 0 ? 'increased' : 'reduced'} by ${Math.abs(rainDelta)}mm`;
  if (irrDelta === 0 && rainDelta === 0) query = 'What if irrigation reduced by 20%';
  if (activeContext.crop) query += ` for ${activeContext.crop}`;
  query += ` in ${district}`;
  sendMessage(query);
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

sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(chatInput.value.trim()); } });
if (voiceInputBtn) voiceInputBtn.addEventListener('click', toggleVoiceInput);
if (languageToggle) languageToggle.addEventListener('click', toggleLanguage);
clearChatBtn.addEventListener('click', clearChat);
sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
if (ttsBtnGlobal) ttsBtnGlobal.addEventListener('click', toggleGlobalTTS);
if (soilImageInput) soilImageInput.addEventListener('change', () => { const file = soilImageInput.files[0]; if (file) analyzeSoilImage(file); });
if (removeImgBtn) removeImgBtn.addEventListener('click', () => {
  soilStrip.style.display = 'none';
  if (soilPreviewImg) soilPreviewImg.src = '';
  soilImageInput.value = '';
});
if (whatifIrrSlider) whatifIrrSlider.addEventListener('input', updateWhatIfLabels);
if (whatifRainSlider) whatifRainSlider.addEventListener('input', updateWhatIfLabels);
if (simulateBtn) simulateBtn.addEventListener('click', sendSimulation);
if (applyContextBtn) applyContextBtn.addEventListener('click', applyManualContext);
if (resetContextBtn) resetContextBtn.addEventListener('click', resetManualContext);
if (manualMonth) manualMonth.addEventListener('change', syncSeasonFromMonth);
if (manualSeason) manualSeason.addEventListener('change', syncMonthFromSeason);
if (window.speechSynthesis) {
  loadPreferredVoice();
  speechSynthesis.onvoiceschanged = () => loadPreferredVoice();
}
initVoiceInput();

document.addEventListener('click', e => {
  if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) sidebar.classList.remove('open');
  }
});

(async function init() {
  await resetAllOnLoad();
  updateLanguageUI();
  updateTTSButton();
  updateWhatIfLabels();
  renderWelcome();
  chatInput.focus();
})();
