// Sends popup actions to background so sockets survive popup close.
const triggerButton = document.getElementById("btn-trigger-server");
const statusElement = document.getElementById("status");
const socketStateLabels = {
    0: "connecting",
    1: "open",
    2: "closing",
    3: "closed",
};

/** Renders short status text in popup UI. */
const setStatus = (text, isError = false) => {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = text;
    statusElement.classList.toggle("text-danger", isError);
    statusElement.classList.toggle("text-success", !isError);
};

/** Updates button style to reflect whether current tab is already listening. */
const setListeningUi = (isListening) => {
    if (!triggerButton) {
        return;
    }

    triggerButton.classList.toggle("btn-danger", isListening);
    triggerButton.classList.toggle("btn-primary", !isListening);
};

/** Reads websocket status for active tab so popup reopen reflects real background state. */
const refreshCurrentTabStatus = () => {
    chrome.runtime.sendMessage({ type: "ws-status" }, (response) => {
        if (chrome.runtime.lastError) {
            setStatus(`Error: ${chrome.runtime.lastError.message}`, true);
            setListeningUi(false);
            return;
        }

        if (!response?.ok) {
            setStatus(response?.error || "Status unavailable", true);
            setListeningUi(false);
            return;
        }

        const stateLabel = socketStateLabels[response.state] || "unknown";
        const isConnected = response.state === 1;
        setListeningUi(isConnected);

        if (isConnected) {
            setStatus(`Listening on tab ${response.tabId}`);
            return;
        }

        if (response.state === 0 || response.state === 2) {
            setStatus(`Tab ${response.tabId} is ${stateLabel}`);
            return;
        }

        setStatus(`Ready (tab ${response.tabId})`);
    });
};

/** Requests websocket start for the currently active tab. */
const startCurrentTabWebSocket = () => {
    chrome.runtime.sendMessage({ type: "start-ws" }, (response) => {
        if (chrome.runtime.lastError) {
            setStatus(`Error: ${chrome.runtime.lastError.message}`, true);
            return;
        }

        if (!response?.ok) {
            setStatus(response?.error || "Unable to start", true);
            return;
        }

        if (response.reason === "already-active") {
            setStatus(`Already active on tab ${response.tabId}`);
            setListeningUi(true);
            return;
        }

        setStatus(`Listening on tab ${response.tabId}`);
        setListeningUi(true);
    });
};

triggerButton?.addEventListener("click", startCurrentTabWebSocket);
refreshCurrentTabStatus();
