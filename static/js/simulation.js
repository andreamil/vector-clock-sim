
function renderVisualization(state) {
    const vizContainer = document.getElementById('visualization-container');
    vizContainer.innerHTML = '';
    const numProcesses = state.processes.length;
    if (numProcesses === 0) return;

    // --- Flatten all events into one list for easier processing ---
    const allEvents = [];
    state.processes.forEach(p => {
        p.events.forEach((event, eventIndex) => {
            allEvents.push({
                ...event,
                process_id: p.id,
                event_index: eventIndex // Keep original index for unique keys
            });
        });
    });

    const width = 100 + (state.global_time + 1) * 60;
    const height = 100 + (numProcesses - 1) * 100;

    const draw = SVG().addTo(vizContainer).size(width, height);
    const eventCoords = {}; // Stores coordinates: 'processId-eventIndex' -> {x, y}

    // 1. Draw process lines
    state.processes.forEach((p, i) => {
        const y = 50 + i * 100;
        draw.line(50, y, width - 50, y).stroke({ width: 2, color: '#333' });
        draw.text(`P${i + 1}`).font({ family: 'monospace', size: 16 }).move(10, y - 8);
    });

    // 2. Draw all events and store their coordinates
    allEvents.forEach(event => {
        const x = 50 + event.time_tick * 60;
        const y = 50 + event.process_id * 100;
        const key = `${event.process_id}-${event.event_index}`;
        eventCoords[key] = { x, y };

        let color = '#0d6efd'; // local
        if (event.type === 'send') color = '#198754';
        if (event.type === 'receive') color = '#dc3545';
        
        draw.circle(10).center(x, y).fill(color);
        draw.text(`(${event.clock.join(',')})`).font({ anchor: 'middle', family: 'monospace', size: 12 }).move(x, y + 20);
    });

    // 3. Draw arrows using the reliable message_id
    const arrowMarker = draw.defs().marker(10, 10, function(add) {
        add.path('M0,0 L10,5 L0,10 Z').fill('#6c757d');
    });

    const sendEvents = allEvents.filter(e => e.type === 'send');

    sendEvents.forEach(sendEvent => {
        const receiveEvent = allEvents.find(
            e => e.type === 'receive' && e.message_id === sendEvent.message_id
        );

        if (receiveEvent) {
            const sendKey = `${sendEvent.process_id}-${sendEvent.event_index}`;
            const receiveKey = `${receiveEvent.process_id}-${receiveEvent.event_index}`;

            const from = eventCoords[sendKey];
            const to = eventCoords[receiveKey];

            if (from && to) {
                draw.line(from.x, from.y, to.x, to.y)
                    .stroke({ width: 1.5, color: '#6c757d' })
                    .marker('end', arrowMarker);
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    // --- Elementos da UI ---
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const tickBtn = document.getElementById('tick-btn');
    const addProcessBtn = document.getElementById('add-process-btn');
    const resetBtn = document.getElementById('reset-btn');
    const statusDiv = document.getElementById('status-div');
    const processControlsContainer = document.getElementById('process-controls-container');

    startBtn.addEventListener('click', () => socket.emit('simulation:start'));
    pauseBtn.addEventListener('click', () => socket.emit('simulation:pause'));
    tickBtn.addEventListener('click', () => socket.emit('simulation:tick'));
    addProcessBtn.addEventListener('click', () => socket.emit('process:add'));
    resetBtn.addEventListener('click', () => socket.emit('simulation:reset'));

    socket.on('state_update', (state) => {
        console.log('Received state update:', state);
        updateUI(state);
        renderVisualization(state);
        renderProcessControls(state);
    });

    function updateUI(state) {
        statusDiv.textContent = `Status: ${state.mode} | Tempo Global: ${state.global_time}`;
        if (state.mode === 'running') {
            statusDiv.className = 'alert alert-success';
            startBtn.disabled = true;
            pauseBtn.disabled = false;
            tickBtn.disabled = true;
        } else { // paused
            statusDiv.className = 'alert alert-secondary';
            startBtn.disabled = false;
            pauseBtn.disabled = true;
            tickBtn.disabled = false;
        }
    }

    function renderProcessControls(state) {
        processControlsContainer.innerHTML = '';
        state.processes.forEach((p, i) => {
            const col = document.createElement('div');
            col.className = 'col-md-4 mb-3';
            
            let options = '';
            state.processes.forEach((target_p, j) => {
                if (i !== j) {
                    options += `<option value="${j}">para P${j + 1}</option>`;
                }
            });

            col.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Processo P${i + 1}</h5>
                        <p class="mb-2">Relógio: <code>[${p.clock.join(', ')}]</code></p>
                        <div class="input-group">
                            <select class="form-select" id="select-p${i}">${options}</select>
                            <button class="btn btn-outline-danger" onclick="forceSendMessage(${i})">Forçar Envio</button>
                        </div>
                    </div>
                </div>`;
            processControlsContainer.appendChild(col);
        });
    }
});

function forceSendMessage(senderId) {
    const select = document.getElementById(`select-p${senderId}`);
    if (select && select.value !== '') {
        const receiverId = parseInt(select.value, 10);
        window.socket.emit('message:force_send', { sender_id: senderId, receiver_id: receiverId });
    }
}
window.socket = io();