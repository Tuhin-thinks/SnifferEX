// Manages one WebSocket connection per started tab in MV3 background context.
const WEBSOCKET_URL = "ws://localhost:8765";
const SESSION_ID = "secret-session-id";

/** Tracks tabId -> WebSocket for active sniffing sessions. */
const tabSockets = new Map();

/** Resolves the active tab id for the current browser window. */
const getActiveTabId = async () => {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs[0]?.id ?? null;
};

/** Sends a JSON message when the socket is open. */
const sendSocketMessage = (socket, message) => {
    if (socket.readyState !== WebSocket.OPEN) {
        return;
    }
    socket.send(JSON.stringify(message));
};

/** Sends sniffing result payload back to backend server. */
const sendSniffingResult = (socket, result) => {
    sendSocketMessage(socket, {
        messageType: "sniffingResult",
        ...result,
    });
};

/** Injects one operation into a specific tab and returns extraction output. */
const injectJS = async ({ tabId, operation, selector, attribute, data }) => {
    const injectedFunctions = {
        getAll: (attributeName, cssSelector, selectIndex) => {
            let elements = document.querySelectorAll(cssSelector);
            if (selectIndex !== null) {
                elements = [elements[selectIndex]].filter(Boolean);
            }

            const result = {};
            const attributes = Array.isArray(attributeName)
                ? attributeName
                : [attributeName];

            elements.forEach((element) => {
                attributes.forEach((attr) => {
                    const value =
                        element.getAttribute(attr) ?? element[attr] ?? null;
                    if (value !== null) {
                        result[attr] = result[attr] || [];
                        result[attr].push(value);
                    }
                });
            });

            return result;
        },

        getElemAttribute: (attributeName, cssSelector, selectIndex) => {
            let elements = document.querySelectorAll(cssSelector);
            if (selectIndex !== null) {
                elements = [elements[selectIndex]].filter(Boolean);
            }
            if (elements.length === 0) {
                return null;
            }
            return (
                elements[0].getAttribute(attributeName) ??
                elements[0][attributeName] ??
                null
            );
        },

        innerHTML: (cssSelector, _attribute, selectIndex) => {
            let elements = document.querySelectorAll(cssSelector);
            if (selectIndex !== null) {
                elements = [elements[selectIndex]].filter(Boolean);
            }
            return elements.length > 0 ? elements[0].innerHTML : null;
        },
    };

    let resultArray = [];

    try {
        switch (operation) {
            case "getAll":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId },
                    func: injectedFunctions.getAll,
                    args: [attribute, selector, data.selectIndex ?? null],
                });
                break;

            case "getElemAttribute":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId },
                    func: injectedFunctions.getElemAttribute,
                    args: [attribute, selector, data.selectIndex ?? null],
                });
                break;

            case "innerHTML":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId },
                    func: injectedFunctions.innerHTML,
                    args: [selector, attribute, data.selectIndex ?? null],
                });
                break;

            case "scrollDown":
                await chrome.scripting.executeScript({
                    target: { tabId },
                    func: (cssSelector, scrollAmount, selectIndex) => {
                        const findScrollableChild = (element) => {
                            const children = element.querySelectorAll("*");
                            for (const child of children) {
                                const overflowY =
                                    window.getComputedStyle(child).overflowY;
                                const isScrollable =
                                    overflowY === "scroll" ||
                                    overflowY === "auto";
                                if (
                                    isScrollable &&
                                    child.scrollHeight > child.clientHeight
                                ) {
                                    return child;
                                }
                            }
                            return null;
                        };

                        if (!cssSelector) {
                            return null;
                        }

                        let selectedElements =
                            document.querySelectorAll(cssSelector);
                        let selectedElement = selectedElements[0] ?? null;
                        if (selectIndex !== null) {
                            selectedElement =
                                [selectedElements[selectIndex]].filter(
                                    Boolean,
                                )[0] ?? null;
                        }
                        if (!selectedElement) {
                            return null;
                        }

                        const scrollingElement =
                            findScrollableChild(selectedElement) ??
                            selectedElement;
                        scrollingElement.scrollBy(
                            0,
                            scrollAmount || scrollingElement.clientHeight,
                        );
                        return true;
                    },
                    args: [
                        data.selector,
                        data.amount,
                        data.selectIndex ?? null,
                    ],
                });
                break;

            case "clickElement":
                await chrome.scripting.executeScript({
                    target: { tabId },
                    func: (cssSelector) => {
                        const element = document.querySelector(cssSelector);
                        if (element) {
                            element.click();
                        }
                    },
                    args: [data.selector],
                });
                break;

            default:
                return null;
        }

        return resultArray.length > 0 ? (resultArray[0]?.result ?? null) : null;
    } catch (error) {
        console.error("SnifferEx injectJS failed:", error);
        return null;
    }
};

/** Executes a backend command against a specific tab and reports results. */
const executeSniffing = async (tabId, socket, commandData) => {
    const { selector, attribute, operation } = commandData;
    const result = await injectJS({
        tabId,
        operation,
        selector,
        attribute,
        data: commandData,
    });

    const ignoreResultOperations = ["scrollDown", "clickElement"];
    if (ignoreResultOperations.includes(operation)) {
        return;
    }

    sendSniffingResult(
        socket,
        result ? { data: result } : { data: null, error: "No result found" },
    );
};

/** Closes and removes the socket for a tab when it exists. */
const stopWebSocketForTab = (tabId) => {
    const socket = tabSockets.get(tabId);
    if (!socket) {
        return false;
    }

    socket.close();
    tabSockets.delete(tabId);
    return true;
};

/** Binds socket event handlers for command processing and cleanup. */
const attachSocketHandlers = (tabId, socket) => {
    socket.onopen = () => {
        console.debug(`SnifferEx WebSocket opened for tab ${tabId}`);
        sendSocketMessage(socket, 
            { role: "browser", session: SESSION_ID, tabId }
        );
    };

    socket.onmessage = async ({ data }) => {
        try {
            const parsedData = JSON.parse(data);
            if (parsedData.command === "sniff") {
                await executeSniffing(tabId, socket, parsedData);
                return;
            }
            if (parsedData.command === "stop") {
                stopWebSocketForTab(tabId);
                return;
            }
            console.warn(
                "SnifferEx received unknown command:",
                parsedData.command,
            );
        } catch (error) {
            console.error("SnifferEx failed to parse socket message:", error);
        }
    };

    socket.onerror = (event) => {
        console.error(`SnifferEx WebSocket error for tab ${tabId}:`, event);
    };

    socket.onclose = () => {
        if (tabSockets.get(tabId) === socket) {
            tabSockets.delete(tabId);
        }
        console.debug(`SnifferEx WebSocket closed for tab ${tabId}`);
    };
};

/** Starts a WebSocket for a tab unless one is already active or connecting. */
const startWebSocketForTab = (tabId) => {
    const existingSocket = tabSockets.get(tabId);
    if (
        existingSocket &&
        (existingSocket.readyState === WebSocket.OPEN ||
            existingSocket.readyState === WebSocket.CONNECTING)
    ) {
        return { started: false, reason: "already-active" };
    }

    const socket = new WebSocket(WEBSOCKET_URL);
    tabSockets.set(tabId, socket);
    attachSocketHandlers(tabId, socket);
    return { started: true };
};

chrome.runtime.onInstalled.addListener((details) => {
    console.log("SnifferEx installed/updated:", details.reason);
});

/** Handles popup and internal messages that control websocket lifecycle. */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
        if (message.type === "start-ws") {
            const tabId = message.tabId ?? (await getActiveTabId());
            if (tabId === null) {
                sendResponse({ ok: false, error: "No active tab found" });
                return;
            }

            const result = startWebSocketForTab(tabId);
            sendResponse({ ok: true, tabId, ...result });
            return;
        }

        if (message.type === "stop-ws") {
            const tabId =
                message.tabId ?? sender.tab?.id ?? (await getActiveTabId());
            if (tabId === null) {
                sendResponse({ ok: false, error: "No active tab found" });
                return;
            }
            const stopped = stopWebSocketForTab(tabId);
            sendResponse({ ok: stopped, tabId });
            return;
        }

        if (message.type === "ws-status") {
            const tabId = message.tabId ?? (await getActiveTabId());
            if (tabId === null) {
                sendResponse({
                    ok: false,
                    connected: false,
                    state: "missing-tab",
                });
                return;
            }

            const socket = tabSockets.get(tabId);
            const state = socket ? socket.readyState : WebSocket.CLOSED;
            sendResponse({
                ok: true,
                tabId,
                connected: state === WebSocket.OPEN,
                state,
            });
        }
    })().catch((error) => {
        console.error("SnifferEx runtime message handler failed:", error);
        sendResponse({ ok: false, error: String(error) });
    });

    return true;
});

/** Supports keyboard command start-listening (Alt+L) on the active tab. */
chrome.commands.onCommand.addListener(async (command) => {
    if (command === "start-listening") {
        const tabId = await getActiveTabId();
        if (tabId !== null) {
            startWebSocketForTab(tabId);
        }
        return;
    }

    if (command === "stop-listening") {
        const tabId = await getActiveTabId();
        if (tabId !== null) {
            stopWebSocketForTab(tabId);
        }
    }
});

/** Ensures only the closed tab's socket is shut down on tab removal. */
chrome.tabs.onRemoved.addListener((tabId) => {
    stopWebSocketForTab(tabId);
});
