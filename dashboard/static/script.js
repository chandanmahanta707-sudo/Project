const clockEl = document.getElementById('clock');
const dateEl = document.getElementById('date');
const cpuBar = document.getElementById('cpuBar');
const cpuText = document.getElementById('cpuText');
const ramBar = document.getElementById('ramBar');
const ramText = document.getElementById('ramText');
const volBar = document.getElementById('volBar');
const volText = document.getElementById('volText');
const networkList = document.getElementById('networkList');
const gpuInfo = document.getElementById('gpuInfo');
const osInfo = document.getElementById('osInfo');

// Removed static diskBar/diskText variables for dynamic drive rendering

const batteryBar = document.getElementById('batteryBar');
const batteryText = document.getElementById('batteryText');
const pluggedText = document.getElementById('pluggedText');
const networkNameEl = document.getElementById('networkName');

const modeToggle = document.getElementById('modeToggle');
const modeLabel = document.getElementById('modeLabel');
const inputModeLabel = document.getElementById('inputModeLabel');
const inputModeToggle = document.getElementById('inputModeToggle');

const textModeContainer = document.getElementById('textModeContainer');

const textForm = document.getElementById('textForm');
const textInput = document.getElementById('textInput');
const textResponse = document.getElementById('textResponse');

const arcReactor = document.querySelector('.arc-container');
const statusReadout = document.querySelector('.status-readout');
const commsLog = document.getElementById('commsLog');

const cpuGraph = document.getElementById('cpuGraph');
const maxGraphBars = 30; // Number of bars to show in the mini graph

const songNameEl = document.getElementById('songName');
const equalizerEl = document.getElementById('equalizer');

modeToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        document.body.classList.add('jarvis-mode');
        document.body.classList.remove('standard-mode');
        modeLabel.textContent = "COMBAT";
    } else {
        document.body.classList.remove('jarvis-mode');
        document.body.classList.add('standard-mode');
        modeLabel.textContent = "STANDARD";
    }
});

if (inputModeToggle) {
    inputModeToggle.addEventListener('change', async (e) => {
        try {
            await fetch('/api/toggle_f2', { method: 'POST' });
        } catch (err) {
            console.error("Failed to toggle mode", err);
        }
    });
}

const ttsEngineSelect = document.getElementById('ttsEngineSelect');
if (ttsEngineSelect) {
    ttsEngineSelect.addEventListener('change', async (e) => {
        try {
            await fetch('/api/tts_engine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine: e.target.value })
            });
        } catch (err) {
            console.error("Failed to update TTS engine", err);
        }
    });
}

function addGraphBar(value) {
    const bar = document.createElement('div');
    bar.className = 'graph-bar';
    bar.style.height = `${value}%`;

    cpuGraph.appendChild(bar);

    if (cpuGraph.children.length > maxGraphBars) {
        cpuGraph.removeChild(cpuGraph.firstElementChild);
    }
}

async function fetchSystemsData() {
    try {
        const response = await fetch('/api/system');
        const data = await response.json();

        // Time and Date
        clockEl.textContent = data.time || '00:00:00';
        dateEl.textContent = data.date || 'YYYY-MM-DD';
        osInfo.textContent = `SYSTEM: ${data.os}`;

        // CPU & RAM
        const cpuVal = data.cpu || 0;
        const ramVal = data.ram || 0;

        cpuBar.style.width = `${cpuVal}%`;
        cpuText.textContent = `${cpuVal}%`;
        ramBar.style.width = `${ramVal}%`;
        ramText.textContent = `${ramVal}%`;

        // Add to graph
        addGraphBar(cpuVal);

        // Volume
        if (data.volume !== "N/A" && data.volume !== undefined) {
            volBar.style.width = `${data.volume}%`;
            volText.textContent = `${data.volume}%`;
        } else {
            volBar.style.width = `0%`;
            volText.textContent = `N/A`;
        }

        // Disks
        if (data.disks && data.disks.length > 0) {
            const drivesContainer = document.getElementById('drivesContainer');
            if (drivesContainer) {
                drivesContainer.innerHTML = '';
                data.disks.forEach(d => {
                    drivesContainer.innerHTML += `
                    <div class="progress-bar-container" style="margin-bottom: 8px;">
                        <div class="progress-label">DRIVE ${d.device} [<span style="color: var(--primary-color);">${d.percent}%</span>]</div>
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${d.percent}%;"></div>
                        </div>
                    </div>`;
                });
            }
        }

        // Battery
        if (data.battery) {
            batteryBar.style.width = `${data.battery.percent}%`;
            batteryText.textContent = `${data.battery.percent}%`;
            pluggedText.textContent = data.battery.plugged ? " (PLUGGED)" : " (DISCHARGING)";

            if (data.battery.percent < 20) {
                batteryBar.style.backgroundColor = "var(--alert-color)";
            } else {
                batteryBar.style.backgroundColor = "var(--primary-color)";
            }
        }

        // Network Name
        if (data.network_name) {
            networkNameEl.textContent = data.network_name.toUpperCase();
        }

        // Network
        if (data.network && data.network.length > 0) {
            networkList.innerHTML = '';
            data.network.forEach(conn => {
                const item = document.createElement('div');
                item.className = 'net-item';
                item.textContent = `ESTABLISHED: ${conn}`;
                networkList.appendChild(item);
            });
        }

        // GPU
        if (data.gpu && data.gpu.length > 0) {
            gpuInfo.innerHTML = '';
            data.gpu.forEach(gpu => {
                const row = document.createElement('div');
                row.className = 'gpu-row';

                const nameStr = gpu.name === 'N/A' ? 'NO HARDWARE' : gpu.name;
                row.innerHTML = `<span>${nameStr}</span><span>LOAD: ${gpu.load}% | TEMP: ${gpu.temp}°C</span>`;
                gpuInfo.appendChild(row);
            });
        }

        // System State Animation
        if (data.state === "LISTENING") {
            arcReactor.classList.add('listening');
            arcReactor.classList.remove('processing');
            statusReadout.textContent = "LISTENING...";
            statusReadout.style.color = "var(--primary-color)";
        } else if (data.state === "PROCESSING") {
            arcReactor.classList.remove('listening');
            arcReactor.classList.add('processing');
            statusReadout.textContent = "PROCESSING...";
            statusReadout.style.color = "var(--secondary-color)";
        } else {
            arcReactor.classList.remove('listening');
            arcReactor.classList.remove('processing');
            statusReadout.textContent = "ALL SYSTEMS NOMINAL";
            statusReadout.style.color = "var(--primary-color)";
        }

        // Interaction Logs
        if (data.logs) {
            commsLog.innerHTML = '';
            data.logs.forEach(msg => {
                const entry = document.createElement('div');
                entry.className = `log-entry ${msg.type}`;
                entry.innerHTML = `<span class="log-time">[${msg.time}]</span> <span class="log-label">${msg.type.toUpperCase()}:</span> ${msg.text}`;
                commsLog.appendChild(entry);
            });
            // Auto-scroll to bottom
            commsLog.scrollTop = commsLog.scrollHeight;
        }

        // Input Mode (Voice/Text)
        if (data.input_mode) {
            let previousInputMode = window.lastInputMode || "voice";
            window.lastInputMode = data.input_mode;
            
            inputModeLabel.textContent = data.input_mode.toUpperCase();
            if (data.input_mode === "text") {
                inputModeLabel.style.color = "var(--primary-color)";
                textModeContainer.style.display = "block";
                if (inputModeToggle && !inputModeToggle.checked) inputModeToggle.checked = true;
                
                if (previousInputMode !== "text") {
                    setTimeout(() => { if (textInput) textInput.focus(); }, 100);
                }
            } else {
                inputModeLabel.style.color = "var(--secondary-color)";
                textModeContainer.style.display = "none";
                if (inputModeToggle && inputModeToggle.checked) inputModeToggle.checked = false;
            }
        }

        // Music Info
        if (data.music) {
            songNameEl.textContent = data.music.song_name;
            if (data.music.status === "PLAYING") {
                equalizerEl.style.display = "flex";
                equalizerEl.classList.remove("paused");
            } else if (data.music.status === "PAUSED") {
                equalizerEl.style.display = "flex";
                equalizerEl.classList.add("paused");
            } else {
                equalizerEl.style.display = "none";
            }
        }

    } catch (e) {
        console.error('System offline or unreachable:', e);
        document.querySelector('.alert-overlay').style.opacity = 1;
        setTimeout(() => { document.querySelector('.alert-overlay').style.opacity = 0; }, 2000);
    }
}

// Ensure proper initial state
if (!modeToggle.checked) {
    document.body.classList.remove('jarvis-mode');
    document.body.classList.add('standard-mode');
    modeLabel.textContent = "STANDARD";
}

// Fetch data every 1.5 seconds
setInterval(fetchSystemsData, 1500);

// Initial fetch
fetchSystemsData();

// Text Mode Handling
textForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const commandText = textInput.value;
    if (!commandText) return;

    textInput.value = '';
    textResponse.textContent = '>> TRANSMITTING...';

    try {
        const res = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: commandText })
        });
        const d = await res.json();
        textResponse.textContent = `>> ${d.response}`;

        setTimeout(() => { textResponse.textContent = ''; }, 3000);
    } catch (err) {
        textResponse.textContent = '>> COMM LINK FAILED';
    }
});

// Easter Egg Interactive Animation
if (arcReactor) {
    arcReactor.style.cursor = "pointer"; // Indicate it's interactive
    arcReactor.addEventListener('mouseenter', () => {
        if (!arcReactor.classList.contains('easter-egg')) {
            arcReactor.classList.add('easter-egg');
            // Remove the class after the 2.5s animation completes to reset the state
            setTimeout(() => {
                arcReactor.classList.remove('easter-egg');
            }, 2500);
        }
    });
}
