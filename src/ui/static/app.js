const tg = window.Telegram.WebApp;
tg.expand();

// Initialize Main Button
tg.MainButton.text = "SAVE CHANGES";
tg.MainButton.textColor = "#ffffff";
tg.MainButton.color = tg.themeParams.button_color || "#0a84ff";

// Extract group_id from URL query parameters or start_param
const urlParams = new URLSearchParams(window.location.search);
let groupId = urlParams.get('group_id');

// If launched via Direct Link, the payload is in start_param
if (!groupId && tg.initDataUnsafe && tg.initDataUnsafe.start_param) {
    groupId = tg.initDataUnsafe.start_param;
}

if (!groupId) {
    document.getElementById('loader').innerHTML = '<p>Error: No group specified.</p>';
} else {
    document.getElementById('groupName').innerText = `Group ID: ${groupId}`;
    fetchGroupData();
}

async function fetchGroupData() {
    try {
        const response = await fetch(`/api/group?group_id=${groupId}`, {
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch group data');
        }

        const data = await response.json();
        populateForm(data);
        
        document.getElementById('loader').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
        document.getElementById('statusIndicator').classList.add('online');
        
        // Show main button after loading data
        tg.MainButton.show();
        
        // Fetch slots
        await fetchSlots();
        
        // Fetch streams
        await fetchStreams();
    } catch (error) {
        console.error(error);
        document.getElementById('loader').innerHTML = `<p>Error loading settings. Are you an admin?</p>`;
    }
}

function populateForm(data) {
    document.getElementById('timezone').value = data.timezone || 'UTC';
    document.getElementById('auto_create').checked = data.auto_create || false;
    document.getElementById('reminder_hours').value = data.reminder_hours || 1.0;
    document.getElementById('check_window_hours').value = data.check_window_hours || 24.0;
    document.getElementById('broadcast_privacy').value = data.broadcast_privacy || 'public';
    document.getElementById('broadcast_description').value = data.broadcast_description || '';
    document.getElementById('broadcast_made_for_kids').checked = data.broadcast_made_for_kids || false;
    
    // Render YouTube Integration section
    const ytContainer = document.getElementById('youtubeStatusContainer');
    if (data.yt_channel_id) {
        // Connected State
        ytContainer.innerHTML = `
            <p class="yt-status-text">Connected to:<br><strong>${data.yt_channel_name || 'YouTube Channel'}</strong></p>
            <button type="button" id="btnDisconnectYt" class="btn-youtube disconnect">Disconnect YouTube</button>
        `;
        document.getElementById('btnDisconnectYt').addEventListener('click', async () => {
            tg.HapticFeedback.impactOccurred('medium');
            if (confirm("Are you sure you want to disconnect YouTube?")) {
                await disconnectYouTube();
            }
        });
    } else {
        // Disconnected State
        ytContainer.innerHTML = `
            <p class="yt-status-text" style="color: var(--hint-color); font-size: 14px;">Link your channel to auto-create broadcasts.</p>
            <button type="button" id="btnConnectYt" class="btn-youtube">Connect YouTube</button>
        `;
        document.getElementById('btnConnectYt').addEventListener('click', () => {
            tg.HapticFeedback.impactOccurred('light');
            tg.openLink(data.yt_auth_url);
        });
    }
}

async function disconnectYouTube() {
    try {
        const response = await fetch(`/api/youtube/disconnect?group_id=${groupId}`, {
            method: 'POST',
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });
        if (!response.ok) throw new Error('Failed to disconnect');
        
        tg.HapticFeedback.notificationOccurred('success');
        // Refresh the whole UI
        await fetchGroupData();
    } catch (error) {
        console.error(error);
        tg.HapticFeedback.notificationOccurred('error');
        alert("Failed to disconnect.");
    }
}

// Handle changes to show the save button if it was hidden
document.getElementById('settingsForm').addEventListener('input', () => {
    if (!tg.MainButton.isVisible) {
        tg.MainButton.show();
    }
});

// Handle Save
Telegram.WebApp.onEvent('mainButtonClicked', async () => {
    tg.MainButton.showProgress();
    
    const formData = {
        timezone: document.getElementById('timezone').value,
        auto_create: document.getElementById('auto_create').checked,
        reminder_hours: parseFloat(document.getElementById('reminder_hours').value),
        check_window_hours: parseFloat(document.getElementById('check_window_hours').value),
        broadcast_privacy: document.getElementById('broadcast_privacy').value,
        broadcast_description: document.getElementById('broadcast_description').value,
        broadcast_made_for_kids: document.getElementById('broadcast_made_for_kids').checked
    };

    try {
        const response = await fetch(`/api/group?group_id=${groupId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `tma ${tg.initData}`
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error('Failed to update group');
        }

        tg.HapticFeedback.notificationOccurred('success');
        tg.close();
    } catch (error) {
        console.error(error);
        tg.HapticFeedback.notificationOccurred('error');
        alert("Failed to save settings.");
    } finally {
        tg.MainButton.hideProgress();
    }
});

// --- Slots Management ---

const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

async function fetchSlots() {
    try {
        const response = await fetch(`/api/slots?group_id=${groupId}`, {
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch slots');
        const slots = await response.json();
        renderSlots(slots);
    } catch (error) {
        console.error("Failed to load slots:", error);
    }
}

function renderSlots(slots) {
    const list = document.getElementById('slotsList');
    list.innerHTML = '';
    
    if (slots.length === 0) {
        list.innerHTML = '<p style="color: var(--hint-color); font-size: 14px; text-align: center;">No slots configured yet.</p>';
        return;
    }
    
    slots.forEach(slot => {
        const card = document.createElement('div');
        card.className = 'slot-card';
        
        const dayStr = daysOfWeek[slot.day_of_week] || 'Unknown';
        
        card.innerHTML = `
            <div class="slot-info">
                <span class="slot-time">${dayStr} at ${slot.local_time}</span>
                ${slot.title_template ? `<span class="slot-title">Title: ${slot.title_template}</span>` : ''}
                ${slot.custom_message ? `<span class="slot-title">Msg: ${slot.custom_message}</span>` : ''}
            </div>
            <div class="slot-actions">
                <button type="button" class="btn-danger" data-id="${slot.slot_id}">Delete</button>
            </div>
        `;
        list.appendChild(card);
    });
    
    // Attach delete listeners
    list.querySelectorAll('.btn-danger').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const slotId = e.target.getAttribute('data-id');
            await deleteSlot(slotId);
        });
    });
}

async function deleteSlot(slotId) {
    tg.HapticFeedback.impactOccurred('light');
    try {
        const response = await fetch(`/api/slots?group_id=${groupId}&slot_id=${slotId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });
        if (!response.ok) throw new Error('Delete failed');
        
        tg.HapticFeedback.notificationOccurred('success');
        await fetchSlots();
    } catch (error) {
        console.error("Failed to delete slot", error);
        tg.HapticFeedback.notificationOccurred('error');
    }
}

document.getElementById('btnAddSlot').addEventListener('click', async () => {
    tg.HapticFeedback.impactOccurred('medium');
    
    const timeInput = document.getElementById('slot_time').value;
    if (!timeInput) {
        tg.HapticFeedback.notificationOccurred('warning');
        alert("Please select a time.");
        return;
    }
    
    const btn = document.getElementById('btnAddSlot');
    btn.disabled = true;
    btn.innerText = 'Adding...';
    
    const day = document.getElementById('slot_day').value;
    const title = document.getElementById('slot_title').value;
    const msg = document.getElementById('slot_message').value;
    
    try {
        const response = await fetch(`/api/slots?group_id=${groupId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `tma ${tg.initData}`
            },
            body: JSON.stringify({
                day_of_week: parseInt(day),
                local_time: timeInput,
                title_template: title,
                custom_message: msg
            })
        });
        
        if (!response.ok) throw new Error('Failed to add slot');
        
        tg.HapticFeedback.notificationOccurred('success');
        
        // Reset form
        document.getElementById('slot_time').value = '';
        document.getElementById('slot_title').value = '';
        document.getElementById('slot_message').value = '';
        
        await fetchSlots();
    } catch (error) {
        console.error("Error creating slot:", error);
        tg.HapticFeedback.notificationOccurred('error');
        alert("Failed to create slot. Please try again.");
    }
});

async function fetchStreams() {
    try {
        const response = await fetch(`/api/streams?group_id=${groupId}`, {
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });
        if (!response.ok) throw new Error('Network response was not ok');
        const streams = await response.json();
        renderStreams(streams);
    } catch (error) {
        console.error("Error fetching streams:", error);
        document.getElementById('streamsList').innerHTML = `<p style="text-align: center; color: var(--hint-color);">Failed to load streams</p>`;
    }
}

function renderStreams(streams) {
    const container = document.getElementById('streamsList');
    if (streams.length === 0) {
        container.innerHTML = `<p style="text-align: center; color: var(--hint-color); padding: 10px 0;">No upcoming streams tracked.</p>`;
        return;
    }
    
    container.innerHTML = '';
    
    // Sort streams by scheduled_start ascending
    streams.sort((a, b) => a.scheduled_start - b.scheduled_start);
    
    streams.forEach(stream => {
        const card = document.createElement('div');
        card.className = `stream-card status-${stream.status.toLowerCase()}`;
        
        const date = new Date(stream.scheduled_start * 1000);
        const dateStr = date.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        
        card.innerHTML = `
            <div class="stream-date">${dateStr}</div>
            <div class="stream-meta">
                <span style="text-transform: capitalize;">${stream.status}</span>
                <a href="${stream.yt_url}" target="_blank" class="stream-link">View on YouTube</a>
            </div>
        `;
        container.appendChild(card);
    });
}

document.getElementById('btnSync').addEventListener('click', async () => {
    tg.HapticFeedback.impactOccurred('medium');
    const btn = document.getElementById('btnSync');
    btn.classList.add('syncing');
    btn.disabled = true;
    
    try {
        const response = await fetch(`/api/sync?group_id=${groupId}`, {
            method: 'POST',
            headers: {
                'Authorization': `tma ${tg.initData}`
            }
        });
        if (!response.ok) throw new Error('Failed to sync');
        
        tg.HapticFeedback.notificationOccurred('success');
        await fetchStreams();
    } catch (error) {
        console.error("Error syncing:", error);
        tg.HapticFeedback.notificationOccurred('error');
        alert("Failed to sync with YouTube.");
    } finally {
        btn.classList.remove('syncing');
        btn.disabled = false;
    }
});
