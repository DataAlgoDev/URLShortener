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
                throw new Error(errData.detail || "Too many requests!! Please slow down");
            }
            throw new Error(errData.detail || 'Failed to shorten URL');
        }

        const data = await response.json();
        
        historyContainer.classList.remove('hidden');
        const uniqueId = 'copy-btn-' + Math.random().toString(36).substring(1, 9);
        const uniqueIdQR = 'qr-btn-' + Math.random().toString(36).substring(1, 9);

        const linkCard = document.createElement('div');
        linkCard.className = 'bg-slate-900/80 p-3 rounded-xl border border-slate-700/80 space-y-2 transition-all';
        linkCard.innerHTML = `
            <div class="text-xs text-yellow-400 truncate" title="${escapeHtml(longUrl)}">
                <span class="text-slate-500 font-semibold">Original:</span> ${escapeHtml(longUrl)}
            </div>
            <div class="flex items-center justify-between bg-slate-900 p-2.5 rounded-lg border border-slate-700">
                <a href="${data.short_url}" target="_blank" class="text-blue-400 hover:underline text-sm truncate mr-2 font-mono">
                    ${data.short_url}
                </a>

                <div class="flex items-center space-x-2">
                    <!-- QR Code Download Button -->
                    <button 
                        id="${uniqueIdQR}"
                        onclick="downloadQrCode('${data.short_url}', '${uniqueIdQR}')" 
                        class="flex items-center justify-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition cursor-pointer"
                        title="Download QR Code"
                    >
                        <svg class="w-3.5 h-3.5 mr-1 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"></path>
                        </svg>
                        <span>QR</span>
                    </button>
                    
                    <!-- Copy Button -->
                    <button 
                        id="${uniqueId}"
                        onclick="copySessionLink('${data.short_url}', '${uniqueId}')" 
                        class="flex items-center justify-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition min-w-[64px] cursor-pointer"
                        title="Copy to clipboard"
                    >
                        <span>Copy</span>
                    </button>
                </div>
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

// Download QR Code Handler
async function downloadQrCode(urlText, btnId) {
    const btn = document.getElementById(btnId);
    const originalContent = btn.innerHTML;

    try {
        // Show loading state on button
        btn.innerHTML = `<span class="text-xs">...</span>`;
        
        // Use a reliable free QR generation API to fetch image blob
        const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(urlText)}&qzone=4`;
        const response = await fetch(qrApiUrl);
        const blob = await response.blob();

        // Create a temporary anchor element to trigger the browser download
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = 'qrcode.png';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);

        // Success state feedback
        btn.innerHTML = `
            <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
            </svg>
        `;
    } catch (err) {
        console.error('Failed to download QR code:', err);
        alert('Could not download QR code.');
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalContent;
        }, 2000);
    }
}

// Helper to prevent HTML injection
function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}