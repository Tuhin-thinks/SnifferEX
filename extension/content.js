// Content script for SnifferEx
console.log('SnifferEx content script loaded on:', window.location.href);

// Listen for messages from background script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Content script received message:', message);

    if (message.action === 'start-listening') {
        // Handle start listening command
        console.log('Starting WebSocket listener from content script');
        sendResponse({ success: true });
    }

    if (message.action === 'extract-data') {
        // Handle data extraction
        const result = extractData(message.selector, message.attribute, message.operation);
        sendResponse({ data: result });
    }

    return true;
});

// Data extraction functions
function extractData(selector, attribute, operation) {
    try {
        switch (operation) {
            case 'getAll':
                const elements = document.querySelectorAll(selector);
                const results = [];
                elements.forEach((element) => {
                    if (element[attribute]) {
                        results.push(element[attribute]);
                    }
                });
                return results;

            case 'getElemAttribute':
                const element = document.querySelector(selector);
                return element && element[attribute] ? element[attribute] : null;

            case 'innerHTML':
                const elem = document.querySelector(selector);
                return elem && elem[attribute] ? elem[attribute] : null;

            default:
                return null;
        }
    } catch (error) {
        console.error('Error extracting data:', error);
        return null;
    }
}

// Optional: Inject indicators or UI elements
function injectSnifferIndicator() {
    if (document.getElementById('sniffer-indicator')) return;

    const indicator = document.createElement('div');
    indicator.id = 'sniffer-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: #ff6b6b;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 9999;
        display: none;
    `;
    indicator.textContent = 'SnifferEx Active';
    document.body.appendChild(indicator);
}

// Initialize
injectSnifferIndicator();