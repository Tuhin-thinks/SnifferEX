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
        console.log("websocket connection opened");
        sendMessage({
            message: { role: "browser", session: sessionID },
        });
    };
    receiveCommands(ws);
    socketError(ws);
};

const receiveCommands = (ws) => {
    ws.onmessage = async ({ data }) => {
        console.debug("received command: ", data);
        const parsedData = JSON.parse(data);
        if (parsedData.command === "sniff") {
            console.log("sniffing command received");
            await executeSniffing(ws, parsedData);
        } else if (parsedData.command === "stop") {
            stopSniffing();
        } else {
            console.log("Unknown command received: ", parsedData.command);
        }
    };
};

const socketError = (ws) => {
    ws.onerror = (event) => {
        console.error("websocket error: ", event);
    };
};

const sendMessage = ({ message }) => {
    ws.send(JSON.stringify(message));
    console.debug("message sent: ", message);
};

/**
 *
 * @param {*} ws
 * @param {Object} result
 */
const sendSniffingResult = (ws, result) => {
    ws.send(
        JSON.stringify({
            messageType: "sniffingResult",
            ...result,
        })
    );
};

/**
 * Inject JavaScript using Manifest V3 chrome.scripting API
 * @param Object{
 * operation: string: operation type;
 * selector: string: css selector;
 * attribute: string: attribute name;
 * data: Object: for executeScript() function, data has the script to be executed;
 * }
 * @returns
 */
const injectJS = async ({ operation, selector, attribute, data }) => {
    // Define the functions that will be injected
    const injectedFunctions = {
        getAll: (attribute, selector) => {
            const elements = document.querySelectorAll(selector);
            let result = {};
            // check if attribute is a list of attributes (else make it a list with single attribute)
            const attributes_list = Array.isArray(attribute)
                ? attribute
                : [attribute];

            elements.forEach((element) => {
                attributes_list.forEach((attr) => {
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

        getElemAttribute: (attribute, selector) => {
            const element = document.querySelector(selector);
            if (element && element[attribute]) {
                return element[attribute];
            }
            return null;
        },

        innerHTML: (selector, attribute) => {
            const element = document.querySelector(selector);
            if (element && element[attribute]) {
                return element[attribute];
            }
            return null;
        },
    };

    let resultArray = [];
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tabId = tabs[0].id;

    try {
        // Use chrome.scripting.executeScript instead of browser.tabs.executeScript
        switch (operation) {
            case "getAll":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    func: injectedFunctions.getAll,
                    args: [attribute, selector],
                });
                break;

            case "getElemAttribute":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    func: injectedFunctions.getElemAttribute,
                    args: [attribute, selector],
                });
                break;

            case "innerHTML":
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    func: injectedFunctions.innerHTML,
                    args: [selector, attribute],
                });
                break;

            case "executeScript":
                // For custom scripts, we need to eval them (be careful with security)
                const customFunction = new Function(
                    "attribute",
                    "selector",
                    data.script
                );
                resultArray = await chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    func: customFunction,
                    args: [attribute, selector],
                });
                break;
        }

        if (resultArray && resultArray.length > 0) {
            return resultArray[0]?.result || null;
        } else {
            return null;
        }
    } catch (error) {
        console.error("Error executing script:", error);
        return null;
    }
};

const executeSniffing = async (ws, data) => {
    const { selector, attribute, operation } = data;

    const result = await injectJS({ operation, selector, attribute, data });

    sendSniffingResult(
        ws,
        result ? { data: result } : { data: null, error: "No result found" }
    );
};

const stopSniffing = () => {
    console.debug("stopSniffing() called");

    if (ws) {
        ws.close();
        ws = null;
    }
};

// Popup script handling
try {
    document
        .getElementById("btn-trigger-server")
        ?.addEventListener("click", connectWebSocket);

    function turnRed() {
        const button = document.getElementById("btn-trigger-server");
        if (button) {
            button.classList.remove("btn-primary");
            button.classList.add("btn-danger");
        }
    }

    turnRed(); // turn button color red
} catch (error) {
    console.error(
        "Error while trying to add eventListeners on button,\nerror: ",
        error
    );
}

const startListening = async (command) => {
    console.debug("startListening() called with command: ", command);
    if (command === "start-listening") {
        await connectWebSocket();
    } else if (command === "stop-listening") {
        stopSniffing();
    }
};

/**
 * Alt+Shift+L then Alt+L should activate the websocket listener, and make it listen for incoming commands
 */
if (chrome.commands) {
    console.log("Registering command listener for chrome.commands");
    chrome.commands.onCommand.addListener(startListening);
}
