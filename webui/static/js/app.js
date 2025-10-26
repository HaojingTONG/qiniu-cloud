// Voice OS Web UI JavaScript

// State
let currentPlan = null;
let currentSteps = [];
let eventSource = null;
let isFirstRecording = true;  // Track if this is the first recording

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Voice OS Web UI initialized');
    connectToEventStream();
});

// Connect to Server-Sent Events
function connectToEventStream() {
    eventSource = new EventSource('/events');

    eventSource.onopen = function() {
        console.log('Connected to event stream');
        updateConnectionStatus(true);
    };

    eventSource.onerror = function() {
        console.error('Event stream error');
        updateConnectionStatus(false);
        // Reconnect after 3 seconds
        setTimeout(connectToEventStream, 3000);
    };

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            handleEvent(data);
        } catch (error) {
            console.error('Error parsing event:', error);
        }
    };
}

// Update connection status
function updateConnectionStatus(connected) {
    const badge = document.getElementById('connectionStatus');
    const statusText = badge.querySelector('.status-text');

    if (connected) {
        badge.classList.add('connected');
        statusText.textContent = '已连接';
    } else {
        badge.classList.remove('connected');
        statusText.textContent = '连接中...';
    }
}

// Handle incoming events
function handleEvent(event) {
    console.log('Event:', event.type, event.data);

    // Add to event log
    addEventToLog(event);

    // Handle specific event types
    switch (event.type) {
        case 'connected':
            break;

        case 'asr_start':
            handleASRStart(event.data);
            break;

        case 'asr_complete':
            handleASRComplete(event.data);
            break;

        case 'planning_start':
            handlePlanningStart();
            break;

        case 'intent_parsed':
            handleIntentParsed(event.data);
            break;

        case 'plan_parsed':
            handlePlanParsed(event.data);
            break;

        case 'step_start':
            handleStepStart(event.data);
            break;

        case 'step_complete':
            handleStepComplete(event.data);
            break;

        case 'step_error':
            handleStepError(event.data);
            break;

        case 'execution_complete':
            handleExecutionComplete(event.data);
            break;

        case 'intent_complete':
            handleIntentComplete(event.data);
            break;

        case 'confirmation_required':
            handleConfirmationRequired(event.data);
            break;

        case 'ready_for_next':
            handleReadyForNext(event.data);
            break;

        case 'tts_start':
            handleTTSStart(event.data);
            break;

        default:
            console.log('Unhandled event type:', event.type);
    }
}

// ASR Handlers
function handleASRStart(data) {
    const asrStatus = document.getElementById('asrStatus');
    asrStatus.innerHTML = `
        <div class="status-icon">🎤</div>
        <div class="status-info">
            <div class="status-label">状态</div>
            <div class="status-value">正在录音...</div>
        </div>
    `;

    const transcript = document.querySelector('.transcript-text');
    transcript.textContent = '正在识别...';
}

function handleASRComplete(data) {
    const asrStatus = document.getElementById('asrStatus');
    asrStatus.innerHTML = `
        <div class="status-icon">✅</div>
        <div class="status-info">
            <div class="status-label">状态</div>
            <div class="status-value">识别完成</div>
        </div>
    `;

    const transcript = document.querySelector('.transcript-text');
    transcript.textContent = data.text || '—';
}

// Planning Handlers
function handlePlanningStart() {
    const planCard = document.getElementById('currentPlan');
    planCard.innerHTML = '<div class="plan-empty">正在规划...</div>';
}

function handleIntentParsed(data) {
    currentPlan = {
        type: 'intent',
        intent: data.intent,
        slots: data.slots
    };
    displayPlan();
}

function handlePlanParsed(data) {
    currentPlan = {
        type: 'plan',
        summary: data.summary,
        steps: data.steps
    };
    currentSteps = data.steps.map((step, index) => ({
        index: index + 1,
        intent: step.intent,
        slots: step.slots,
        status: 'pending'
    }));
    displayPlan();
    displaySteps();
}

function displayPlan() {
    const planCard = document.getElementById('currentPlan');

    if (!currentPlan) {
        planCard.innerHTML = '<div class="plan-empty">暂无活动任务</div>';
        return;
    }

    if (currentPlan.type === 'intent') {
        planCard.innerHTML = `
            <div class="plan-summary">单步任务: ${currentPlan.intent}</div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                参数: ${JSON.stringify(currentPlan.slots, null, 2)}
            </div>
        `;
    } else if (currentPlan.type === 'plan') {
        const stepsHTML = currentPlan.steps.map((step, i) => `
            <li class="plan-step">
                <span class="plan-step-number">${i + 1}</span>
                <span>${step.intent}</span>
            </li>
        `).join('');

        planCard.innerHTML = `
            <div class="plan-summary">${currentPlan.summary}</div>
            <ol class="plan-steps">
                ${stepsHTML}
            </ol>
        `;
    }
}

// Execution Handlers
function displaySteps() {
    const container = document.getElementById('stepsContainer');

    if (currentSteps.length === 0) {
        container.innerHTML = '<div class="steps-empty">等待任务...</div>';
        document.getElementById('progressSection').style.display = 'none';
        return;
    }

    // Show progress
    document.getElementById('progressSection').style.display = 'block';
    updateProgress();

    // Display steps
    const stepsHTML = currentSteps.map(step => {
        const statusText = {
            'pending': '等待中',
            'running': '执行中',
            'completed': '已完成',
            'error': '失败'
        }[step.status] || '未知';

        // Build details HTML
        let detailsHTML = '';
        if (step.message) {
            detailsHTML += `<div class="step-message">${step.message}</div>`;
        }
        if (step.file_path) {
            detailsHTML += `<div class="step-file-path">📁 文件位置: <code>${step.file_path}</code></div>`;
        }

        return `
            <div class="step-item ${step.status}" id="step-${step.index}">
                <div class="step-header">
                    <div class="step-number">${step.index}</div>
                    <div class="step-title">${step.intent}</div>
                    <div class="step-status">${statusText}</div>
                </div>
                ${detailsHTML ? `<div class="step-details">${detailsHTML}</div>` : ''}
            </div>
        `;
    }).join('');

    container.innerHTML = stepsHTML;
}

function handleStepStart(data) {
    const stepIndex = data.step_number;
    if (currentSteps[stepIndex - 1]) {
        currentSteps[stepIndex - 1].status = 'running';
        displaySteps();
    }
}

function handleStepComplete(data) {
    const stepIndex = data.step_number;
    if (currentSteps[stepIndex - 1]) {
        currentSteps[stepIndex - 1].status = 'completed';
        currentSteps[stepIndex - 1].message = data.message;
        // Add file path if available
        if (data.file_path) {
            currentSteps[stepIndex - 1].file_path = data.file_path;
        }
        displaySteps();
    }
}

function handleStepError(data) {
    const stepIndex = data.step_number;
    if (currentSteps[stepIndex - 1]) {
        currentSteps[stepIndex - 1].status = 'error';
        currentSteps[stepIndex - 1].message = data.error;
        displaySteps();
    }
}

function handleExecutionComplete(data) {
    updateProgress(100);
    // Reset after 3 seconds
    setTimeout(() => {
        currentPlan = null;
        currentSteps = [];
        displayPlan();
        displaySteps();
    }, 3000);
}

function handleIntentComplete(data) {
    // For single intent tasks, display file path if available
    if (data.file_path && currentPlan && currentPlan.type === 'intent') {
        const planCard = document.getElementById('currentPlan');
        const existingHTML = planCard.innerHTML;

        // Add file path info
        const filePathHTML = `
            <div class="file-path-info">
                <div class="file-path-label">📁 文件位置:</div>
                <div class="file-path-value"><code>${data.file_path}</code></div>
            </div>
        `;

        planCard.innerHTML = existingHTML + filePathHTML;
    }
}

function updateProgress(percentage) {
    if (percentage === undefined) {
        const completed = currentSteps.filter(s => s.status === 'completed').length;
        const total = currentSteps.length;
        percentage = total > 0 ? (completed / total) * 100 : 0;
    }

    document.getElementById('progressPercentage').textContent = `${Math.round(percentage)}%`;
    document.getElementById('progressFill').style.width = `${percentage}%`;
}

// Confirmation Handler
function handleConfirmationRequired(data) {
    const dialog = document.getElementById('confirmationDialog');
    const message = document.getElementById('confirmationMessage');

    message.textContent = data.message || '需要确认此操作';
    dialog.style.display = 'block';
}

function handleConfirm(confirmed) {
    // Send confirmation to backend
    fetch('/api/confirm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ confirmed: confirmed })
    });

    // Hide dialog
    document.getElementById('confirmationDialog').style.display = 'none';
}

// TTS Handler
function handleTTSStart(data) {
    const ttsStatus = document.getElementById('ttsStatus');
    ttsStatus.innerHTML = `<div class="tts-text">🔊 ${data.text}</div>`;
}

// Event Log
function addEventToLog(event) {
    const log = document.getElementById('eventLog');
    const time = new Date(event.timestamp).toLocaleTimeString('zh-CN');

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item';
    eventItem.innerHTML = `
        <div class="event-time">${time}</div>
        <div class="event-type">${event.type}</div>
        <div class="event-data">${formatEventData(event.data)}</div>
    `;

    log.insertBefore(eventItem, log.firstChild);

    // Keep only last 50 events
    while (log.children.length > 50) {
        log.removeChild(log.lastChild);
    }
}

function formatEventData(data) {
    if (typeof data === 'string') return data;
    if (data.text) return data.text;
    if (data.message) return data.message;
    if (data.intent) return `intent: ${data.intent}`;
    if (data.summary) return data.summary;
    return JSON.stringify(data).substring(0, 50);
}

function clearEventLog() {
    document.getElementById('eventLog').innerHTML = '';
}

// Continue Handler
function handleReadyForNext(data) {
    const dialog = document.getElementById('continueDialog');
    const message = dialog.querySelector('.continue-message');
    const hint = dialog.querySelector('.continue-hint');
    const continueBtn = dialog.querySelector('.btn-continue');

    // Customize message based on whether this is first recording
    if (isFirstRecording) {
        message.textContent = '准备就绪！';
        hint.textContent = '点击下方按钮开始语音指令';
        continueBtn.innerHTML = '🎤 开始录音';
    } else {
        message.textContent = '任务已完成！';
        hint.textContent = '点击"继续"开始下一条指令';
        continueBtn.innerHTML = '▶️ 继续录音';
    }

    // Show continue dialog
    dialog.style.display = 'block';
}

function handleContinue(shouldContinue) {
    // Send continue signal to backend
    fetch('/api/continue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ continue: shouldContinue })
    });

    // Hide dialog
    document.getElementById('continueDialog').style.display = 'none';

    if (shouldContinue) {
        // After first recording starts, no longer first time
        isFirstRecording = false;
    } else {
        // If user chose to stop, show a message
        const container = document.getElementById('stepsContainer');
        container.innerHTML = '<div class="steps-empty">会话已结束</div>';
    }
}
