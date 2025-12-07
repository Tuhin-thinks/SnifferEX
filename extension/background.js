// Background service worker for SnifferEx (Manifest V3)
console.log('SnifferEx background service worker loaded');
console.debug("SnifferEx.js loaded (Brave compatible)");
var ws = null;
var sessionID = "secret-session-id";

/**
 * Function to connect to the running websocket server.
 */
const connectWebSocket = async () => {
    console.debug("connectWebSocket() called");

    // Use chrome.tabs instead of browser.tabs
    const activeTabs = await chrome.tabs.query({
        active: true,
        currentWindow: true,
    });
    const currentTabURL = activeTabs[activeTabs.length - 1].url;
    console.debug("currentTabURL: ", currentTabURL);

    // connect websocket
    ws = new WebSocket("ws://localhost:8765");
    ws.onopen = (event) => {
        console.debug("websocket connection opened");
        sendMessage({
            message: { role: "browser", session: sessionID },
        });
    };
    receiveCommands(ws);
    socketError(ws);
};


// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    console.log('SnifferEx extension installed/updated:', details.reason);
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "start-ws") {
    connectWebSocket();
    sendResponse({ ok: true });
  }
});