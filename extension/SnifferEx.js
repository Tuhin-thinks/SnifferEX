console.debug('SnifferEx.js loaded');
var ws = null;

/**
 * Function to connect to the running websocket server.
 */
const connectWebSocket = async () => {
    console.debug('connectWebSocket() called');

    const activeTabs = await browser.tabs.query({ active: true });
    const currentTabURL = activeTabs[activeTabs.length - 1].url;
    console.debug('currentTabURL: ', currentTabURL);

    // // connect websocket
    ws = new WebSocket('ws://localhost:8765');
    ws.onopen = (event) => {
        console.debug('websocket connection opened');
        sendMessage({
            message: `Hello from client, I am ready to receive commands: ${currentTabURL}`,
        });
    };
    receiveCommands(ws);
    socketError(ws);
};

const receiveCommands = (ws) => {
    ws.onmessage = async ({ data }) => {
        console.debug('received command: ', data);
        const parsedData = JSON.parse(data);
        if (parsedData.command === 'sniff') {
            console.log('sniffing command received');
            await executeSniffing(ws, parsedData);
        } else if (parsedData.command === 'stop') {
            stopSniffing();
        } else {
            console.log('Unknown command received: ', parsedData.command);
        }
    };
};

const socketError = (ws) => {
    ws.onerror = (event) => {
        console.error('websocket error: ', event);
    };
};

const sendMessage = ({ message }) => {
    ws.send(JSON.stringify(message));
    console.debug('message sent: ', message);
};

/**
 *
 * @param {*} ws
 * @param {Object} result
 */
const sendSniffingResult = (ws, result) => {
    ws.send(
        JSON.stringify({
            messageType: 'sniffingResult',
            ...result,
        })
    );
};

/**
 *
 * @param Object{
 *
 * selector: string: css selector.;
 * attribute: string: attribute name.;
 * data: Object: for executeScript() function, data has the script to be executed.;
 *
 * }
 * @returns
 */
const injectJS = async ({ operation, selector, attribute, data }) => {
    function getAll(attribute, selector) {
        const elements = document.querySelectorAll(selector);
        result = [];
        elements.forEach((element) => {
            if (element[attribute]) {
                result.push(element[attribute]);
            }
        });
        return result;
    }

    function getElemAttribute(attribute, selector) {
        const element = document.querySelector(selector);
        if (element[attribute]) {
            return element[attribute];
        }
    }

    function innerHTML(selector, attribute) {
        const innerHTML = document.querySelector(selector)[attribute];
        return innerHTML;
    }

    let resultArray = [];

    // inject the script into the page, based on the value of the operation parameter
    switch (operation) {
        case 'getAll':
            resultArray = await browser.tabs.executeScript({
                code: '(' + getAll + `)('${attribute}', '${selector}')`,
            });
            break;

        case 'getElemAttribute':
            const _codeString =
                '(' + getElemAttribute + `)('${attribute}', '${selector}')`;
            console.debug(_codeString);

            resultArray = await browser.tabs.executeScript({
                code: _codeString,
            });
            break;

        case 'innerHTML':
            resultArray = await browser.tabs.executeScript({
                code: '(' + innerHTML + `)('${attribute}', '${selector}')`,
            });
            break;

        case 'executeScript':
            resultArray = await browser.tabs.executeScript({
                code: '(' + data.script + `)('${attribute}', '${selector}')`,
            });
            break;
    }

    return resultArray[0];
};

const executeSniffing = async (ws, data) => {
    const { selector, attribute, operation } = data;

    const result = await injectJS({ operation, selector, attribute, data });

    sendSniffingResult(
        ws,
        result ? { data: result } : { data: null, error: 'No result found' }
    );
};

const stopSniffing = () => {
    console.debug('stopSniffing() called');

    if (ws) {
        ws.close();
        ws = null;
    }
};

try {
    document
        .getElementById('btn-trigger-server')
        .addEventListener('click', connectWebSocket);
    function turnRed() {
        document
            .getElementById('btn-trigger-server')
            .classList.remove('btn-primary');
        document
            .getElementById('btn-trigger-server')
            .classList.add('btn-danger');
    }

    turnRed(); // turn button color red
} catch (error) {
    console.error(
        'Error while trying to add evenListeners on button,\nerror: ',
        error
    );
} finally {
}

const startListening = async (command) => {
    if (command === 'start-listening') {
        await connectWebSocket();
    } else if (command === 'stop-listening') {
        stopSniffing();
    }
};

/**
 * Alt+Shift+L then Alt+L should activate the websocket listener, and make it listen for incoming commands
 */
browser.commands.onCommand.addListener(startListening);
