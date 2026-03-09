// Sends popup actions to background so sockets survive popup close.
const triggerButton = document.getElementById("btn-trigger-server");
const statusElement = document.getElementById("status");

/** Renders short status text in popup UI. */
const setStatus = (text, isError = false) => {
    if (!statusElement) {
        return;
    }

    statusElement.textContent = text;
    statusElement.classList.toggle("text-danger", isError);
    statusElement.classList.toggle("text-success", !isError);
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
            return;
        }

        setStatus(`Listening on tab ${response.tabId}`);
        triggerButton?.classList.replace("btn-primary", "btn-danger");
    });
};

triggerButton?.addEventListener("click", startCurrentTabWebSocket);
