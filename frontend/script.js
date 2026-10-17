// --- Elements for Home / Guest Page & Dashboard ---
const guestShortenForm = document.getElementById('GuestShortenForm');
const userShortenForm = document.getElementById('UserShortenForm');
const urlInput = document.getElementById('urlInput');
const historyContainer = document.getElementById('historyContainer');
const linksList = document.getElementById('linksList');
const errorBox = document.getElementById('errorBox');

// --- Account / Auth Elements ---
const usernameInput = document.getElementById('usernameInput');
const passwordInput = document.getElementById('passwordInput');
const loginStatus = document.getElementById('loginStatus');
const signUpBtn = document.getElementById('signUpBtn');
const signInBtn = document.getElementById('signInBtn');
const logoutBtn = document.getElementById('logoutBtn');

// --- Reusable URL Shortening Handler ---
async function handleUrlShorten(e, endpointUrl) {
    e.preventDefault();
    if (errorBox) errorBox.classList.add('hidden');

    const longUrl = urlInput ? urlInput.value.trim() : '';
    if (!longUrl) return;

    try {
        const response = await fetch(endpointUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: longUrl }),
            credentials: 'include' // Ensures cookies (session_id) are sent for authenticated users
        });

        if (!response.ok) {
            const errData = await response.json();
            if (response.status === 429) {
                throw new Error(errData.detail || "Too many requests!! Please slow down");
            }
            throw new Error(errData.detail || 'Failed to shorten URL');
        }

        const data = await response.json();
        
        if (historyContainer) historyContainer.classList.remove('hidden');
        const uniqueId = 'copy-btn-' + Math.random().toString(36).substring(1, 9);
        const uniqueIdQR = 'qr-btn-' + Math.random().toString(36).substring(1, 9);

        const shortUrl = data.short_url || `http://localhost:8000/${data.uid}`;

        const linkCard = document.createElement('div');
        linkCard.className = 'bg-slate-900/80 p-3 rounded-xl border border-slate-700/80 space-y-2 transition-all';
        linkCard.innerHTML = `
            <div class="text-xs text-yellow-400 truncate" title="${escapeHtml(longUrl)}">
                <span class="text-slate-500 font-semibold">Original:</span> ${escapeHtml(longUrl)}
            </div>
            <div class="flex items-center justify-between bg-slate-900 p-2.5 rounded-lg border border-slate-700">
                <a href="${shortUrl}" target="_blank" class="text-blue-400 hover:underline text-sm truncate mr-2 font-mono">
                    ${shortUrl}
                </a>
                <div class="flex items-center space-x-2">
                    <button id="${uniqueIdQR}" onclick="downloadQrCode('${shortUrl}', '${uniqueIdQR}')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition cursor-pointer" title="Download QR Code"><span>QR</span></button>
                    <button id="${uniqueId}" onclick="copySessionLink('${shortUrl}', '${uniqueId}')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition min-w-[64px] cursor-pointer" title="Copy"><span>Copy</span></button>
                </div>
            </div>
        `;

        if (linksList) linksList.prepend(linkCard);
        if (urlInput) urlInput.value = '';

    } catch (err) {
        if (errorBox) {
            errorBox.textContent = err.message;
            errorBox.classList.remove('hidden');
        }
    }
}

// Bind Guest Form -> hits /guest/shorten/
if (guestShortenForm) {
    guestShortenForm.addEventListener('submit', (e) => handleUrlShorten(e, '/guest/shorten/'));
}

// Bind User Dashboard Form -> hits /users/shorten/
if (userShortenForm) {
    userShortenForm.addEventListener('submit', (e) => handleUrlShorten(e, '/users/shorten/'));
}


// --- Sign In Handler ---
if (signInBtn) {
    signInBtn.addEventListener('click', async () => {
        if (loginStatus) loginStatus.classList.add('hidden');

        const username = usernameInput ? usernameInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value.trim() : '';

        if (!username || !password) {
            if (loginStatus) {
                loginStatus.textContent = 'Fields are not filled. Please provide both username and password.';
                loginStatus.className = 'mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs text-center';
                loginStatus.classList.remove('hidden');
            }
            return;
        }

        try {
            const response = await fetch('/users/signin/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: username, password: password }),
                credentials: 'include'
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to sign in');
            }

            // Success: Redirect to dashboard
            window.location.href = '/users/dashboard/';

        } catch (err) {
            if (loginStatus) {
                loginStatus.textContent = err.message;
                loginStatus.className = 'mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs text-center';
                loginStatus.classList.remove('hidden');
            }
        }
    });
}


// --- Sign Up Handler ---
if (signUpBtn) {
    signUpBtn.addEventListener('click', async () => {
        if (loginStatus) loginStatus.classList.add('hidden');

        const username = usernameInput ? usernameInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value.trim() : '';

        if (!username || !password) {
            if (loginStatus) {
                loginStatus.textContent = 'Fields are not filled. Please provide both username and password.';
                loginStatus.className = 'mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs text-center';
                loginStatus.classList.remove('hidden');
            }
            return;
        }

        try {
            const response = await fetch('/users/signup/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: username, password: password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to sign up');
            }

            if (loginStatus) {
                loginStatus.textContent = `Account created successfully for "${data.user_name}"! You can now sign in.`;
                loginStatus.className = 'mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-xs text-center';
                loginStatus.classList.remove('hidden');
            }
            
            if (usernameInput) usernameInput.value = '';
            if (passwordInput) passwordInput.value = '';

        } catch (err) {
            if (loginStatus) {
                loginStatus.textContent = err.message;
                loginStatus.className = 'mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs text-center';
                loginStatus.classList.remove('hidden');
            }
        }
    });
}


// --- Dashboard Initialization & API /api/me Handling ---
document.addEventListener('DOMContentLoaded', async () => {
    const accountUsernameEl = document.getElementById('accountUsername');
    const userDataBoxEl = document.getElementById('userDataBox');

    // Only run if we are on the dashboard page and these elements exist
    if (!userDataBoxEl) return;

    try {
        const response = await fetch('/api/me/', {
            method: 'GET',
            credentials: 'include' // Sends the HttpOnly session cookie
        });

        if (!response.ok) {
            // If session is invalid or expired, redirect back to login
            window.location.href = '/';
            return;
        }

        const data = await response.json();

        // Check if the response is an array of records (links)
        if (Array.isArray(data)) {
            if (accountUsernameEl) {
                accountUsernameEl.textContent = data.length > 0 ? ` #${data[0]}` : 'Active User';
            }

            if (data.length === 0) {
                userDataBoxEl.innerHTML = `<p class="text-slate-500 text-center py-4 text-xs">No short URLs found yet.</p>`;
                return;
            }

            // Render table with columns: Clicks, Short URL, Original URL
            let tableHTML = `
                <div class="overflow-x-auto overflow-y-auto pr-1">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="border-b border-slate-700 text-slate-400 bg-slate-900 sticky top-0 z-10">
                                <th class="p-3 text-center">Clicks</th>
                                <th class="p-3">Short URL</th>
                                <th class="p-3">Original URL</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
            `;

            data[1].forEach(item => {
                const shortUrl = item.s_url || `http://localhost:8000/${item.uid}`;
                tableHTML += `
                    <tr class="hover:bg-slate-800/60 transition">
                        <td class="p-3 text-emerald-400 font-semibold text-center">
                            ${item.clicks}
                        </td>
                        <td class="p-3 font-mono text-blue-400 whitespace-nowrap">
                            <a href="${shortUrl}" target="_blank" class="hover:underline" title="${shortUrl}">${shortUrl}</a>
                        </td>
                        <td class="p-3 max-w-[180px] truncate text-slate-300" title="${escapeHtml(item.l_url)}">
                            ${escapeHtml(item.l_url)}
                        </td>
                    </tr>
                `;
            });

            tableHTML += `
                        </tbody>
                    </table>
                </div>
            `;

            userDataBoxEl.innerHTML = tableHTML;
        } else {
            // Object fallback
            if (accountUsernameEl && data.username) {
                accountUsernameEl.textContent = data.username;
            }
            userDataBoxEl.innerHTML = '';
            for (const [key, value] of Object.entries(data)) {
                const row = document.createElement('div');
                row.className = 'flex justify-between py-1 border-b border-slate-800';
                row.innerHTML = `<span class="text-blue-400 font-semibold">${key}:</span> <span class="text-slate-100 truncate ml-2">${value}</span>`;
                userDataBoxEl.appendChild(row);
            }
        }

    } catch (err) {
        console.error("Failed to fetch user data:", err);
        userDataBoxEl.innerHTML = `<span class="text-rose-400 text-xs">Error loading user records.</span>`;
    }
});


// --- Logout Handler ---
if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
        try {
            await fetch('/users/logout/', { 
                method: 'POST',
                credentials: 'include' 
            });
        } catch (e) {
            console.error("Logout error:", e);
        } finally {
            // 2. Clear frontend client-side storage
            localStorage.clear();
            sessionStorage.clear();

            // 4. Redirect back to login/home
            window.location.href = '/';
        }
    });
}


// --- Helper Functions ---
function copySessionLink(urlText, btnId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    
    navigator.clipboard.writeText(urlText).then(() => {
        // Change button to green with tick mark
        const originalContent = btn.innerHTML;
        btn.innerHTML = '<span>✓</span>';
        btn.className = 'px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded border border-emerald-500 transition min-w-[64px] cursor-pointer';

        // Revert back after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.className = 'px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-slate-600 transition min-w-[64px] cursor-pointer';
        }, 2000);
    });
}

async function downloadQrCode(urlText, btnId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    const originalContent = btn.innerHTML;
    try {
        btn.innerHTML = `<span>...</span>`;
        const res = await fetch(`https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(urlText)}`);
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = 'qrcode.png';
        a.click();
    } finally {
        btn.innerHTML = originalContent;
    }
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}