
let SESSION_ID = localStorage.getItem('sf_session') || null;
let activeContext = { district: null, soil: null, season: null, month: null, crop: null };
let isProcessing = false;

const messagesList = document.getElementById('messagesList');
const messagesWrap = document.getElementById('messagesWrap');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const voiceInputBtn = document.getElementById('voiceInputBtn');
const voiceStatus = document.getElementById('voiceStatus');
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

const INTRO_MESSAGE = `🤖 I'm your Smart Farming AI for Tamil Nadu, and I'm here to help with agriculture questions.\n\nTry one of these examples:`;

const WELCOME_QUERIES = [
  'Best crops for Madurai with red soil during Kharif?',
  'How much rainfall does Coimbatore receive?',
  'Pest risks in Dharmapuri?',
  'Overview of Erode district?'
];

let ttsEnabled = false;
let currentUtterance = null;
let speechQueue = [];
let preferredVoice = null;
let recognition = null;
let isListening = false;
let stopVoiceRequested = false;

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
  renderMessage(`✅ Manual context updated.`, 'bot');
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

function loadPreferredVoice() {
  if (!window.speechSynthesis) return null;
  const voices = speechSynthesis.getVoices();
  preferredVoice =
    voices.find(v => /en-IN/i.test(v.lang)) ||
    voices.find(v => /India/i.test(v.name)) ||
    voices.find(v => /^en-/i.test(v.lang)) ||
    voices[0] ||
    null;
  return preferredVoice;
}

function splitSpeechText(text, maxLen = 220) {
  const sentences = text.match(/[^.!?]+[.!?]*/g) || [text];
  const chunks = [];
  let current = '';
  sentences.forEach(sentence => {
    const next = `${current} ${sentence}`.trim();
    if (next.length > maxLen && current) {
      chunks.push(current);
      current = sentence.trim();
    } else {
      current = next;
    }
  });
  if (current) chunks.push(current);
  return chunks;
}

function speakNextChunk() {
  if (!window.speechSynthesis || !speechQueue.length) {
    currentUtterance = null;
    return;
  }
  const chunk = speechQueue.shift();
  currentUtterance = new SpeechSynthesisUtterance(chunk);
  currentUtterance.lang = preferredVoice?.lang || 'en-IN';
  currentUtterance.voice = preferredVoice || loadPreferredVoice();
  currentUtterance.rate = 0.94;
  currentUtterance.pitch = 1.02;
  currentUtterance.volume = 1;
  currentUtterance.onend = speakNextChunk;
  currentUtterance.onerror = () => { currentUtterance = null; speechQueue = []; };
  speechSynthesis.speak(currentUtterance);
}

function getTime() { return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }); }
function speakText(text) {
  if (!window.speechSynthesis) return;
  const cleaned = cleanSpeechText(text);
  if (!cleaned) return;
  stopSpeaking();
  loadPreferredVoice();
  speechQueue = splitSpeechText(cleaned);
  speakNextChunk();
}
function stopSpeaking() {
  speechQueue = [];
  if (window.speechSynthesis) speechSynthesis.cancel();
  currentUtterance = null;
}
function updateTTSButton() {
  if (!ttsBtnGlobal) return;
  ttsBtnGlobal.classList.toggle('tts-active', ttsEnabled);
  ttsBtnGlobal.title = ttsEnabled ? 'Disable auto voice replies' : 'Enable auto voice replies';
  ttsBtnGlobal.querySelector('.tts-icon').textContent = ttsEnabled ? '🔊' : '🔇';
}
function toggleGlobalTTS() { ttsEnabled = !ttsEnabled; updateTTSButton(); if (!ttsEnabled) stopSpeaking(); }

function setVoiceStatus(message, isError = false) {
  if (!voiceStatus) return;
  voiceStatus.textContent = message || 'Tamil Nadu Smart Farming • Context-aware follow-up support';
  voiceStatus.classList.toggle('voice-error', Boolean(isError));
}

function updateVoiceButton() {
  if (!voiceInputBtn) return;
  voiceInputBtn.classList.toggle('listening', isListening);
  voiceInputBtn.textContent = isListening ? '■' : '🎙';
  voiceInputBtn.title = isListening ? 'Stop listening' : 'Speak your question';
}

function initVoiceInput() {
  if (!voiceInputBtn) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceInputBtn.disabled = true;
    voiceInputBtn.title = 'Voice input is not supported in this browser';
    setVoiceStatus('Voice input is not supported in this browser.', true);
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = 'en-IN';
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    stopVoiceRequested = false;
    stopSpeaking();
    updateVoiceButton();
    setVoiceStatus('Listening... speak your farming question.');
  };

  recognition.onresult = event => {
    let finalText = '';
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal) finalText += transcript;
      else interimText += transcript;
    }
    const spokenText = (finalText || interimText).trim();
    if (spokenText) chatInput.value = spokenText;
    chatInput.focus();
    chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
    if (finalText.trim()) {
      setVoiceStatus(`Heard: ${finalText.trim()}`);
    }
  };

  recognition.onerror = event => {
    const isPermissionError = event.error === 'not-allowed' || event.error === 'service-not-allowed';
    const msg = isPermissionError
      ? 'Microphone permission was blocked. Please allow microphone access.'
      : 'Voice input stopped. Please try again.';
    isListening = false;
    stopVoiceRequested = true;
    updateVoiceButton();
    setVoiceStatus(msg, true);
  };

  recognition.onend = () => {
    const text = chatInput.value.trim();
    const shouldSend = isListening && !stopVoiceRequested && text;
    isListening = false;
    updateVoiceButton();
    if (shouldSend) {
      setVoiceStatus('Sending voice question...');
      sendMessage(text);
    } else if (!text && !stopVoiceRequested) {
      setVoiceStatus('No speech detected. Tap the mic and try again.', true);
    } else {
      setVoiceStatus('Voice input stopped.');
    }
  };
}

function toggleVoiceInput() {
  if (!recognition || isProcessing) return;
  if (isListening) {
    stopVoiceRequested = true;
    recognition.stop();
    return;
  }
  try {
    stopVoiceRequested = false;
    chatInput.value = '';
    recognition.start();
  } catch (_) {
    updateVoiceButton();
    setVoiceStatus('Voice input is already starting. Please wait a moment.', true);
  }
}

function createWelcomeChips() {
  const wrap = document.createElement('div');
  wrap.className = 'welcome-chips';
  WELCOME_QUERIES.forEach(query => {
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
    const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, session_id: SESSION_ID }) });
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
  if (whatifIrrVal) whatifIrrVal.textContent = `${parseInt(whatifIrrSlider.value)}%`;
  if (whatifRainVal) whatifRainVal.textContent = `${parseInt(whatifRainSlider.value)} mm`;
  if (simulateBtn) simulateBtn.textContent = activeContext.district ? `▶ Simulate for ${activeContext.district}` : '▶ Run Simulation';
}

function sendSimulation() {
  const district = activeContext.district;
  if (!district) { renderMessage('⚠️ Please set a district in Manual Context or ask a district-specific question first, then run the simulation again.', 'bot'); return; }
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

function renderWelcome() { messagesList.innerHTML = ''; renderMessage(INTRO_MESSAGE, 'bot', true, true); }

sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(chatInput.value.trim()); } });
if (voiceInputBtn) voiceInputBtn.addEventListener('click', toggleVoiceInput);
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
  speechSynthesis.onvoiceschanged = loadPreferredVoice;
}
initVoiceInput();

document.addEventListener('click', e => {
  if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) sidebar.classList.remove('open');
  }
});

(async function init() {
  await resetAllOnLoad();
  updateTTSButton();
  updateWhatIfLabels();
  renderWelcome();
  chatInput.focus();
})();
