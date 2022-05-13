var endpoint = null
var socket = null
var loc = window.location

var wsProtocol = 'ws'
if (loc.protocol === 'https:') {
    wsProtocol = 'wss';
}

function connect() {
    endpoint = `${wsProtocol}://${loc.host}/websocket/grid_id=${currentState.grid_id}`
    console.log(endpoint)
    socket = new WebSocket(endpoint)
    socket.onmessage = function (e) {
        console.log('Message', e)
        let data = JSON.parse(e.data)
        if (data.type == 'update') {
            updateFullMeta(data.fullmeta)
            if (data.fullmeta.atlas == undefined) {
                let svgToUpdate = { ...data.fullmeta.squares, ...data.fullmeta.holes }
                svgUpdate(svgToUpdate)
                populateReportHead()
                return
            } else if (data.fullmeta.atlas[Object.keys(data.fullmeta.atlas)[0]].status == 'completed') {
                reportMain()
                return
            }
        }
        else if (data.type == 'reload') {
            loadSVG(data, $(`#main ${data.element}`))
        } else {
            console.log(data)
        }
    }
    socket.onopen = function (e) {
        console.log('Open', e)
    }
    socket.onerror = function (e) {
        console.log('Error', e)
    }
    socket.onclose = function (e) {
        console.log('Close', e)
        if (fullmeta && fullmeta.status != 'complete') {
            console.log('Grid status is incomplete, trying to reconnect websocket')
            setTimeout(function () {

                connect();
            }, 5000);
        }
    };
}


function websocketMain() {
    if (socket !== null) {
        console.log("Closing socket connection")
        socket.close()
        socket = null
    }
    // fullmeta && fullmeta.status != 'complete' && 
    if (socket == null) {
        console.log('connecting to websocket')
        connect()
    }
    // } else {
    //     console.log('Grid is complete, socket connection not required')
    // }

}

function websocketSend(type, data) {
    if (socket.readyState === WebSocket.OPEN) {
        console.log("Socket is opened, sending message")
        socket.send(JSON.stringify({
            'type': type,
            'data': data
        }))
    } else {
        console.log("Socket not opened, cannot send")
    }
}