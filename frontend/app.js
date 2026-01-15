const API_URL = "http://localhost:8000";
let token = localStorage.getItem("token");
let currentUserType = "";

// Init
document.addEventListener("DOMContentLoaded", () => {
    if (token) {
        showDashboard();
    } else {
        showAuthTab('login');
    }
});

// Auth Logic
async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    try {
        const res = await fetch(`${API_URL}/auth/token`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) throw new Error("Login failed");
        
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem("token", token);
        showDashboard();
    } catch (e) {
        document.getElementById('auth-msg').innerText = e.message;
        document.getElementById('auth-msg').style.color = "red";
    }
}

async function register() {
    const username = document.getElementById('reg-username').value;
    const password = document.getElementById('reg-password').value;
    const type = document.getElementById('reg-type').value;
    
    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, user_type: type })
        });
        
        if (!res.ok) throw new Error("Registration failed (username taken?)");
        
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem("token", token);
        showDashboard();
    } catch (e) {
        document.getElementById('auth-msg').innerText = e.message;
        document.getElementById('auth-msg').style.color = "red";
    }
}

function logout() {
    localStorage.removeItem("token");
    token = null;
    location.reload();
}

// Navigation
function showAuthTab(tab) {
    document.querySelectorAll('.auth-form').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    if (tab === 'login') {
        document.getElementById('login-form').classList.remove('hidden');
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
    } else {
        document.getElementById('register-form').classList.remove('hidden');
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    // Find button to highlight - simplistic way
    const buttons = document.querySelectorAll('.nav-btn');
    if(tabName === 'profile') buttons[0].classList.add('active');
    if(tabName === 'documents') buttons[1].classList.add('active');
    if(tabName === 'schemes') buttons[2].classList.add('active');

    if (tabName === 'profile') loadProfile();
    if (tabName === 'documents') loadDocuments();
    if (tabName === 'schemes') loadSchemes();
}

async function showDashboard() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('dashboard-section').classList.remove('hidden');
    await loadProfile(); // to get user type
    switchTab('profile');
}

// Profile
async function loadProfile() {
    const res = await fetch(`${API_URL}/profile/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    
    if (data.full_name) {
        document.getElementById('prof-name').value = data.full_name || "";
        document.getElementById('prof-dob').value = data.dob || "";
        document.getElementById('prof-state').value = data.state || "";
        document.getElementById('prof-district').value = data.district || "";
        document.getElementById('prof-income').value = data.income || "";
        document.getElementById('prof-category').value = data.category || "";
        document.getElementById('prof-aadhaar').value = data.aadhaar_number || "";
        
        // Populate Student/Farmer fields if they exist
        // In a real app we'd toggle visibility based on user.user_type but for now we assume fields are available
    }
}

async function saveProfile() {
    const profile = {
        full_name: document.getElementById('prof-name').value,
        dob: document.getElementById('prof-dob').value,
        state: document.getElementById('prof-state').value,
        district: document.getElementById('prof-district').value,
        income: parseFloat(document.getElementById('prof-income').value) || 0,
        category: document.getElementById('prof-category').value,
        aadhaar_number: document.getElementById('prof-aadhaar').value
    };

    const res = await fetch(`${API_URL}/profile/`, {
        method: 'PUT',
        headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(profile)
    });

    if (res.ok) alert("Profile Saved!");
}

// Documents
async function loadDocuments() {
    const res = await fetch(`${API_URL}/documents/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const docs = await res.json();
    
    const container = document.getElementById('documents-list');
    container.innerHTML = "";
    
    docs.forEach(doc => {
        const div = document.createElement('div');
        div.className = `card ${doc.status}`;
        
        // Check if extraction failed (simple check for "failed" in msg or "Mismatch" without valid data)
        // We'll just show the Edit button always.
        
        div.innerHTML = `
            <div style="display:flex; justify-content:space-between;">
                <strong>${doc.name}</strong>
                <span class="status-badge status-${doc.status}">${doc.status.toUpperCase()}</span>
            </div>
            ${doc.validation_message ? `<p style="color: red; font-size: 13px;">${doc.validation_message}</p>` : ''}
            
            <div style="margin-top: 10px; display: flex; gap: 5px;">
                <button onclick="deleteDoc(${doc.id})" style="background: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">Delete</button>
                <button onclick="openEditDoc(${doc.id}, '${doc.name}')" style="background: #3b82f6; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">Edit / Verify Manually</button>
            </div>
        `;
        container.appendChild(div);
    });
}

async function deleteDoc(id) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    
    const res = await fetch(`${API_URL}/documents/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (res.ok) {
        loadDocuments();
    } else {
        alert("Failed to delete document");
    }
}

async function openEditDoc(id, currentName) {
    // Simple Prompt-based edit flow for MVP
    const newName = prompt("Edit Document Name:", currentName);
    if (newName === null) return;
    
    const newFullName = prompt("Enter Name exactly as in Document:", "");
    if (newFullName === null) return;

    const newDob = prompt("Enter DOB (YYYY-MM-DD):", "");
    if (newDob === null) return;
    
    const newId = prompt("Enter ID Number (if any):", "");
    if (newId === null) return;
    
    const updateData = {
        name: newName,
        full_name: newFullName,
        dob: newDob,
        id_number: newId
    };

    const res = await fetch(`${API_URL}/documents/${id}`, {
        method: 'PUT',
        headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json' 
        },
        body: JSON.stringify(updateData)
    });
    
    if (res.ok) {
        alert("Document Updated & Verified!");
        loadDocuments();
    } else {
        alert("Failed to update document");
    }
}

async function uploadDocument() {
    const name = document.getElementById('doc-name-input').value;
    const fileInput = document.getElementById('doc-file-input');
    
    if (!name || fileInput.files.length === 0) return alert("Select file and enter name");

    const formData = new FormData();
    formData.append("name", name);
    formData.append("file", fileInput.files[0]);

    const res = await fetch(`${API_URL}/documents/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
    });

    if (res.ok) {
        alert("Uploaded & Verified!");
        loadDocuments();
    } else {
        const err = await res.json();
        alert("Error: " + err.detail);
    }
}

// Schemes
async function loadSchemes() {
    const res = await fetch(`${API_URL}/schemes/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    renderSchemes(await res.json());
}

async function discoverSchemes() {
    const btn = document.getElementById('discover-btn');
    btn.innerText = "Searching...";
    btn.disabled = true;
    
    try {
        const res = await fetch(`${API_URL}/schemes/discover`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        renderSchemes(await res.json());
    } catch(e) {
        alert("Discovery failed");
    } finally {
        btn.innerText = "Discover More Schemes (AI)";
        btn.disabled = false;
    }
}

async function downloadKit(schemeId) {
    const res = await fetch(`${API_URL}/schemes/${schemeId}/apply`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "Application_Kit.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
    } else {
        alert("Failed to generate kit");
    }
}

function goToUpload(docName) {
    switchTab('documents');
    document.getElementById('doc-name-input').value = docName;
    alert(`Please upload: ${docName}`);
}

function renderSchemes(schemes) {
    const eligibleContainer = document.getElementById('eligible-schemes-list');
    const ineligibleContainer = document.getElementById('ineligible-schemes-list');
    
    eligibleContainer.innerHTML = "";
    ineligibleContainer.innerHTML = "";
    
    schemes.forEach(s => {
        const div = document.createElement('div');
        div.className = "card scheme-card";
        
        let actionBtn = "";
        if (s.is_eligible) {
            actionBtn = `
                <div style="display:flex; gap:10px; margin-top:10px;">
                    <a href="${s.portal_url}" target="_blank"><button class="apply-btn">Visit Portal</button></a>
                    <button class="apply-btn" style="background:#4f46e5" onclick="downloadKit(${s.id})">Download Application Kit (PDF)</button>
                </div>`;
        } else {
            if (s.missing_documents.length > 0) {
                // Take the first missing doc as a suggestion
                const firstMissing = s.missing_documents[0];
                actionBtn = `<button class="upload-req-btn" onclick="goToUpload('${firstMissing}')">Upload ${firstMissing}</button>`;
            } else {
                actionBtn = `<span style="color: #999;">Not Eligible</span>`;
            }
        }
        
        div.innerHTML = `
            <h4>${s.name}</h4>
            <p>${s.description}</p>
            <p><strong>Benefits:</strong> ${s.benefits}</p>
            ${!s.is_eligible ? `<p class="missing-docs">Reason: ${s.reason}</p>` : ''}
            ${s.missing_documents.length > 0 ? `<p class="missing-docs">Missing: ${s.missing_documents.join(", ")}</p>` : ''}
            ${actionBtn}
        `;
        
        if (s.is_eligible) {
            eligibleContainer.appendChild(div);
        } else {
            ineligibleContainer.appendChild(div);
        }
    });
}