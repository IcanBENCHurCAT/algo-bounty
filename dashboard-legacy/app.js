// State Management
let state = {
  address: localStorage.getItem("bounty_address") || null,
  jwt: localStorage.getItem("bounty_jwt") || null,
  karma: parseInt(localStorage.getItem("bounty_karma")) || 25,
  activeTab: "board",
  bounties: [],
  selectedBountyId: null,
  challenge: null,
  notifications: []
};

// API Base URL
const API_BASE = window.location.origin;

// Toast Utility
function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.innerText = msg;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 4000);
}

// Format Address helper
function formatAddress(addr) {
  if (!addr) return "";
  return addr.substring(0, 6) + "..." + addr.substring(addr.length - 4);
}

// Headers builder
function getHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (state.jwt) {
    headers["Authorization"] = `Bearer ${state.jwt}`;
  }
  return headers;
}

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  initUI();
  fetchBounties();
  setupSSE();
  
  if (state.address && state.jwt) {
    showLoggedInState();
    fetchNotifications();
    fetchMyBounties();
  }
});

// Setup tab navigation and event listeners
function initUI() {
  // Tab Switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const tab = e.target.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  // Connect Wallet
  document.getElementById("btn-connect").addEventListener("click", () => {
    // Open Sign Challenge Modal with mock credential
    openSignModal();
  });

  // Disconnect
  document.getElementById("btn-disconnect").addEventListener("click", () => {
    logout();
  });

  // Modal Sign Cancel
  document.getElementById("btn-sign-cancel").addEventListener("click", () => {
    document.getElementById("modal-sign").classList.add("hidden");
  });

  // Sign Challenge Action
  document.getElementById("btn-sign-approve").addEventListener("click", () => {
    verifyAuth();
  });

  // Filter Event Listeners
  document.getElementById("filter-status").addEventListener("change", fetchBounties);
  document.getElementById("filter-karma").addEventListener("input", fetchBounties);
  document.getElementById("filter-hitm").addEventListener("change", fetchBounties);

  // Submit Bounty Form
  document.getElementById("form-create-bounty").addEventListener("submit", createBounty);

  // Submit Work Modal Cancel
  document.getElementById("btn-submit-cancel").addEventListener("click", () => {
    document.getElementById("modal-submit").classList.add("hidden");
  });

  // Submit Work Form Action
  document.getElementById("form-submit-work").addEventListener("submit", submitWork);
}

function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tab);
  });
  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.toggle("active", content.id === `tab-${tab}`);
  });

  if (tab === "dashboard") {
    fetchNotifications();
    fetchMyBounties();
  }
}

// SSE Connection
function setupSSE() {
  const eventSource = new EventSource(`${API_BASE}/api/v1/events`);
  
  eventSource.addEventListener("bounty.created", (e) => {
    const data = JSON.parse(e.data);
    showToast(`🎯 New Bounty Created: ${data.bounty_id}`);
    fetchBounties();
  });

  eventSource.addEventListener("bounty.claimed", (e) => {
    const data = JSON.parse(e.data);
    showToast(`🤝 Bounty Claimed: ${data.bounty_id} by worker`);
    fetchBounties();
    if (state.activeTab === "dashboard") fetchMyBounties();
  });

  eventSource.addEventListener("bounty.submitted", (e) => {
    const data = JSON.parse(e.data);
    showToast(`🚀 Work Submitted for Bounty: ${data.bounty_id}`);
    fetchBounties();
    if (state.activeTab === "dashboard") {
      fetchMyBounties();
      fetchNotifications();
    }
  });

  eventSource.addEventListener("bounty.approved", (e) => {
    const data = JSON.parse(e.data);
    showToast(`🎉 Bounty Approved! Payout released for: ${data.bounty_id}`);
    fetchBounties();
    if (state.activeTab === "dashboard") {
      fetchMyBounties();
      fetchNotifications();
    }
  });
}

// Fetch Bounties List
async function fetchBounties() {
  const status = document.getElementById("filter-status").value;
  const karma = document.getElementById("filter-karma").value;
  const hitm = document.getElementById("filter-hitm").value;

  let query = `?1=1`;
  if (status) query += `&status=${status}`;
  if (karma) query += `&min_karma=${karma}`;
  if (hitm) query += `&hitm=${hitm}`;

  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties${query}`);
    const data = await res.json();
    state.bounties = data.bounties;
    renderBountiesGrid();
    updateStats(data.bounties);
  } catch (err) {
    showToast("Error loading bounties list");
  }
}

function renderBountiesGrid() {
  const grid = document.getElementById("bounties-grid");
  grid.innerHTML = "";

  if (state.bounties.length === 0) {
    grid.innerHTML = `<div class="loader">No bounties found matching filters.</div>`;
    return;
  }

  state.bounties.forEach(b => {
    const card = document.createElement("div");
    card.className = "bounty-card glass";

    // Setup action buttons based on status & roles
    let actionBtn = "";
    if (b.status === "open") {
      if (state.address && b.creator !== state.address) {
        actionBtn = `<button class="btn btn-primary" onclick="claimBounty('${b.bounty_id}')">🤝 Claim Bounty</button>`;
      } else if (!state.address) {
        actionBtn = `<button class="btn btn-primary" onclick="openSignModal()">🔌 Connect to Claim</button>`;
      }
    } else if (b.status === "claimed" && b.worker === state.address) {
      actionBtn = `<button class="btn btn-primary" onclick="openSubmitModal('${b.bounty_id}')">🚀 Submit Solution</button>`;
    } else if (b.status === "submitted" && b.creator === state.address) {
      actionBtn = `
        <div class="bounty-actions">
          <button class="btn btn-primary" onclick="approveBounty('${b.bounty_id}')">✅ Approve</button>
          <button class="btn btn-secondary" onclick="rejectBounty('${b.bounty_id}')">❌ Reject</button>
        </div>
      `;
    } else if (b.status === "rejected" && b.worker === state.address) {
      actionBtn = `
        <div class="bounty-actions">
          <button class="btn btn-primary" onclick="openSubmitModal('${b.bounty_id}')">🚀 Submit Revision</button>
          <button class="btn btn-secondary" onclick="disputeBounty('${b.bounty_id}')">⚠️ Dispute</button>
        </div>
      `;
    }

    card.innerHTML = `
      <div>
        <div class="bounty-header">
          <span class="bounty-badge badge-${b.status}">${b.status}</span>
          <span class="bounty-amount">${b.amount / 1_000_000} ALGO</span>
        </div>
        <h3>${b.description.split('\n')[0]}</h3>
        <p>${b.description.substring(0, 100)}${b.description.length > 100 ? '...' : ''}</p>
        <div class="bounty-meta">
          <div class="bounty-meta-item">📍 Repo: <strong>${b.repo_url.replace('https://github.com/', '')}</strong></div>
          <div class="bounty-meta-item">👤 Creator: <strong>${formatAddress(b.creator)}</strong></div>
          <div class="bounty-meta-item">🛡️ Min Karma: <strong>${b.karma_requirement}</strong></div>
          <div class="bounty-meta-item">⚙️ HITM: <strong>${b.hitm ? 'Yes' : 'No'}</strong></div>
          ${b.worker ? `<div class="bounty-meta-item">👷 Worker: <strong>${formatAddress(b.worker)}</strong></div>` : ''}
        </div>
      </div>
      <div>
        ${actionBtn}
      </div>
    `;
    grid.appendChild(card);
  });
}

function updateStats(bounties) {
  const totalTVL = bounties.filter(b => b.status !== "closed").reduce((acc, b) => acc + b.amount, 0);
  document.getElementById("tvl-val").innerText = `${(totalTVL / 1_000_000).toFixed(2)} ALGO`;
  document.getElementById("active-count").innerText = bounties.filter(b => b.status === "open" || b.status === "claimed" || b.status === "submitted").length;
}

// Authentication Flow
async function openSignModal() {
  // We can let the user pick between a simulated Creator or Worker wallet for testing
  const modalText = document.getElementById("challenge-text");
  modalText.innerHTML = `
    <div class="form-group">
      <label>Choose Wallet Persona (For Test & Validation):</label>
      <select id="sign-persona-select" class="form-control" style="background:#08070d; border:1px solid #333; color:#fff; padding:8px; border-radius:6px; width:100%;">
        <option value="RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5">Creator Profile (Garret's Wallet)</option>
        <option value="RTCedWorkerAddress555abc123999testwork">Worker Profile (Agent Developer)</option>
        <option value="custom">Custom Wallet Address...</option>
      </select>
    </div>
    <div class="form-group hidden" id="custom-addr-group">
      <label>Enter Custom Address:</label>
      <input type="text" id="sign-custom-addr" placeholder="RTC..." style="background:#08070d; border:1px solid #333; color:#fff; padding:8px; border-radius:6px; width:100%;">
    </div>
    <div style="margin-top:15px; color:#8c889e;">Challenge String to Sign:</div>
    <div id="raw-challenge-str" style="margin-top:5px; font-weight:600;">Requesting challenge...</div>
  `;

  document.getElementById("modal-sign").classList.remove("hidden");

  // Show/Hide custom input
  const select = document.getElementById("sign-persona-select");
  select.addEventListener("change", () => {
    const customGroup = document.getElementById("custom-addr-group");
    customGroup.classList.toggle("hidden", select.value !== "custom");
    requestChallenge();
  });

  await requestChallenge();
}

async function requestChallenge() {
  const address = getSelectedAddress();
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address })
    });
    const data = await res.json();
    state.challenge = data.challenge;
    const rawBox = document.getElementById("raw-challenge-str");
    if (rawBox) rawBox.innerText = data.challenge;
  } catch (err) {
    showToast("Error requesting login challenge");
  }
}

function getSelectedAddress() {
  const select = document.getElementById("sign-persona-select");
  if (!select) return "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5";
  if (select.value === "custom") {
    return document.getElementById("sign-custom-addr").value || "RTCcustomWallet123456789abcde";
  }
  return select.value;
}

async function verifyAuth() {
  const address = getSelectedAddress();
  // Append MOCK_SIG suffix so gateway bypasses actual Ed25519 signature verify for simulation
  const signature = `${address}-MOCK_SIG`;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        address,
        signature,
        challenge: state.challenge
      })
    });
    const data = await res.json();
    
    state.address = data.address;
    state.jwt = data.jwt;
    state.karma = data.karma;

    localStorage.setItem("bounty_address", data.address);
    localStorage.setItem("bounty_jwt", data.jwt);
    localStorage.setItem("bounty_karma", data.karma);

    document.getElementById("modal-sign").classList.add("hidden");
    showLoggedInState();
    fetchBounties();
    fetchNotifications();
    fetchMyBounties();
    showToast("Wallet Connected successfully!");
  } catch (err) {
    showToast("Wallet verification failed");
  }
}

function showLoggedInState() {
  document.getElementById("btn-connect").classList.add("hidden");
  document.getElementById("wallet-info").classList.remove("hidden");
  document.getElementById("wallet-addr").innerText = formatAddress(state.address);
  document.getElementById("karma-badge").innerText = `Karma: ${state.karma}`;
}

function logout() {
  state.address = null;
  state.jwt = null;
  state.karma = 25;

  localStorage.removeItem("bounty_address");
  localStorage.removeItem("bounty_jwt");
  localStorage.removeItem("bounty_karma");

  document.getElementById("btn-connect").classList.remove("hidden");
  document.getElementById("wallet-info").classList.add("hidden");
  
  showToast("Wallet Disconnected.");
  fetchBounties();
  if (state.activeTab === "dashboard") {
    switchTab("board");
  }
}

// Bounty Actions
async function createBounty(e) {
  e.preventDefault();
  
  if (!state.address) {
    showToast("Please connect your wallet first");
    return;
  }

  const payload = {
    description: document.getElementById("create-desc").value,
    amount: Math.round(parseFloat(document.getElementById("create-amount").value) * 1_000_000), // microALGO
    repo_url: document.getElementById("create-repo").value,
    hitm: document.getElementById("create-hitm").value === "true",
    karma_requirement: parseInt(document.getElementById("create-karma").value) || 0
  };

  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      showToast("Bounty Escrow Created & Funded successfully!");
      document.getElementById("form-create-bounty").reset();
      switchTab("board");
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Creation failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error creating bounty");
  }
}

async function claimBounty(id) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties/${id}/claim`, {
      method: "POST",
      headers: getHeaders()
    });
    
    if (res.ok) {
      showToast("Bounty Claimed successfully!");
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Claim failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error claiming bounty");
  }
}

function openSubmitModal(id) {
  state.selectedBountyId = id;
  document.getElementById("modal-submit").classList.remove("hidden");
}

async function submitWork(e) {
  e.preventDefault();
  const pr_url = document.getElementById("submit-pr-url").value;

  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties/${state.selectedBountyId}/submit`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({
        pr_url,
        proof_data: { type: "code", submit_agent: state.address }
      })
    });

    if (res.ok) {
      showToast("Work solution submitted successfully!");
      document.getElementById("modal-submit").classList.add("hidden");
      document.getElementById("form-submit-work").reset();
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Submission failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error submitting solution");
  }
}

async function approveBounty(id) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties/${id}/approve`, {
      method: "POST",
      headers: getHeaders()
    });
    if (res.ok) {
      showToast("Bounty Approved! Escrow funds released to worker.");
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Approval failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error approving bounty");
  }
}

async function rejectBounty(id) {
  const reason = prompt("Enter reason for rejection/revision:");
  if (reason === null) return; // Cancelled

  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties/${id}/reject`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ reason })
    });
    if (res.ok) {
      showToast("Work rejected. Reversion request sent to worker.");
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Rejection failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error rejecting bounty");
  }
}

async function disputeBounty(id) {
  const reason = prompt("Enter dispute reason for mediator review:");
  if (reason === null) return;

  try {
    const res = await fetch(`${API_BASE}/api/v1/bounties/${id}/dispute`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ reason })
    });
    if (res.ok) {
      showToast("Dispute opened. Escrow locked awaiting mediator resolution.");
      fetchBounties();
    } else {
      const err = await res.json();
      showToast(`Dispute initiation failed: ${err.detail}`);
    }
  } catch (err) {
    showToast("Network error opening dispute");
  }
}

// User Dashboard details
async function fetchNotifications() {
  if (!state.address) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/notifications`, { headers: getHeaders() });
    const data = await res.json();
    state.notifications = data;
    renderNotifications();
  } catch (err) {
    console.error("Error fetching notifications", err);
  }
}

function renderNotifications() {
  const list = document.getElementById("notif-list");
  list.innerHTML = "";
  if (state.notifications.length === 0) {
    list.innerHTML = `<div class="empty-state">No notifications.</div>`;
    return;
  }
  state.notifications.forEach(n => {
    const card = document.createElement("div");
    card.className = `notification-card ${n.read ? '' : 'unread'}`;
    card.innerHTML = `
      <span>${n.message}</span>
      ${n.read ? '' : `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="markNotifRead(${n.id})">Mark Read</button>`}
    `;
    list.appendChild(card);
  });
}

async function markNotifRead(id) {
  try {
    await fetch(`${API_BASE}/api/v1/notifications/${id}/read`, {
      method: "POST",
      headers: getHeaders()
    });
    fetchNotifications();
  } catch (err) {
    console.error("Error reading notification", err);
  }
}

function fetchMyBounties() {
  if (!state.address) return;
  const list = document.getElementById("my-bounties-list");
  list.innerHTML = "";

  const myBounties = state.bounties.filter(b => b.creator === state.address || b.worker === state.address);
  if (myBounties.length === 0) {
    list.innerHTML = `<div class="empty-state">No active bounties.</div>`;
    return;
  }

  myBounties.forEach(b => {
    const item = document.createElement("div");
    item.className = "notification-card";
    const role = b.creator === state.address ? "Creator" : "Worker";
    item.innerHTML = `
      <div>
        <strong>ALGO-${b.bounty_id.split('_')[1] || b.bounty_id}</strong> (${role})<br>
        <span style="font-size: 12px; color:#8c889e;">Status: ${b.status} | Amount: ${b.amount / 1_000_000} ALGO</span>
      </div>
    `;
    list.appendChild(item);
  });
}
