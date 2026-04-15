/* ════════════════════════════════════════════════════════════
   SmartFarm AI – Chat Frontend Logic v3
   AI-first agent + Score Badges + Follow-up Chips + What-If UI
   ════════════════════════════════════════════════════════════ */

// ── Session ───────────────────────────────────────────────────
let SESSION_ID = localStorage.getItem('sf_session') || null;
let isProcessing = false;
let lastKnownDistrict = null;
let activeContext = JSON.parse(localStorage.getItem('sf_context') || '{}');

const INTRO_MESSAGE = `🤖 I'm your Smart Farming AI for Tamil Nadu, and I'm best at answering specific agricultural questions.

Try asking things like:

"Best crops for Madurai with red soil during Kharif?"
"How much rainfall does Coimbatore receive?"
"Pest risks in Dharmapuri?"
"Overview of Erode district?"

Or type help to see everything I can do.`;

// TTS state
let ttsEnabled = JSON.parse(localStorage.getItem('sf_tts') || 'false');
let currentUtterance = null;

// ── DOM refs ──────────────────────────────────────────────────
const messagesList   = document.getElementById('messagesList');
const messagesWrap   = document.getElementById('messagesWrap');
const chatInput      = document.getElementById('chatInput');
const sendBtn        = document.getElementById('sendBtn');
const clearChatBtn   = document.getElementById('clearChat');
const sidebarToggle  = document.getElementById('sidebarToggle');
const sidebar        = document.querySelector('.sidebar');
const quickQueries   = document.getElementById('quickQueries');
const soilImageInput = document.getElementById('soilImageInput');
const soilStrip      = document.getElementById('soilPreviewStrip');
const soilPreviewImg = document.getElementById('soilPreviewImg');
const soilPreviewName= document.getElementById('soilPreviewName');
const removeImgBtn   = document.getElementById('removeImgBtn');
const districtFilter = document.getElementById('districtFilter');
const ttsBtnGlobal   = document.getElementById('ttsBtnGlobal');
const whatifPanel    = document.getElementById('whatifPanel');
const ctxCrop        = document.getElementById('ctxCrop');
const ctxDistrict    = document.getElementById('ctxDistrict');
const ctxSoil        = document.getElementById('ctxSoil');
const ctxMonth       = document.getElementById('ctxMonth');
const ctxSeason      = document.getElementById('ctxSeason');
const whatifIrrSlider= document.getElementById('whatifIrrSlider');
const whatifRainSlider=document.getElementById('whatifRainSlider');
const whatifIrrVal   = document.getElementById('whatifIrrVal');
const whatifRainVal  = document.getElementById('whatifRainVal');
const simulateBtn    = document.getElementById('simulateBtn');


function prettyContextValue(value) {
    if (!value) return '—';
    return String(value)
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function updateContextUI(memory = {}) {
    activeContext = { ...activeContext, ...memory };
    localStorage.setItem('sf_context', JSON.stringify(activeContext));
    if (ctxCrop) ctxCrop.textContent = prettyContextValue(activeContext.crop);
    if (ctxDistrict) ctxDistrict.textContent = prettyContextValue(activeContext.district);
    if (ctxSoil) ctxSoil.textContent = prettyContextValue(activeContext.soil);
    if (ctxMonth) ctxMonth.textContent = prettyContextValue(activeContext.month);
    if (ctxSeason) ctxSeason.textContent = prettyContextValue(activeContext.season);
    if (activeContext.district) {
        lastKnownDistrict = activeContext.district;
        _updateWhatifHint(activeContext.district);
    }
}

function clearContextUI() {
    activeContext = {};
    localStorage.removeItem('sf_context');
    updateContextUI({});
}

// ── Score badge renderer ──────────────────────────────────────
// Detects **SCORE:7.5/10:Very Good** markers and renders visual badges
function renderScoreBadges(html) {
    return html.replace(
        /\*\*SCORE:(\d+\.?\d*)\/10:([^*]+)\*\*/g,
        (_, score, label) => {
            const numScore = parseFloat(score);
            const pct = (numScore / 10) * 100;
            const colorClass = numScore >= 8.5 ? 'score-excellent'
                             : numScore >= 7.0 ? 'score-very-good'
                             : numScore >= 5.5 ? 'score-moderate'
                             : numScore >= 4.0 ? 'score-below'
                             : 'score-poor';
            return `<div class="score-badge-wrap">
                <div class="score-badge ${colorClass}">${score}<span>/10</span></div>
                <div class="score-bar-wrap"><div class="score-bar-fill ${colorClass}" style="width:0%" data-pct="${pct}"></div></div>
                <span class="score-label">${label.trim()}</span>
            </div>`;
        }
    );
}

// Animate score bars after insertion
function animateScoreBars(container) {
    container.querySelectorAll('.score-bar-fill').forEach(bar => {
        const pct = bar.dataset.pct;
        requestAnimationFrame(() => {
            setTimeout(() => { bar.style.width = pct + '%'; }, 100);
        });
    });
}

// ── Follow-up chips extractor ────────────────────────────────
// Detects FOLLOWUP_CHIPS:chip1|chip2|chip3 markers
function extractFollowupChips(text) {
    const match = text.match(/FOLLOWUP_CHIPS:([^\n]+)/);
    if (!match) return [];
    return match[1].split('|').map(c => c.trim()).filter(Boolean).slice(0, 4);
}

function removeFollowupMarker(text) {
    return text.replace(/---\s*\*\*FOLLOWUP_CHIPS:[^\n]+\*\*\s*/g, '')
               .replace(/FOLLOWUP_CHIPS:[^\n]+/g, '').trim();
}

// ── Markdown → HTML ───────────────────────────────────────────
function parseMarkdown(text) {
    // Tables first (before line processing)
    text = text.replace(/\n(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g, parseTable);

    let lines = text.split('\n');
    let html = '';
    let inList = false;

    for (let line of lines) {
        // Headings
        if (/^### (.+)/.test(line)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h3>${line.replace(/^### /, '')}</h3>`;
        } else if (/^## (.+)/.test(line)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h2>${line.replace(/^## /, '')}</h2>`;
        } else if (/^# (.+)/.test(line)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h1>${line.replace(/^# /, '')}</h1>`;
        }
        // Bullet
        else if (/^[*-] (.+)/.test(line)) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${inlineFormat(line.replace(/^[*-] /, ''))}</li>`;
        }
        // Numbered
        else if (/^\d+\. (.+)/.test(line)) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${inlineFormat(line.replace(/^\d+\. /, ''))}</li>`;
        }
        // HR
        else if (/^---$/.test(line.trim())) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<hr>';
        }
        // Table HTML (already rendered)
        else if (line.trim().startsWith('<table')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += line;
        }
        // Empty line
        else if (line.trim() === '') {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<br>';
        }
        // Normal paragraph
        else {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<p>${inlineFormat(line)}</p>`;
        }
    }
    if (inList) html += '</ul>';
    return html;
}

function inlineFormat(text) {
    return text
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function parseTable(match, header, sep, body) {
    const headers = header.trim().split('|').map(c => c.trim()).filter(Boolean);
    const rows = body.trim().split('\n').filter(r => r.includes('|'));
    let html = '<table><thead><tr>';
    headers.forEach(c => { html += `<th>${inlineFormat(c)}</th>`; });
    html += '</tr></thead><tbody>';
    rows.forEach(row => {
        const cells = row.trim().split('|').map(c => c.trim()).filter(Boolean);
        html += '<tr>';
        cells.forEach(c => { html += `<td>${inlineFormat(c)}</td>`; });
        html += '</tr>';
    });
    html += '</tbody></table>';
    return '\n' + html + '\n';
}

// Strip markdown for TTS (plain text)
function stripMarkdown(text) {
    return text
        .replace(/#{1,3} /g, '')
        .replace(/\*\*/g, '').replace(/\*/g, '')
        .replace(/`/g, '')
        .replace(/\|[-| :]+\|/g, '')  // separator rows
        .replace(/\|/g, ' ')
        .replace(/\n+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

// ── Time ──────────────────────────────────────────────────────
function getTime() {
    return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ── TTS ───────────────────────────────────────────────────────
function speakText(text) {
    if (!window.speechSynthesis) return;
    stopSpeaking();
    const plain = stripMarkdown(text);
    currentUtterance = new SpeechSynthesisUtterance(plain);
    currentUtterance.lang = 'en-IN';
    currentUtterance.rate = 0.95;
    currentUtterance.pitch = 1.0;
    // Prefer an Indian English voice if available
    const voices = speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang === 'en-IN') ||
                           voices.find(v => v.lang.startsWith('en'));
    if (preferredVoice) currentUtterance.voice = preferredVoice;
    speechSynthesis.speak(currentUtterance);
}

function stopSpeaking() {
    if (window.speechSynthesis && speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }
    currentUtterance = null;
}

function toggleGlobalTTS() {
    ttsEnabled = !ttsEnabled;
    localStorage.setItem('sf_tts', JSON.stringify(ttsEnabled));
    updateTTSButton();
    if (!ttsEnabled) stopSpeaking();
}

function updateTTSButton() {
    if (!ttsBtnGlobal) return;
    ttsBtnGlobal.title = ttsEnabled ? 'TTS On — click to disable' : 'Enable text-to-speech';
    ttsBtnGlobal.classList.toggle('tts-active', ttsEnabled);
    ttsBtnGlobal.querySelector('.tts-icon').textContent = ttsEnabled ? '🔊' : '🔇';
}

// ── Render Message ────────────────────────────────────────────
function renderMessage(text, role, animate = true) {
    const row = document.createElement('div');
    row.className = `msg-row ${role === 'user' ? 'user-row' : 'bot-row'}`;
    if (!animate) row.style.animation = 'none';

    const avatar = document.createElement('div');
    avatar.className = `msg-avatar ${role === 'user' ? 'user-avatar' : 'bot-avatar'}`;
    avatar.textContent = role === 'user' ? '👤' : '🌿';

    const content = document.createElement('div');
    content.className = 'msg-content';

    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${role === 'user' ? 'user-bubble' : 'bot-bubble'}`;

    if (role === 'user') {
        bubble.textContent = text;
    } else {
        // Clean up followup marker before rendering
        const cleanText = removeFollowupMarker(text);
        let mdHtml = parseMarkdown(cleanText);
        mdHtml = renderScoreBadges(mdHtml);
        bubble.innerHTML = mdHtml;
        // Animate score bars after DOM insertion
        requestAnimationFrame(() => animateScoreBars(bubble));

        // Extract and render follow-up chips
        const chips = extractFollowupChips(text);
        if (chips.length > 0) {
            const chipContainer = document.createElement('div');
            chipContainer.className = 'followup-chips';
            chips.forEach(chip => {
                const btn = document.createElement('button');
                btn.className = 'followup-chip';
                btn.textContent = chip;
                btn.addEventListener('click', () => sendMessage(chip));
                chipContainer.appendChild(btn);
            });
            content.appendChild(chipContainer);
        }
    }

    // Bottom bar for bot messages
    const bottomBar = document.createElement('div');
    bottomBar.className = 'msg-bottom';

    const timeEl = document.createElement('span');
    timeEl.className = 'msg-time';
    timeEl.textContent = getTime();
    bottomBar.appendChild(timeEl);

    // Per-message TTS button for bot messages
    if (role === 'bot') {
        const ttsMsgBtn = document.createElement('button');
        ttsMsgBtn.className = 'msg-tts-btn';
        ttsMsgBtn.title = 'Read aloud';
        ttsMsgBtn.textContent = '🔊';
        let speaking = false;
        ttsMsgBtn.addEventListener('click', () => {
            if (speaking) {
                stopSpeaking();
                ttsMsgBtn.textContent = '🔊';
                speaking = false;
            } else {
                speakText(text);
                ttsMsgBtn.textContent = '⏹';
                speaking = true;
                currentUtterance.onend = () => {
                    ttsMsgBtn.textContent = '🔊';
                    speaking = false;
                };
            }
        });
        bottomBar.appendChild(ttsMsgBtn);

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'msg-tts-btn';
        copyBtn.title = 'Copy response';
        copyBtn.textContent = '📋';
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(stripMarkdown(text)).then(() => {
                copyBtn.textContent = '✓';
                setTimeout(() => copyBtn.textContent = '📋', 1500);
            });
        });
        bottomBar.appendChild(copyBtn);
    }

    content.appendChild(bubble);
    content.appendChild(bottomBar);
    row.appendChild(avatar);
    row.appendChild(content);
    messagesList.appendChild(row);
    scrollToBottom();

    // Auto-speak if TTS enabled
    if (role === 'bot' && ttsEnabled) {
        speakText(text);
    }

    return row;
}

// ── Typing indicator ──────────────────────────────────────────
let typingEl = null;
function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'msg-row typing-row bot-row';
    typingEl.innerHTML = `
        <div class="msg-avatar bot-avatar">🌿</div>
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <span class="typing-label">Thinking…</span>
        </div>`;
    messagesList.appendChild(typingEl);
    scrollToBottom();
}
function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
}

function scrollToBottom() {
    requestAnimationFrame(() => { messagesWrap.scrollTop = messagesWrap.scrollHeight; });
}

// ── Send message ──────────────────────────────────────────────
async function sendMessage(text) {
    if (isProcessing || !text.trim()) return;
    isProcessing = true;
    chatInput.value = '';
    sendBtn.disabled = true;
    stopSpeaking();

    renderMessage(text, 'user');
    showTyping();

    const districtVal = districtFilter.value.trim();
    const payload = {
        message: districtVal && !text.toLowerCase().includes(districtVal.toLowerCase())
            ? `${text} in ${districtVal}`
            : text,
        session_id: SESSION_ID
    };

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        SESSION_ID = data.session_id;
        localStorage.setItem('sf_session', SESSION_ID);
        // Track the district from response for the What-If panel
        if (data.memory) updateContextUI(data.memory);
        if (data.district) {
            lastKnownDistrict = data.district;
            _updateWhatifHint(data.district);
        }
        hideTyping();
        renderMessage(data.text || '❌ No response received.', 'bot');
    } catch (err) {
        hideTyping();
        renderMessage('❌ Connection error. Is the server running on port 5000?', 'bot');
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// ── Soil image upload ─────────────────────────────────────────
async function analyzeSoilImage(file) {
    if (isProcessing) return;
    isProcessing = true;
    sendBtn.disabled = true;
    stopSpeaking();

    const reader = new FileReader();
    reader.onload = e => {
        soilPreviewImg.src = e.target.result;
        soilPreviewName.textContent = `Analyzing: ${file.name}...`;
        soilStrip.style.display = 'flex';
    };
    reader.readAsDataURL(file);

    renderMessage(`📸 Uploaded: ${file.name}`, 'user');
    showTyping();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    const form = new FormData();
    form.append('image', file);
    form.append('session_id', SESSION_ID || '');

    const districtVal = districtFilter.value.trim();
    if (districtVal) {
        form.append('district', districtVal);
    }

    try {
        const res = await fetch('/soil', {
            method: 'POST',
            body: form,
            signal: controller.signal
        });

        const data = await res.json();

        if (data.session_id) {
            SESSION_ID = data.session_id;
            localStorage.setItem('sf_session', SESSION_ID);
        }

        hideTyping();

        if (!res.ok || data.error) {
            renderMessage(`❌ Soil analysis error: ${data.error || 'Unknown error'}`, 'bot');
        } else {
            // Track district from soil response for What-If panel
            if (data.memory) updateContextUI(data.memory);
            if (data.memory && data.memory.district) {
                lastKnownDistrict = data.memory.district;
                _updateWhatifHint(data.memory.district);
            }
            renderMessage(data.text, 'bot');
        }
    } catch (err) {
        hideTyping();
        if (err.name === 'AbortError') {
            renderMessage('❌ Soil analysis timed out. Please try another image.', 'bot');
        } else {
            renderMessage('❌ Soil analysis failed. Please try again.', 'bot');
        }
    } finally {
        clearTimeout(timeout);
        isProcessing = false;
        sendBtn.disabled = false;
        soilStrip.style.display = 'none';
        soilPreviewImg.src = '';
        soilImageInput.value = '';
    }
}


// ── What-If Panel ─────────────────────────────────────────────
function _updateWhatifHint(district) {
    // Update the simulate button label to show which district will be used
    if (!simulateBtn) return;
    if (district) {
        simulateBtn.textContent = `▶ Simulate for ${district}`;
        simulateBtn.title = `Run What-If simulation for ${district}`;
    } else {
        simulateBtn.textContent = '▶ Run Simulation';
        simulateBtn.title = '';
    }
}

function setupWhatIfPanel() {
    if (!whatifIrrSlider || !whatifRainSlider) return;
    whatifIrrSlider.addEventListener('input', () => {
        whatifIrrVal.textContent = whatifIrrSlider.value + '%';
    });
    whatifRainSlider.addEventListener('input', () => {
        whatifRainVal.textContent = '+' + whatifRainSlider.value + ' mm';
    });
}

function sendSimulation() {
    // Resolve district: sidebar filter > last known from chat > nothing
    const districtFromFilter = districtFilter ? districtFilter.value.trim() : '';
    const district = districtFromFilter || lastKnownDistrict || '';

    // If no district is known, ask user to specify one
    if (!district) {
        renderMessage(
            '⚠️ **Which district should I simulate for?**\n\n' +
            'Please type a district name in the **District Filter** box on the left, ' +
            'or ask a question mentioning a district first (e.g. *"Best crops for Coimbatore"*) ' +
            'so I can remember it — then click Simulate again.',
            'bot'
        );
        return;
    }

    const irrBoost  = parseInt(whatifIrrSlider  ? whatifIrrSlider.value  : 0);
    const rainBoost = parseInt(whatifRainSlider ? whatifRainSlider.value : 0);

    let query = 'What if';
    if (irrBoost > 0)  query += ` irrigation improved by ${irrBoost}%`;
    if (rainBoost > 0) query += (irrBoost > 0 ? ' and' : '') + ` rainfall increased by ${rainBoost}mm`;
    if (irrBoost === 0 && rainBoost === 0) query = 'What if irrigation significantly improved';
    query += ` in ${district}`;

    sendMessage(query);
}

// ── Welcome screen ────────────────────────────────────────────
function renderWelcome() {
    messagesList.innerHTML = '';
    renderMessage(INTRO_MESSAGE, 'bot');
}

// ── District autocomplete (sidebar chip filter) ───────────────
function setupDistrictAutocomplete() {
    districtFilter.addEventListener('input', () => {
        const val = districtFilter.value.trim().toLowerCase();
        document.querySelectorAll('.q-chip').forEach(chip => {
            chip.style.display = (!val || chip.textContent.toLowerCase().includes(val)) ? '' : 'none';
        });
    });
    // Also support pressing Enter on district filter to query
    districtFilter.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            const val = districtFilter.value.trim();
            if (val) {
                chatInput.value = `Tell me about ${val}`;
                sendMessage(chatInput.value.trim());
                districtFilter.value = '';
            }
        }
    });
}

// ── Event Listeners ───────────────────────────────────────────
sendBtn.addEventListener('click', () => {
    const msg = chatInput.value.trim();
    if (msg) sendMessage(msg);
});

chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (msg) sendMessage(msg);
    }
});

quickQueries.addEventListener('click', e => {
    const chip = e.target.closest('.q-chip');
    if (chip) { chatInput.value = chip.dataset.query; sendMessage(chip.dataset.query); }
});

messagesList.addEventListener('click', e => {
    const chip = e.target.closest('.welcome-chip');
    if (chip) sendMessage(chip.dataset.query);
});

soilImageInput.addEventListener('change', () => {
    const file = soilImageInput.files[0];
    if (file) analyzeSoilImage(file);
});

removeImgBtn.addEventListener('click', () => {
    soilStrip.style.display = 'none';
    soilPreviewImg.src = ''; soilImageInput.value = '';
});

clearChatBtn.addEventListener('click', async () => {
    stopSpeaking();

    const oldSession = SESSION_ID;

    messagesList.innerHTML = '';
    SESSION_ID = null;
    localStorage.removeItem('sf_session');

    if (oldSession) {
        try {
            await fetch('/reset_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: oldSession })
            });
        } catch (_) {
            // Ignore reset failure on UI side
        }
    }

    clearContextUI();
    renderWelcome();
});


sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

// TTS global toggle
if (ttsBtnGlobal) {
    ttsBtnGlobal.addEventListener('click', toggleGlobalTTS);
    updateTTSButton();
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', e => {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Simulate button
if (simulateBtn) {
    simulateBtn.addEventListener('click', sendSimulation);
}

// Slider listeners
if (whatifPanel) {
    setupWhatIfPanel();
}

// ── Init ──────────────────────────────────────────────────────
renderWelcome();
setupDistrictAutocomplete();
updateContextUI(activeContext);
chatInput.focus();
