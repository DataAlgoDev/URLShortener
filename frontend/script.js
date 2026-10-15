// static/script.js
const form = document.getElementById('shortenForm');
const urlInput = document.getElementById('urlInput');
const historyContainer = document.getElementById('historyContainer');
const linksList = document.getElementById('linksList');
const errorBox = document.getElementById('errorBox');

const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('usernameInput');
const passwordInput = document.getElementById('passwordInput');
const loginStatus = document.getElementById('loginStatus');

// URL Shortening Submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.classList.add('hidden');

    const longUrl = urlInput.value.trim();

    try {
        const response = await fetch('/shorten/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: longUrl })
        });

        if (!response.ok) {
            const errData = await response.json();
        // Check if it's a rate limit error (Status 429)
        if (response.status === 429) {
            // errData.detail will contain: "Rate limit exceeded: 3 per 1 second"
            throw new Error(errData.detail || "Too many requests!! Pleas slow down");
        }
        throw new Error(errData.detail || 'Failed to shorten URL');
        }

        const data = await response.json();
        
        historyContainer.classList.remove('hidden');
        const uniqueId = 'copy-btn-' + Math.random().toString(36).substring(2, 9);

        const linkCard = document.createElement('div');
        linkCard.className = 'bg-slate-900/80 p-3 rounded-xl border border-slate-700/80 space-y-2 transition-all';
        linkCard.innerHTML = `
            <div class="text-xs text-slate-400 truncate" title="${escapeHtml(longUrl)}">
                <span class="text-slate-500 font-semibold">Original:</span> ${escapeHtml(longUrl)}
            </div>
            <div class="flex items-center justify-between bg-slate-900 p-2.5 rounded-lg border border-slate-700">
                <a href="${data.short_url}" target="_blank" class="text-blue-400 hover:underline text-sm truncate mr-2 font-mono">
                    ${data.short_url}
                </a>
                <button 
                    id="${uniqueId}"
                    onclick="copySessionLink('${data.short_url}', '${uniqueId}')" 
                    class="flex items-center justify-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition min-w-[64px] cursor-pointer"
                >
                    <span>Copy</span>
                </button>
            </div>
        `;

        linksList.prepend(linkCard);
        urlInput.value = '';

    } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove('hidden');
    }
});

// Login Form Submission Handler
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginStatus.classList.add('hidden');

    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    // Placeholder login behavior (hook up to your FastAPI token/auth endpoint when ready)
    if (username && password) {
        loginStatus.textContent = `Welcome back, ${username}! (Auth stub)`;
        loginStatus.className = 'mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-xs';
        loginStatus.classList.remove('hidden');
        passwordInput.value = '';
    } else {
        loginStatus.textContent = 'Please enter credentials.';
        loginStatus.className = 'mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs';
        loginStatus.classList.remove('hidden');
    }
});

// Individual copy handler for session links
function copySessionLink(urlText, btnId) {
    const btn = document.getElementById(btnId);
    
    const checkmarkSvg = `
        <svg class="w-4 h-4 text-white animate-scale-in" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
        </svg>
    `;

    navigator.clipboard.writeText(urlText).then(() => {
        btn.innerHTML = checkmarkSvg;
        btn.classList.remove('bg-slate-800', 'hover:bg-slate-700', 'border-slate-600');
        btn.classList.add('bg-emerald-600', 'border-emerald-500');

        setTimeout(() => {
            btn.innerHTML = '<span>Copy</span>';
            btn.classList.remove('bg-emerald-600', 'border-emerald-500');
            btn.classList.add('bg-slate-800', 'hover:bg-slate-700', 'border-slate-600');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

// Helper to prevent HTML injection
function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}