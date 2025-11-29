// ============================================
// GLOBAL STATE
// ============================================
const freeSlotsEl = document.getElementById('free-slots');
const gateStateEl = document.getElementById('gate-state');
const lastUpdateEl = document.getElementById('last-update');
const slotsContainer = document.getElementById('slots');
const errorsList = document.getElementById('errors');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const systemStatus = document.getElementById('system-status');
const usageRateEl = document.getElementById('usage-rate');
const gateStatusCard = document.getElementById('gate-status-card');

let lastUpdateTime = null;
let connectionStatus = 'connecting';
let updateInterval = null;
let fetchErrorCount = 0;
const MAX_FETCH_ERRORS = 3;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function updateConnectionStatus(status) {
  connectionStatus = status;
  if (status === 'online') {
    statusIndicator.className = 'status-indicator online';
    statusText.textContent = 'Hệ thống hoạt động';
    systemStatus.className = 'system-status online';
  } else if (status === 'offline') {
    statusIndicator.className = 'status-indicator offline';
    statusText.textContent = 'Mất kết nối';
    systemStatus.className = 'system-status offline';
  } else {
    statusIndicator.className = 'status-indicator';
    statusText.textContent = 'Đang kết nối...';
    systemStatus.className = 'system-status';
  }
}

function calculateUsageRate(free, total) {
  if (total === 0) return 0;
  const used = total - free;
  return Math.round((used / total) * 100);
}

function formatTime(dateString) {
  if (!dateString) return '--';
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 5) return 'Vừa xong';
    if (diff < 60) return `${diff} giây trước`;
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
    return date.toLocaleTimeString('vi-VN');
  } catch (e) {
    return dateString;
  }
}

// ============================================
// FETCH STATUS
// ============================================

async function fetchStatus() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const res = await fetch('/api/status', {
      signal: controller.signal,
      headers: {
        'Cache-Control': 'no-cache',
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    const data = await res.json();
    render(data);
    
    // Update connection status
    if (data.arduino_connected) {
      updateConnectionStatus('online');
      if (data.arduino_update_age && data.arduino_update_age > 10) {
        showToast(`⚠️ Arduino không cập nhật trong ${Math.round(data.arduino_update_age)}s`, 'warning');
      }
    } else {
      updateConnectionStatus('offline');
      showToast('⚠️ Mất kết nối với Arduino', 'error');
    }
    
    lastUpdateTime = data.last_update;

    return data;
  } catch (err) {
    console.error('Lỗi khi lấy dữ liệu:', err);
    fetchErrorCount++;
    updateConnectionStatus('offline');

    if (err.name === 'AbortError') {
      showToast('Kết nối quá chậm. Vui lòng kiểm tra mạng.', 'error');
    } else {
      showToast('Không thể kết nối đến server.', 'error');
    }

    // Hiển thị thông báo lỗi
    if (errorsList) {
      errorsList.innerHTML = `
        <li style="color: #b91c1c;">
          ⚠️ Lỗi kết nối: ${err.message}. Đang thử lại... (${fetchErrorCount}/${MAX_FETCH_ERRORS})
        </li>
      `;
    }

    // Exponential backoff: tăng delay khi có nhiều lỗi
    if (fetchErrorCount >= MAX_FETCH_ERRORS) {
      const backoffDelay = Math.min(5000 * Math.pow(2, fetchErrorCount - MAX_FETCH_ERRORS), 30000);
      console.warn(`Backoff: đợi ${backoffDelay}ms trước khi retry`);
      await new Promise(resolve => setTimeout(resolve, backoffDelay));
    }

    return null;
  } finally {
    // Reset error count khi thành công
    if (fetchErrorCount > 0) {
      fetchErrorCount = 0;
    }
  }
}

// ============================================
// RENDER FUNCTIONS
// ============================================

function render(data) {
  if (!data) return;

  // Update stats
  if (freeSlotsEl) {
    freeSlotsEl.textContent = data.free || 0;
  }

  const totalSlots = data.total_slots || 
    parseInt(document.getElementById('total-slots')?.textContent) || 3;
  const usageRate = calculateUsageRate(data.free || 0, totalSlots);

  if (usageRateEl) {
    usageRateEl.textContent = `${usageRate}%`;
  }

  // Update gate status
  const gateState = data.gate || 'unknown';
  if (gateStateEl) {
    gateStateEl.textContent = gateState === 'open' ? 'MỞ' : 'ĐÓNG';
  }

  if (gateStatusCard) {
    gateStatusCard.className = `stat-card ${
      gateState === 'open' ? 'status-online' : ''
    }`;
  }

  // Update Arduino connection status
  if (data.arduino_connected !== undefined) {
    const arduinoStatusEl = document.getElementById('arduino-status');
    if (arduinoStatusEl) {
      if (data.arduino_connected) {
        arduinoStatusEl.innerHTML = `
          <span style="color: #22c55e;">●</span> Arduino: Kết nối
          ${data.arduino_update_age ? ` (${Math.round(data.arduino_update_age)}s trước)` : ''}
        `;
      } else {
        arduinoStatusEl.innerHTML = `
          <span style="color: #ef4444;">●</span> Arduino: Mất kết nối
        `;
      }
    }
  }

  // Update last update time
  if (lastUpdateEl && data.last_update) {
    lastUpdateEl.textContent = formatTime(data.last_update);
  }

  // Render slots với manual control cho Slot 2,3
  if (slotsContainer && data.slots) {
    slotsContainer.innerHTML = '';
    data.slots.forEach((status, idx) => {
      const slotId = idx + 1;
      const el = document.createElement('div');
      el.className = `slot ${status ? 'occupied' : 'free'}`;
      
      // Slot 1: từ sensor (không có manual control)
      // Slot 2,3: có manual control
      let controlsHTML = '';
      if (slotId > 1) {
        controlsHTML = `
          <div class="slot-controls" style="margin-top: 8px;">
            <button onclick="manualSlot(${slotId}, false)" class="btn btn-sm btn-success" style="margin-right: 4px;">
              Đánh dấu trống
            </button>
            <button onclick="manualSlot(${slotId}, true)" class="btn btn-sm btn-danger">
              Đánh dấu có xe
            </button>
          </div>
        `;
      } else {
        controlsHTML = '<span style="color: #6b7280; font-size: 0.85rem;">(Tự động từ sensor)</span>';
      }
      
      el.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <span>🚗 Slot ${slotId}</span>
            <strong style="margin-left: 8px;">${status ? 'ĐANG ĐỖ' : 'TRỐNG'}</strong>
          </div>
        </div>
        ${controlsHTML}
      `;
      slotsContainer.appendChild(el);
    });
  }

  // Render errors
  if (errorsList) {
    errorsList.innerHTML = '';
    if (!data.errors || data.errors.length === 0) {
      errorsList.innerHTML =
        '<li style="color: #22c55e;">✅ Hệ thống hoạt động bình thường.</li>';
    } else {
      data.errors.forEach((err) => {
        const li = document.createElement('li');
        li.textContent = `⚠️ ${err}`;
        errorsList.appendChild(li);
      });
    }
  }
}

// ============================================
// MANUAL CONTROL FUNCTIONS
// ============================================

async function manualGate(state) {
  const btn = event?.target;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Đang xử lý...';
  }

  try {
    const res = await fetch('/api/gate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ state: state }),
    });
    const data = await res.json();

    if (res.ok) {
      showToast(
        `Barrier đã được ${state === 'open' ? 'mở' : 'đóng'} thành công!`,
        'success'
      );
      // Notification cho web
      if (window.Notification && Notification.permission === 'granted') {
        new Notification(`Barrier ${state === 'open' ? 'đã mở' : 'đã đóng'}`);
      }
      fetchStatus();
    } else {
      const errorMsg = data.error || 'Không thể điều khiển barrier';
      if (errorMsg.includes('AUTO mode')) {
        showToast(
          '⚠️ Đang ở chế độ AUTO. Chuyển sang MANUAL để điều khiển thủ công.',
          'warning'
        );
      } else {
        showToast(`Lỗi: ${errorMsg}`, 'error');
      }
    }
  } catch (err) {
    showToast(`Lỗi kết nối: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = state === 'open' ? '🔓 Mở Barrier' : '🔒 Đóng Barrier';
    }
  }
}

async function manualSlot(slotId, occupied) {
  try {
    const res = await fetch(`/api/slot/${slotId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ occupied: occupied }),
    });
    const data = await res.json();

    if (res.ok) {
      showToast(
        `Slot ${slotId} đã được đặt thành: ${
          occupied ? 'CÓ XE' : 'TRỐNG'
        }`,
        'success'
      );
      // Notification cho web
      if (window.Notification && Notification.permission === 'granted') {
        new Notification(`Slot ${slotId} ${occupied ? 'có xe' : 'trống'}`);
      }
      fetchStatus();
    } else {
      const errorMsg = data.error || 'Không thể đặt slot';
      if (errorMsg.includes('AUTO mode')) {
        showToast(
          '⚠️ Đang ở chế độ AUTO. Chuyển sang MANUAL để điều khiển thủ công.',
          'warning'
        );
      } else {
        showToast(`Lỗi: ${errorMsg}`, 'error');
      }
    }
  } catch (err) {
    showToast(`Lỗi kết nối: ${err.message}`, 'error');
  }
}

// Buzzer đã được loại bỏ, thay bằng web notifications
// async function manualBuzzer(duration = 0.2) {
  const btn = event?.target;
  if (btn) {
    btn.disabled = true;
  }

  try {
    const res = await fetch(`/api/buzzer?duration=${duration}`, {
      method: 'POST',
    });
    const data = await res.json();

    if (res.ok) {
      showToast('Buzzer đã được kích hoạt!', 'success');
    } else {
      showToast(`Lỗi: ${data.error || 'Không thể kích hoạt buzzer'}`, 'error');
    }
  } catch (err) {
    showToast(`Lỗi kết nối: ${err.message}`, 'error');
  } finally {
    if (btn) {
      setTimeout(() => {
        btn.disabled = false;
      }, 500);
    }
  }
}

function refreshData() {
  showToast('Đang làm mới dữ liệu...', 'info');
  fetchStatus();
}

// ============================================
// SETUP MANUAL CONTROLS
// ============================================

function setupManualControls() {
  // Gate controls
  const btnGateOpen = document.getElementById('btn-gate-open');
  const btnGateClose = document.getElementById('btn-gate-close');
  if (btnGateOpen) {
    btnGateOpen.addEventListener('click', () => manualGate('open'));
  }
  if (btnGateClose) {
    btnGateClose.addEventListener('click', () => manualGate('closed'));
  }

  // Request notification permission
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }

  // Refresh button
  const btnRefresh = document.getElementById('btn-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', refreshData);
  }
}

function renderSlotControls(data) {
  const slotControls = document.getElementById('slot-controls');
  if (!slotControls) return;

  if (!data || !data.slots) {
    slotControls.innerHTML = '<p style="color: #6b7280;">Đang tải...</p>';
    return;
  }

  slotControls.innerHTML = '';
  data.slots.forEach((status, idx) => {
    const div = document.createElement('div');
    div.className = 'slot-control-item';
    div.innerHTML = `
      <span>Slot ${idx + 1}: <strong>${
      status ? 'OCCUPIED' : 'FREE'
    }</strong></span>
      <button class="btn btn-sm ${status ? 'btn-success' : 'btn-danger'}" 
              onclick="manualSlot(${idx}, ${!status})">
        Đặt ${status ? 'FREE' : 'OCCUPIED'}
      </button>
    `;
    slotControls.appendChild(div);
  });
}

// Update render function to include slot controls
const originalRender = render;
render = function (data) {
  originalRender(data);
  renderSlotControls(data);
};

// ============================================
// INITIALIZE
// ============================================

function init() {
  // Initial fetch
  fetchStatus();

  // Setup manual controls
  setupManualControls();

  // Auto-refresh every 1 second
  updateInterval = setInterval(() => {
    fetchStatus();
  }, 1000);

  // Check connection health
  setInterval(() => {
    if (lastUpdateTime) {
      const now = new Date();
      const lastUpdate = new Date(lastUpdateTime);
      const diff = Math.floor((now - lastUpdate) / 1000);

      if (diff > 10 && connectionStatus === 'online') {
        updateConnectionStatus('offline');
        showToast('Mất kết nối với server. Đang thử lại...', 'error');
      }
    }
  }, 5000);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (updateInterval) {
    clearInterval(updateInterval);
  }
});
