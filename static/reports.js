
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value

function escapeRegExp(string) {
    return string.match(/(\d+)$/g); // $& means the whole matched string
};


async function loadSVG(data, element) {
    console.log(data, element)
    if (data['fullmeta'] !== null) {
        var targets = data['targets']
        if ("svg" in data) {
            element.html(data['svg'])
        }
        updateFullMeta(data['fullmeta'])
        grabCuration()
    }
}

function svgUpdate(svgToUpdate) {
    for (const [key, value] of Object.entries(svgToUpdate)) {
        console.log(key, value)
        setSVGcss(value, document.getElementById(key))
    }
}

function setSVGcss(item, el) {
    if (el.classList.contains('clicked')) {
        el.classList.remove(...el.classList);
        el.classList.add('clicked')
    } else {
        el.classList.remove(...el.classList);
    }
    if (item.has_active) {
        el.classList.add('has_active')
    } else if (item.has_queued) {
        el.classList.add('has_queued')
    }
    else if (item.has_completed) {
        el.classList.add('has_completed')
    }


    if (item.class_num === undefined) {
        el.classList.add(item.quality)
    } else {
        if (item.quality !== null && item.quality.length == 1) {
            el.classList.add(`quality-${item.quality}`)
        } else if (item.quality == 'bad') {
            el.classList.add(`quality-4`)
        } else {
            if (item.class_num != null) {
                el.classList.add(`class_${item.class_num}`)
            } else {
                el.classList.add(`class_0`)
            }
        }
    }
    if (item.status !== null) {
        el.classList.add(item.status)

        $(`#${item.id}_text`).removeClass(['queued', 'started', 'acquired', 'processed', 'targets_picked']).addClass(item.status)
    }
    if (item.bis_type === "is_area") {
        el.classList.add('is_area')
    }

};

async function queueSquareTargets(elem) {
    var url = `/api/squares/${currentState.square}/all/`
    console.log(url)
    await apifetchAsync(url, { 'action': elem.value }, "PATCH", message=`Adding all target to queue for ${currentState.square}`);
    loadSquare(currentState.square)
}



async function loadAtlas(metaonly = false, display_type = null, method = null) {
    var url = `/api/atlas/${Object.keys(fullmeta.atlas)[0]}/load/?format=json&display_type=${display_type}&method=${method}&metaonly=${metaonly}`
    console.log(url)
    const data = await fetchAsync(url, message='Loading Atlas');
    currentState['atlasDisplayType'] = data.displayType
    currentState['atlasMethod'] = data.method
    loadSVG(data, generalElements.atlas)
    $("#Atlas_div").html(data.card)
    pushState()

};

$('#main').on("mouseenter mouseleave", '.legend', function () {
    $(this).closest('.mapCard').find(`[label='${$(this).attr('label')}']`).toggleClass('hovered')
})
$('#main').on("click", '.legend', function () {
    let card = $(this).closest('.mapCard')
    let elems = card.find(`[label=${$(this).attr('label')}]`)
    for (elem of elems) {
        sele = squareSelection
        console.log(card.attr('targets'))
        if (card.attr('targets') == 'hole') {

            sele = holeSelection
        }
        selectElement(elem, sele)
        checkSelection(card.attr('targets'))
    }
})

$('#main').on('click', '.showLegend', function () {
    console.log($(this), $(this).closest('.mapCard'))
    $(this).closest('.mapCard').find('#legend, #scaleBar').toggleClass('d-none')
})

// $("#main").find(".hasTooltip").tooltip();


function selectElement(elem, selection) {
    if (selection.includes(elem.id)) {
        console.log('Unselecting')
        elem.classList.remove('clicked')
        var selection = selection.splice(selection.indexOf(elem.id), 1)

    } else {
        selection.push(elem.id)
        elem.classList.add('clicked')
    }
    console.log(holeSelection, squareSelection)
};

function checkSelection(type = 'square') {
    var selection = squareSelection
    var menuBtn = '#squareSeleMenuBtn'
    var clearBtn = '#squareClearSele'
    if (type == 'hole') {
        selection = holeSelection
        menuBtn = '#holeSeleMenuBtn'
        clearBtn = '#holeClearSele'
    } else if (type == 'targets') {
        selection = targetsSelection
        menuBtn = '#addTargetsBtn'
        clearBtn = '#clearTargets'
    }

    if (selection.length > 0) {
        $(menuBtn).removeClass("disabled")
        $(clearBtn).removeClass("disabled")
        return
    }
    $(menuBtn).addClass("disabled")
    $(clearBtn).addClass("disabled")

}


function clearSelection(selection, type) {
    console.log(`Clearing Selection`)

    if (type == 'hole') {
        button = $('#holeClearSele')
    } else if (type == 'targets') {
        button = $('#clearTargets')
    } else {
        button = $('#squareClearSele')
    }
    while (selection.length != 0) {
        if (type != 'targets') {
            document.getElementById(selection[0]).classList.remove('clicked')
        } else {
            selection[0][0].remove()
        }

        selection.shift()
    }
    button.prop("disabled", true)
    popup_sele = null
    checkSelection(type)
}

async function loadSquare(full_id, metaonly = false, display_type = null, method = null) {
    console.log('Loading Square:', full_id)
    let meta = fullmeta.squares[full_id]

    if (meta.status == 'completed') {
        var url = `/api/squares/${meta.id}/load/?format=json&display_type=${display_type}&method=${method}&metaonly=${metaonly}`
        console.log('URL:', url)
        const data = await fetchAsync(url, message=`Loading Square ${meta.id}`)
        currentState['squareDisplayType'] = data.displayType
        currentState['squareMethod'] = data.method
        loadSVG(data, generalElements.square)
        $("#Square_div").html(data.card)
        pushState()
    };
};

async function loadHole(elem, metaonly = false) {
    var center = elem
    if (elem.classList.contains('completed') | elem.classList.contains('processed')) {
        if (!metaonly) {
            //Find center hole
            if (elem.classList.contains('is_area')) {
                center = elem.parentElement.getElementsByClassName('center')[0]
            }
            var imglm = document.createElement('img')
            let data = await fetchAsync(`/api/holes/${center.id}/load`, message=`Loading Hole ${center.id}`)
            loadSVG(data, generalElements.hole)
            // $("#Atlas_div").html(data.card)
            // imglm.src = lm_data.png.url
            // imglm.className = "col-s-12 col-xl-3 col-lg-4 col-md-6 shadow-1-strong rounded p-2"
            $("#mmHole").html(data.card)
        }
        if (elem.classList.contains('completed')) {  
        hm_data = await fetchAsync(`/api/holes/${center.id}/highmag/`, message=`Loading high mag data.`)
        $('#Hole').html(hm_data)
        grabCuration()
        };
    };
};

function grabCuration() {
    $('#Hole_div .holeCard').each(function () {
        var related = $(`#square-svg #${$(this).attr('hole_id')}`)
        var label = related.attr('label')
        if (label != "target") {
            $(this).css("border", `3px solid ${related.attr('stroke')}`)
            console.log($(this).find('.dropdown-item .active'))
            $(this).find('.dropdown-item.active').removeClass('active')
            $(this).find(`[label = '${label}']`).addClass('active')
        }
    })
}


function showNumber(id) {
    console.log(id)
}

function add_text(item, text, size) {
    ft_sz = Math.floor(size / 3000 * 80)
    el = document.createElementNS("http://www.w3.org/2000/svg", 'text')
    el.setAttribute("x", item.x + Math.floor(Math.sqrt(item.area) / 2))
    el.setAttribute("y", item.y - Math.floor(Math.sqrt(item.area) / 2))
    el.setAttribute("class", 'svgtext ' + item.status)
    el.setAttribute("font-size", ft_sz)
    el.setAttribute("stroke-width", Math.floor(ft_sz / 5))
    el.textContent = text
    return el
}

async function changeGridStatus(status) {
    if (status == 'aborting') {
        var r = confirm("Do you want to stop acquisition and move to the next sample?");
    } else if (status == 'started') {
        var r = confirm("Do you want to restart this grid?\nYou'll need to rerun the session to run the sample");
    }
    if (r == true) {
        console.log(status, fullmeta.grid_id)
        var url = `/api/grids/${fullmeta.grid_id}/`
        await apifetchAsync(url, { 'status': status }, "PATCH", message=`Setting grid status to ${status}`);
        await reportMain()
        websocketMain()
    } else {
        console.log("Cancel")
    }
}

function rateGrid(el) {
    var url = `/api/grids/${fullmeta.grid_id}/`;
    var value = el.value
    let sidebar_element = $(`#sidebarGrids #${fullmeta.grid_id} div`)
    if ( el.classList.contains('active')) {
        value = null
    }
    document.getElementById("goodGrid").classList.remove('active');
    document.getElementById("badGrid").classList.remove('active');
    
    apifetchAsync(url, { 'quality': value }, "PATCH", message=`Setting grid quality to ${value}`);
    
    sidebar_element.removeClass(function (index, className) {
        return (className.match(/(^|\s)quality-\S+/g) || []).join(' ')})
    if (value != null) {
        el.classList.add('active');
        sidebar_element.addClass(`quality-${value}`)
    }
}

function hideSVG(el) {
    let final = 'visible'
    if (el.classList.contains('active')) {
        final = 'hidden'
        el.classList.remove('active')
    } else {
        el.classList.add('active')
    }
    if (el.value == 'Numbers') {
        $('#atlasText,#squareText').attr('visibility', final);
    }
    if (el.value == 'Labels') {
        $('#atlasText,#squareText,#atlasShapes,#squareShapes').attr('visibility', final);
    }
}

function hideSVGlabel(el, parentid) {
    elements = document.getElementById(parentid).getElementsByClassName(el.value);
    // find final visibility
    let final = 'visible'
    if (el.classList.contains('active')) {
        final = 'hidden'
        el.classList.remove('active')
    } else {
        el.classList.add('active')
    }
    for (let element of elements) {
        element.setAttribute('visibility', final);
    }
}

function openMenu(el, menu) {
    menu.classList.remove('show')
    report = document.getElementById('main').getBoundingClientRect()
    elBox = el.getBoundingClientRect()
    X = elBox.left - report.left
    Y = elBox.bottom - report.top
    menu.classList.toggle('show')
    menu.style.left = X
    menu.style.top = Y
}
function openGoTo(el) {
    openMenu(el, document.getElementById('popupMenuGoTo'))
}

function optionMenu(meta, type = 'holes') {
    var queueBtn = document.getElementById('opt-queued-square')
    var queueDiv = document.getElementById('squareQueue')
    if (type == 'holes') {
        var queueBtn = document.getElementById('opt-queued-hole')
        var queueDiv = document.getElementById('holeQueue')
    }
    if (fullmeta.status != 'complete') {
        queueDiv.classList.remove('d-none')
        queueDiv.classList.add('d-block')
        let queued = []
        Object.keys(fullmeta[type]).map(function (_key) {
            if (meta.includes(_key)) {
                queued.push(fullmeta[type][_key].status)
            }
        })
        queued = Array.from(new Set(queued))
        console.log(queued)
        if (queueBtn !== null) {
            if (queued.length == 1) {
                queueBtn.disabled = false
                if (queued[0] == 'queued') {
                    queueBtn.value = 0
                    queueBtn.innerHTML = 'Remove from queue'

                } else if (queued[0] === null) {
                    queueBtn.value = 1
                    queueBtn.innerHTML = 'Add to queue'
                } else {
                    queueBtn.disabled = true
                }
            } else {
                queueBtn.disabled = true
            }
        }
    } else {
        queueDiv.classList.add('d-none')
        queueDiv.classList.remove('d-block')
    }
    popupsele = [meta, type]
}

// function closeOptionMenu() {
//     menu = document.getElementById("popupMenuGoTo")
//     menu.classList.remove('show')
// }

function closePopup(element) {
    console.log(element);
    element.classList.add('hidden');
    deactivateButton(element)
    document.getElementById('zoomedContent').innerHTML = zoomedContentCln.innerHTML
    hmSelection = null
    popupsele = null
}

function deactivateButton(element) {
    var active = element.getElementsByClassName('active')
    while (active.length > 0) {
        active[0].classList.remove('active')
    }
}

function grabFormData(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Array.from(formData.entries()).reduce((memo, pair) => ({
        ...memo,
        [pair[0]]: pair[1],
    }), {});
    console.log(data)
    return data
}

$('#main').on('keyup', '#editNotesForm', delay(function (e) {
    $('#editNotesForm').submit();
}, 500));


$('#main').on('submit', '#editNotesForm, #editGridForm', function (e) {
    let data = grabFormData(e)
    var url = `/api/grids/${currentState.grid_id}/`
    apifetchAsync(url, data, "PATCH", message=`Edit grid notes`)
});

$('#main').on('submit', '#editCollectionParamsForm', function (e) {
    let data = grabFormData(e)
    var url = `/api/grids/${currentState.grid_id}/editcollectionparams/`
    apifetchAsync(url, data, "PATCH", message=`Changing grid collection parameters`)
});

// $('#main').on('click', '#gridParamBtn', function (e) {
//     target = e.target
//     var expanded = target.getAttribute('aria-expanded')
//     if (expanded == 'false') {
//         target.innerHTML = '- Grid details'
//         target.classList.add('active')
//     } else {
//         target.innerHTML = '+ Grid details'
//         target.classList.remove('active')
//     }
// })

// $('#main').on('click', '#legendsBtn', function (e) {
//     target = e.target
//     var expanded = target.getAttribute('aria-expanded')
//     if (expanded == 'false') {
//         target.innerHTML = 'Hide legend'
//         target.classList.add('active')
//     } else {
//         target.innerHTML = 'Show legend'
//         target.classList.remove('active')
//     }
// })

// $('#main').on('click', '#gridStatsBtn', function (e) {
//     target = e.target
//     var expanded = target.getAttribute('aria-expanded')
//     console.log(expanded)

//     if (expanded == 'false') {
//         target.innerHTML = 'Hide Stats'
//         target.classList.add('active')
//     } else {
//         target.innerHTML = 'Show Stats'
//         target.classList.remove('active')
//     }
// })


async function popupSele(element) {
    var type = popupsele[1]
    var ids = popupsele[0]
    var new_value = element.value
    var do_reload = false
    console.log('Choosing!', new_value)
    if (type === 'squares') {
        var reload = loadAtlas
        var reloadArgs = { 'metaonly': true }
        var clearSeleArgs = [squareSelection, type]
    }
    else if (type === 'holes') {
        var reload = loadSquare
        var reloadArgs = { 'full_id': currentState.square, 'metaonly': true }
        var clearSeleArgs = [holeSelection, type]
    }
    if (element.parentElement.id === 'quality') {
        var column = 'quality'
    } else {
        var column = 'selected'
        reloadArgs.metaonly = false
        do_reload = true
        new_value = parseInt(new_value)

    }
    let data = await updateTarget(type, ids, column, new_value)
    if (data) {
        console.log('Data', data)
        if (do_reload) {
            await reload(...Object.values(reloadArgs))
            updateFullMeta(data.fullmeta)
            let svgToUpdate = { ...data.fullmeta.squares }
            svgUpdate(svgToUpdate)
        } else {
            updateFullMeta(data.fullmeta)
            let svgToUpdate = { ...data.fullmeta.squares, ...data.fullmeta.holes }
            svgUpdate(svgToUpdate)
        }

    }
    clearSelection(...clearSeleArgs)
    element.parentElement.parentElement.classList.remove('show')
    popup_sele = null
}



async function updateTargets(model, display_type, method, key, new_value, ids = null) {

    var sele = squareSelection
    let stateKey = 'atlas'
    if (model == 'holes') {
        sele = holeSelection
        stateKey = 'square'
    }
    if (ids) {
        sele = ids
    }
    let request = {
        type: model,
        ids: sele,
        display_type: display_type || currentState[`${stateKey}DisplayType`],
        method: method || currentState[`${stateKey}Method`],
        key: key,
        new_value: new_value
    }
    console.log('updateClassifier request: ', request)
    var url = `/api/updatetargets/`
    resp = await apifetchAsync(url, request, "PATCH", message=`Updating targets ${key} to ${new_value}`)
    updateData(resp)
    // resp = await websocketSend('update.target', request)
    console.log('updateClassifier response: ', resp)
    clearSelection(sele, model)
}

async function loadMeta() {
    return await fetchAsync(`/api/grids/${currentState.grid_id}/fullmeta`, message='Loading specimen metadata')
}

function countBisGroupSizes() {
    var bisGroupSizes = new Object()
    jQuery.map(fullmeta.holes, function (obj) {
        if (obj.bis_group != null && [null, '1', '2'].includes(obj.quality)) {
            bisGroupSizes[obj.bis_group] = bisGroupSizes[obj.bis_group] + 1 || 1
        }
    })
    return bisGroupSizes
};

function renderCounts() {
    document.getElementById('holeCountQueued').innerHTML = fullmeta.counts.queued
    document.getElementById('holeCountAcquired').innerHTML = fullmeta.counts.completed
    document.getElementById('holeCountPerhour').innerHTML = fullmeta.counts.perhour
    document.getElementById('holeLasthour').innerHTML = fullmeta.counts.lasthour
}



function SvgCoords(evt) {

    var el = evt.target
    var svg = el.parentElement
    var pt = svg.createSVGPoint()
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    var cursorpt = pt.matrixTransform(svg.getScreenCTM().inverse());
    console.log("(" + cursorpt.x + ", " + cursorpt.y + ")");
    var target = add_target(cursorpt)
    svg.appendChild(target)
    return [target, [cursorpt.x, cursorpt.y]]
}

function add_target(item) {
    el = document.createElementNS("http://www.w3.org/2000/svg", 'path')
    el.setAttribute("d", `M${item.x - 10} ${item.y - 30} h20 v20 h20 v20 h-20 v20 h-20 v-20 h-20 v-20 h20 z`)
    el.setAttribute("class", "temporaryTarget")
    el.setAttribute('style', 'fill: red')
    return el
}

async function addTargets(btn, selection) {
    console.log(selection)
    var coords = []
    for (i in selection) {
        coords.push(selection[i][1])
    }

    console.log(`Adding targets on square: ${currentState.square}`, coords)
    clearSelection(selection, 'targets')
    var url = "/api/addtargets/"
    let res = await apifetchAsync(url, { 'session_id': fullmeta.session_id, 'square_id': currentState.square, 'targets': coords }, 'POST', message='Adding targets')
    console.log(res)
    loadSquare(currentState.square, false)
}

async function regroupBIS(square_id) {
    let url = `/api/squares/${square_id}/regroup_bis/`
    let res = await apifetchAsync(url, {}, 'PATCH', message=`Regrouping BIS on for ${square_id}`)
    console.log('regroupBIS: ', res)
    await loadSquare(currentState.square, false)
}

function populateReportHead() {
    var date = new Date(fullmeta.last_update)
    $('#gridLastUpdate').html(date.toLocaleString('en-CA', { 'localeMatcher': 'lookup', 'hour12': false }))
    $('#gridStatus').html(`${fullmeta.status}`)
    if (fullmeta.status == 'complete') {
        $('#stop-button').prop("disabled", true)
        $('#restart-button').prop("disabled", false)
    } else {
        $('#stop-button').prop("disabled", false)
        $('#restart-button').prop("disabled", true)
    }
}

async function reportMain() {
    generalElements = {
        'atlas': document.getElementById('Atlas_im'),
        'square': document.getElementById('Square_im'),
        'hole': document.getElementById('mmHole')
    }
    currentTarget = null
    hm_data = null
    hovered = [];
    squareSelection = []
    holeSelection = []
    popupsele = null
    hmSelection = null
    targetsSelection = []
    zoomedContentCln = document.getElementById('zoomedContent').cloneNode(true)
    fullmeta = await loadMeta()
    populateReportHead()
    renderCounts()
    if (fullmeta.status != null) {
        console.log(fullmeta.atlas[Object.keys(fullmeta.atlas)[0]].status)
        if (fullmeta.atlas[Object.keys(fullmeta.atlas)[0]].status == 'completed') {
            await loadAtlas(metaonly = false, display_type = currentState['atlasDisplayType'] || null, method = currentState['atlasMethod'] || null);
            if (![null, undefined].includes(currentState.square)) {
                await loadSquare(currentState.square, metaonly = false, display_type = currentState['squareDisplayType'] || null, method = currentState['squareMethod'] || null)
            }
            if (![null, undefined].includes(currentState.hole)) {
                await loadHole(document.getElementById(currentState.hole))
            }
            return
        }
        console.log('atlas is acquiring')
        $('#Atlas_im').html('<h3>Grid is started. Atlas will appear once acquired.</h3>')
        return
    }
    $('#Atlas_im').html('<h3>Grid is not yet started. Atlas will appear once acquired.</h3>')
};
$('#main').on('change', ".card circle", function () {
    console.log('Changed!')
})

$('#main').on('mouseenter', ".holeCard", function (e) {
    var hole = document.getElementById($(this).attr('hole_id'))
    var highmag = document.getElementById($(this).attr('id'))
    if (hole) {
        hovered.push(hole)
        hole.classList.add("hovered")
    }
    if (highmag) {
        hovered.push(highmag)
        highmag.classList.add("hovered")
    }
}).on("mouseleave", ".holeCard", function () {
    for (let i in hovered) {
        hovered[i].classList.remove("hovered")
    };
    hovered = []
}
);

function clickHole(elem) {
    selectElement(elem, holeSelection);
    checkSelection('hole')
    currentState.hole = elem.id
    loadHole(elem);
    console.log(currentState)
    pushState()
};


$('#main').on("click", '#Square_div svg', function (event) {
    if (event.shiftKey) {
        targetsSelection.push(SvgCoords(event))
        console.log(targetsSelection)
        checkSelection('targets')
    }
});

function showIframe() {
    iframepopup = document.getElementById('iframepopup')
    iframepopup.classList.remove('hidden')

    var iframe = document.createElement('iframe');
    iframe.src = `/autoscreenViewer/run/session/${fullmeta.session_id}`
    iframe.width = '100%'
    iframe.height = '100%'
    iframepopup.appendChild(iframe)
};


function clickSquare(elem) {
    let meta = fullmeta['squares'][elem.id]
    selectElement(elem, squareSelection);
    checkSelection('square')
    if (meta.status == 'completed') {
        if (currentState.square === elem.id) {
            console.log('Reloading square meta')
            loadSquare(elem.id, true)
            return
        }
        currentState.square = elem.id;
        clearSelection(holeSelection, 'hole')
        clearSelection(targetsSelection, 'targets')
        loadSquare(elem.id);
        console.log(currentState)
        pushState()
    }
};

// $('#main').on('click', function (event) {
//     if (event.target.id != 'goToSeleMenu' && !$(event.target).closest('#popupMenu').length) {
//         closeOptionMenu()
//     }
// });



$('#main').on("mouseenter", '#Square_div circle', function () {
    hovered = []
    var parent = this.parentElement.children
    if (this.parentElement.id) {
        for (let item of parent) {
            hovered.push(item);
            item.classList.add("hovered")
        }
    } else {
        hovered.push(this)
        this.classList.add("hovered")
    };
}).on("mouseleave", '#Square_div circle', function () {
    for (let i in hovered) {
        hovered[i].classList.remove("hovered")
    };
    hovered = []
}
);

function colorBISgroups() {
    consope.log('Coloring!')
    let colors = ['#a50026', '#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695']
    var count = 0
    $('#squareShapes').children("*[id]").each(function () {
        let index = count % colors.length
        randomColor = colors[index]
        $(this).children().attr('class', '').attr('fill', randomColor).attr('stroke', randomColor).attr('fill-opacity', 1)
        count++
    })

}

$("#main").on('click', '.zoomBtn', function () {
    console.log('Click', $(this))
    let card = $(this).closest('.holeCard')
    let icon = $(this).children('.zoomIcon')
    console.log(card)
    if (card.hasClass('popupFull')) {
        card.removeClass('popupFull')
        icon.removeClass("bi-zoom-out").addClass("bi-zoom-in")
        return
    }
    card.addClass('popupFull')
    icon.removeClass("bi-zoom-in").addClass("bi-zoom-out")
}) 


function updateData(data) {
    if (data.type == 'update') {
        updateFullMeta(data.fullmeta)
        if (Object.keys(data.fullmeta.atlas).length === 0) {
            console.log('UPDATING!!')
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