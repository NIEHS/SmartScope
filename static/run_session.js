const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value
var interval = null

async function loadlogs() {
    console.log('SENDING REQUEST!')
    let url = `/api/sessions/${session_id}/get_logs`
    data = await apifetchAsync(url, null, 'GET')
    console.log(data)
    if (data.reload === true) {
        location.reload();
    }
    queue = document.getElementById('queue')
    queue.innerHTML = data.queue
    out = document.getElementById('out')
    out.innerHTML = data.out
    proc = document.getElementById('proc')
    proc.innerHTML = data.proc
    elements = [out, proc]
    for (const i in elements) {
        console.log(i, elements[i])
        elements[i].scrollTop = elements[i].scrollHeight;
    }
    disk.innerHTML = `Hard drive: ${data.disk[0]} GB total, ${data.disk[1]} GB free, ${data.disk[2]}% full`
    isPaused(data.paused)
    isStopFile(data.is_stop_file)
    setPause(data)
}

async function startSession(start = true) {
    let url = `/api/sessions/${session_id}/run_session/`
    var str = 'stop'
    if (start === true) {
        str = 'start'
    }
    var r = confirm(`Do you want to ${str} this session?`);
    if (r == true) {
        console.log("starting")
        response = await apifetchAsync(url, { 'start': start }, 'POST');
        return response
    } else {
        console.log("Cancel")
    }

}


async function togglePause() {
    console.log('toggling pause')
    let url = `/api/sessions/${session_id}/pause_between_grids/`
    resp = await apifetchAsync(url, { 'pause': '' }, 'PUT');
    setPause(resp)
    console.log('Response:', resp)

}

async function continueRun(value) {
    let url = `/api/sessions/${session_id}/continue_run/`
    resp = await apifetchAsync(url, { 'continue': value }, 'PUT');
    isPaused(resp)
    console.log('Response:', resp)

}

function setPause(data) {
    pause = document.getElementById('pause')
    pause.classList.remove('btn-outline-success')
    pause.classList.remove('btn-outline-danger')
    console.log(data.pause)
    if (data.pause === true) {
        pause.classList.add('btn-outline-success')
    } else {
        pause.classList.add('btn-outline-danger')
    }
}

function isStopFile(data) {
    console.log('Is Stop File?', data)

    if (data == true) {
        $('#stopSignal').removeClass('d-none')
        return
    }
    $('#stopSignal').addClass('d-none')

}

function isPaused(paused) {
    paused_div = document.getElementById('paused')
    if (paused === true) {
        paused_div.classList.remove('hidden')
    } else {
        paused_div.classList.add('hidden')
    }
}

function autoRefresh(enable = true) {
    if (enable === true) {
        console.log('Autorefresh enabled')
        interval = setInterval(function () {
            console.log("Refreshing!")
            loadlogs()
        }
            , 10000);
        return
    }
    console.log('Autorefresh disabled')
    clearInterval(interval);
};

async function checkIsRunning(element, response = null) {
    let url = `/api/sessions/${session_id}/check_is_running/`
    if (response === null) {
        response = await apifetchAsync(url, null, 'GET')
    }
    if (response.status === 'running') {
        element.className = 'btn btn-outline-danger'
        element.value = 'stop'
        element.innerHTML = 'Stop'
        autoRefresh()
        return response
    }
    element.className = 'btn btn-outline-primary'
    element.value = 'start'
    element.innerHTML = 'Start'
    autoRefresh(enable = false)
    return response
};

$(document).ready(async function () {
    loadlogs(); run_status = await checkIsRunning(document.getElementById('start-button')); console.log(run_status)
});

$('#start-button').on('click', async function () {
    console.log(this)
    let val = (this.value === "start");
    run_status = await startSession(val);
    await checkIsRunning(this, response = run_status);
    console.log(run_status)
})

$('#force-start-button').on('click', async function () {
    console.log(this)
    let val = (this.value === "start");
    run_status = await startSession(val);
})

$('#removeLockButton, #forceKill').on('click', async function () {
    console.log(`Running ${this.value}`)
    let url = `/api/sessions/${session_id}/${this.value}/`
    data = await apifetchAsync(url, null, 'POST')
    console.log(data)
})

// $('#stop-button').on('click', function () { start(start = false);is_running=false; checkIsRunning()})
$('#pause').on('click', function () { togglePause() })
$('#continue-next, #continue').on('click', function () { console.log(this, this.value); continueRun(this.value) })

