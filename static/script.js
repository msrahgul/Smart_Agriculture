/* ════════════════════════════════════════════════════════════
   SmartFarm AI – Chat Frontend Logic
   ════════════════════════════════════════════════════════════ */

// ── Session ID (persisted across page refreshes) ────────────
let SESSION_ID = localStorage.getItem('sf_session') || null;
let pendingSoilFile = null;
let isProcessing = false;

// ── DOM refs ─────────────────────────────────────────────────
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

// ── Markdown → HTML (simple, no dependency) ──────────────────
function parseMarkdown(text) {
    let out = text
        // Headings
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
        .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
        // Bold + italic
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g,   '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g,        '<em>$1</em>')
        // Code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // HR
        .replace(/^---$/gm, '<hr>')
        // Tables
        .replace(/\n(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)*)/g, parseTable)
        // Bullet lists
        .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
        // Numbered lists  
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Line break → <br>
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    return '<p>' + out + '</p>';
}

function parseTable(match, header, sep, body) {
    const headerCells = header.trim().split('|').map(c => c.trim()).filter(Boolean);
    const rows = body.trim().split('\n').filter(r => r.includes('|'));
    let html = '<table><thead><tr>';
    headerCells.forEach(c => { html += `<th>${c}</th>`; });
    html += '</tr></thead><tbody>';
    rows.forEach(row => {
        const cells = row.trim().split('|').map(c => c.trim()).filter(Boolean);
        html += '<tr>';
        cells.forEach(c => { html += `<td>${c}</td>`; });
        html += '</tr>';
    });
    html += '</tbody></table>';
    return '\n' + html + '\n';
}

// ── Time helper ───────────────────────────────────────────────
function getTime() {
    return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ── Render a message bubble ───────────────────────────────────
function renderMessage(text, role) {
    const row = document.createElement('div');
    row.className = `msg-row ${role === 'user' ? 'user-row' : 'bot-row'}`;

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
        bubble.innerHTML = parseMarkdown(text);
    }

    const time = document.createElement('div');
    time.className = 'msg-time';
    time.textContent = getTime();

    content.appendChild(bubble);
    content.appendChild(time);
    row.appendChild(avatar);
    row.appendChild(content);
    messagesList.appendChild(row);
    scrollToBottom();
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
        </div>`;
    messagesList.appendChild(typingEl);
    scrollToBottom();
}
function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
}

// ── Auto-scroll ───────────────────────────────────────────────
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesWrap.scrollTop = messagesWrap.scrollHeight;
    });
}

// ── Send a chat message ───────────────────────────────────────
async function sendMessage(text) {
    if (isProcessing || !text.trim()) return;
    isProcessing = true;
    chatInput.value = '';
    sendBtn.disabled = true;

    renderMessage(text, 'user');
    showTyping();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_id: SESSION_ID }),
        });
        const data = await res.json();
        SESSION_ID = data.session_id;
        localStorage.setItem('sf_session', SESSION_ID);

        hideTyping();
        renderMessage(data.text || '❌ No response received.', 'bot');
    } catch (err) {
        hideTyping();
        renderMessage('❌ Connection error. Please make sure the server is running.', 'bot');
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// ── Upload and analyze soil image ─────────────────────────────
async function analyzeSoilImage(file) {
    if (isProcessing) return;
    isProcessing = true;
    sendBtn.disabled = true;

    // Show preview strip
    const reader = new FileReader();
    reader.onload = e => {
        soilPreviewImg.src = e.target.result;
        soilPreviewName.textContent = `Analyzing: ${file.name}`;
        soilStrip.style.display = 'flex';
    };
    reader.readAsDataURL(file);

    // Show user message
    renderMessage(`🖼️ Uploaded soil image: ${file.name} — analyzing…`, 'user');
    showTyping();

    const form = new FormData();
    form.append('image', file);
    const districtVal = districtFilter.value.trim();
    if (districtVal) form.append('district', districtVal);

    try {
        const res = await fetch('/soil', { method: 'POST', body: form });
        const data = await res.json();
        hideTyping();
        if (data.error) {
            renderMessage(`❌ Soil analysis failed: ${data.error}`, 'bot');
        } else {
            renderMessage(data.text, 'bot');
        }
    } catch (err) {
        hideTyping();
        renderMessage('❌ Soil analysis failed. Please try again.', 'bot');
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        soilStrip.style.display = 'none';
        soilPreviewImg.src = '';
        soilImageInput.value = '';
        pendingSoilFile = null;
    }
}

// ── Welcome screen ────────────────────────────────────────────
function renderWelcome() {
    const card = document.createElement('div');
    card.className = 'welcome-card';
    card.innerHTML = `
        <div class="welcome-icon">🌿</div>
        <h2>Smart Farming AI</h2>
        <p>Your intelligent agricultural assistant for <strong>Tamil Nadu</strong>.<br>
        Ask me anything about crops, rainfall, wages, irrigation, pest risks, and more.</p>
        <div class="welcome-chips">
            <button class="welcome-chip" data-query="Best crops for Coimbatore?">🌾 Best crops for Coimbatore</button>
            <button class="welcome-chip" data-query="Rainfall in Salem?">🌧️ Rainfall in Salem</button>
            <button class="welcome-chip" data-query="Agricultural wages in Madurai?">💰 Wages in Madurai</button>
            <button class="welcome-chip" data-query="Pest risk in Dharmapuri?">🐛 Pest risk — Dharmapuri</button>
            <button class="welcome-chip" data-query="Overview of Erode district?">📋 Overview of Erode</button>
        </div>
    `;
    messagesList.appendChild(card);
}

// ── District Filter → autocomplete for soil endpoint ──────────
function setupDistrictAutocomplete() {
    districtFilter.addEventListener('input', () => {
        const val = districtFilter.value.trim().toLowerCase();
        // Simple visual filter on quick chips
        document.querySelectorAll('.q-chip').forEach(chip => {
            chip.style.display = val === '' || chip.textContent.toLowerCase().includes(val) ? '' : 'none';
        });
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

// Quick query chips
quickQueries.addEventListener('click', e => {
    const chip = e.target.closest('.q-chip');
    if (chip) {
        const query = chip.dataset.query;
        chatInput.value = query;
        sendMessage(query);
    }
});

// Welcome chips (delegated)
messagesList.addEventListener('click', e => {
    const chip = e.target.closest('.welcome-chip');
    if (chip) {
        const query = chip.dataset.query;
        sendMessage(query);
    }
});

// Soil image upload
soilImageInput.addEventListener('change', () => {
    const file = soilImageInput.files[0];
    if (file) analyzeSoilImage(file);
});

// Remove soil preview
removeImgBtn.addEventListener('click', () => {
    soilStrip.style.display = 'none';
    soilPreviewImg.src = '';
    soilImageInput.value = '';
    pendingSoilFile = null;
});

// Clear chat
clearChatBtn.addEventListener('click', () => {
    messagesList.innerHTML = '';
    SESSION_ID = null;
    localStorage.removeItem('sf_session');
    renderWelcome();
});

// Sidebar toggle (mobile)
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', e => {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// ── Initialize ────────────────────────────────────────────────
renderWelcome();
setupDistrictAutocomplete();
chatInput.focus();
