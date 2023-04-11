var url = window.location.href;
var currentState = new Object



var pathname = new URL(url).pathname;

path = pathname.split('/')

function delay(fn, ms) {
    let timer = 0
    return function(...args) {
      clearTimeout(timer)
      timer = setTimeout(fn.bind(this, ...args), ms || 0)
    }
  }

function selected() {
    $('.active', '#sidebar-container').removeClass('active');
    for (const [key, val] of Object.entries(currentState)) {
        // console.log(`${key}, ${val}`)
        if (['group', 'session_id', 'grid_id'].includes(key) && val !== undefined) {
            $(`#${val}`).addClass('active')
        }
    }
}



async function loadSidePanelState() {
    await loadSidePanel(null, null, push = false)
    for (const [key, val] of Object.entries(currentState)) {
        // console.log(`${key}, ${val}`)
        if (['group', 'session_id'].includes(key) && val !== undefined) {
            await loadSidePanel(key, val, push = false)
        } else if (key == 'grid_id') {
            await loadReport(key, val, push = false)
        }
    }
}

function pushState() {
    var string = "?"
    for (const [key, value] of Object.entries(currentState)) {
        string += `${key}=${value}&`;
    }
    window.history.replaceState(currentState, document.title, pathname + string)
}

function updateFullMeta(data) {
    console.log(data)
    fullmeta = {
        ...fullmeta, ...data,
        atlas: { ...fullmeta.atlas, ...data.atlas },
        squares: { ...fullmeta.squares, ...data.squares },
        holes: { ...fullmeta.holes, ...data.holes }
    }
    console.log(fullmeta)
}

let idGen = () => {
    return Math.floor((1 + Math.random()) * 0x10000)
        .toString(16)
        .substring(1);
}

let createLoadingMessage = (message) => {
    let id = idGen()
    $('#loadingMessages').append(
        `<div class="notification d-inline-flex justify-content-end">
            <div id="${id}" class="alert mb-0 mt-1 alert-primary fade show" role="alert">
                <span>${message}</span>
            </div>
        </div>`)
    return id
}

let processLoadingMessage = (response, id) => {
    if (response.ok) {
        $(`#loadingMessages #${id}`).removeClass('alert-primary').addClass('alert-success')
        setTimeout(function() {
            $(`#loadingMessages #${id}`).alert('close');
            $(`#loadingMessages #${id}`).parent().remove()
        }, 2000);
    } else {
        $(`#loadingMessages #${id}`).removeClass('alert-primary').addClass('alert-danger')
    }
}

async function fetchAsync(url, message='alert') {
    let id = createLoadingMessage(message)
    let response = await fetch(url);
    processLoadingMessage(response,id)
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
        return response.json()
    } else {
        return response.text()
    }
};


async function apifetchAsync(url, dict, method, message='alert!') {
    content = {
        method: method,
        headers: {
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'mode': 'same-origin'
        },
    }
    let id = createLoadingMessage(message)
    if (dict != null) {
        content.body = JSON.stringify(dict)
    }
    let response = await fetch(url, content);
    processLoadingMessage(response,id)
    let data = await response.json();
    return data;
};

function pickHex(color1, color2, min, max, val) {
    var value = (val - min) / (max - min)
    var p = Math.min.apply(null, [1, value]);
    console.log(value, p)
    var w = p * 2 - 1;
    var w1 = (w / 1 + 1) / 2;
    var w2 = 1 - w1;
    var rgb = [Math.round(color1[0] * w1 + color2[0] * w2),
    Math.round(color1[1] * w1 + color2[1] * w2),
    Math.round(color1[2] * w1 + color2[2] * w2)];
    return rgb;
}

function arrayRemove(arr, value) {

    return arr.filter(function (ele) {
        return ele != value;
    });
}

async function updateTarget(type, ids, key, new_value, useAPI = false) {
    console.log(`UPDATING ${type}, ${ids}, ${key} to ${new_value}`)

    var dict = {}
    dict['key'] = key
    dict['new_value'] = new_value
    dict['type'] = type
    dict['ids'] = ids
    console.log(dict)
    var url = `/api/updatetargets/`
    if (socket !== null) {
        if (socket.readyState !== WebSocket.OPEN) {
            console.log('Websocket closed, cannot run update')

        } else {
            console.log('Using websocket')
            return await websocketSend('update.target', dict)
        }
    }
    if (useAPI) {
        console.log('Running api')
        return await apifetchAsync(url, dict, "PATCH")
    }
}

function checkState() {

    var state = url.match(/([a-zA-Z_]+)=([a-zA-Z0-9-_%]*)/g)
    if (state != null) {
        for (i in state) {
            var split = state[i].split('=')
            currentState[split[0]] = split[1]
        }
    }
    console.log(currentState)
}

async function loadSidePanel(requestfield = null, id = null, push = true) {
    const loadInto = { 'group': 'sidebarSessions', 'session_id': 'sidebarGrids' }
    var loadinto = 'sidebarGroups'
    var url = "/api/sidepanel/"
    if (requestfield !== null) {
        url += `?${requestfield}=${id}`
        currentState[requestfield] = id
        loadinto = loadInto[requestfield]
    }
    console.log(url, push)
    let models = await fetchAsync(url, message=`Loading ${requestfield}.`)
    $(`#${loadinto}`).html(models)

    if (push) {
        pushState()
        selected()
    }
}

async function loadReport(requestfield = null, id = null, push = true) {
    console.log(`Loading report for grid: ${requestfield}, ${id}, ${push}`)
    var url = `/api/report/?grid_id=${id}`
    console.log(url)
    var report = await fetchAsync(url,message=`Loading report for grid ${id}`)
    console.log('Previous grid:', currentState.grid_id)
    if (currentState.grid_id && currentState.grid_id != id) {
        console.log('Resetting hole and square state')
        delete currentState['hole']
        delete currentState['square']
        delete currentState['squareMethod']
        delete currentState['squareDisplayType']
        delete currentState['atlasMethod']
        delete currentState['atlasDisplayType']
    }

    currentState[requestfield] = id
    if (push) {
        console.log('Pushing state')
        pushState()
        selected()
    }
    $(`#main`).html(report)
    if (typeof csrftoken == 'undefined') {
        console.log('loading script', reportscript, typeof csrftoken)
        $.getScript(reportscript);
        $.getScript(websocketscript);
        while (typeof csrftoken == 'undefined') {
            console.log('loading script', typeof csrftoken)
            await new Promise(r => setTimeout(r, 500));
        }
    }

    await reportMain()
    websocketMain()
    htmx.process(htmx.find('#main'))
}


