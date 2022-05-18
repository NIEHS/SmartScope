var loadedHoles = []
var loadedImages = []
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const preload = 10
var hmSelection = null
var loading = false
var imageError = false
var count = null
var socket = null

async function preloadMic(data) {
    var mic = new Image();
    mic.id = 'mic'
    mic.src = data.png.url;
    mic.className = 'mw-100 mh-100';
    mic.onerror = imageLoadError

    var ctf = new Image();
    if (data.ctffit !== null) {
        ctf.src = data.ctf_img;
    } else {
        let fft = await fetchAsync(`/api/highmag/${element.id}/fft/`)
        ctf.src = `data:image/png;charset=utf-8;base64,${fft.img}`
    }
    ctf.id = 'fftImg'
    ctf.ctf_img = 'mw-100 mh-100';
    loadedImages.push([mic, ctf])

}

function imageLoadError() {
    console.log('Image not found')
    imageError = true
}

async function preloadNext() {
    let numToLoad = preload - loadedHoles.length
    if (numToLoad > 0) {
        loading = true
        console.log(`Loading ${numToLoad} new micrographs`)
        let url = `/api/holes/preload_highmag/?number=${numToLoad}&grid_id=${currentState.grid_id || ''}&format=json`

        let datacount = await fetchAsync(url)
        count = datacount.count
        let data = datacount.data
        tickCount(0)
        for (i in data) {
            await preloadMic(data[i].high_mag)
            loadedHoles.push(data[i])
        }
        console.log(loadedHoles, loadedImages)
        loading = false
        return
    }
    console.log(`Already ${preload} micrographs loaded`)
}

function loadMicrograph() {

    hmSelection = loadedHoles.shift()['high_mag']
    let images = loadedImages.shift()

    console.log('Hm selection =', hmSelection)
    console.log(images)

    document.getElementById('hm_name').innerHTML = hmSelection.name
    $('#mic').replaceWith(images[0])
    $('#fftImg').replaceWith(images[1])
    if (hmSelection.ctffit !== null) {
        document.getElementById('defocus').innerHTML = `Defocus: ${Math.round(hmSelection.defocus / 1000) / 10} &microm`
        document.getElementById('astig').innerHTML = `Astig: ${Math.round(hmSelection.astig)} A`
        document.getElementById('ctffit').innerHTML = `CTFfit: ${Math.round(hmSelection.ctffit * 100) / 100} A`


    }
}

function tickCount(value) {
    count += value
    $('#count').text(count)
}

$('#hmQuality').on('click', async function (e) {
    console.log(hmSelection)
    if (e.target.value == 'skip') {
        console.log('Skipping image')

    } else {
        await updateTarget('holes', [hmSelection.hole_id], 'quality', e.target.value, useAPI = true)
        tickCount(-1)

    }
    loadMicrograph()
    if (loadedImages.length < 5 && loading == false) {
        await preloadNext()
    }
})

$(document).ready(async function () {
    var currentState = checkState()
    await preloadNext()
    await loadMicrograph()

})
