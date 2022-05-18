
function validateField(check) {
    var regexp = /^[a-zA-Z0-9-_]+$/;
    if (check.search(regexp) === -1) { return false }
    return true
};

$("#id_session").on('change', function () {
    console.log($(this).get(0))
    $(this).parent().addClass('was-validated')
    return $(this).get(0).checkValidity()
});

$("input[name$='-name']").on('change', function () {
    console.log($(this).val())
    $(this).parent().addClass('was-validated')
    $(this).get(0).checkValidity()
    if ($(this).val()) {
        console.log($(this).parents().eq(4))
        $(this).parents().eq(4).find('select').prop('required', true)
        return
    }
    $(this).parents().eq(4).find('select').removeAttr('required')
});

$("img[id$='_help']").tooltip();

function isNumber(n) {
    return !isNaN(parseFloat(n)) && isFinite(n);
}

function fillFromPrevious(prev_num) {
    const curr_num = prev_num + 1

    for (item of ['holeType', 'meshSize', "meshMaterial"]) {
        var prevVal = $(`[name='${prev_num}-${item}'`).val()

        $(`[name='${curr_num}-${item}'`).val(prevVal)
    }
    let prevName = $(`[name='${prev_num}-name'`).val()
    $(`[name='${curr_num}-position'`).val(parseInt($(`[name='${prev_num}-position'`).val(), 10) + 1)

    var prevNameSplit = prevName.split('_')
    var popped = prevNameSplit.pop()
    if (isNumber(popped)) {
        popped = [parseInt(popped, 10) + 1]
    } else {
        popped = [popped, 1]
    }
    newName = prevNameSplit.concat(popped).join('_')
    $(`[name='${curr_num}-name'`).val(newName)

}

$("#addGridbtn").on('click', function addGrid() {
    let val = $("#addGridDiv").prev().attr('id').split('-')[1]

    console.log('Adding Grid!', val)
    var origDiv = $(`#grid-${val}`)
    var clonedDiv = origDiv.clone();
    // $(this).val(parseInt(val, 10) + 1)
    val = parseInt(val, 10) + 1
    clonedDiv.attr("id", `grid-${val}`);
    console.log(origDiv, clonedDiv)
    origDiv.after(clonedDiv);
    for (item of ['name', 'position', 'holeType', 'meshSize', 'meshMaterial']) {
        clonedDiv.find(`[name$=-${item}]`).attr('name', `${val}-${item}`).attr('id', `id_${val}-${item}`)
    }

    fillFromPrevious(val - 1)
})

function fillFromPreviousWrapper(el) {
    var div = el.closest(".topgrid")
    var num = parseInt(div.id.split('-').pop() - 1)
    if (num != 0) {
        fillFromPrevious(num)
    }
}

function removeGrid(el) {
    var div = el.closest(".topgrid")
    if ($(".topgrid").length > 1) {
        div.remove()
    }

}


function validateForm(event) {
    let form = event.target
    var has_error = false
    if ($('input[name$="-name"]').filter(function () { return $(this).val() != ""; }).length === 0) {
        console.log('No grid filled', $('#autoloaderForm').get(0))
        $('#autoloaderForm').get(0).setCustomValidity('Need to fill in at least one position')
        $('#autoloaderFormError').removeClass('collapse')
        $('#autoloaderFormError').html('At least one grid is required')
        has_error = true
    } else {
        $('#autoloaderForm').get(0).setCustomValidity("")
        $('#autoloaderFormError').addClass('collapse')
    }

    var posVals = []
    $('input[name$="-position"]').each(function () { posVals.push($(this).val()) })
    posValsSet = new Set(posVals)
    console.log(posVals, posVals.length, posValsSet, posValsSet.size)
    if (posVals.length != posValsSet.size) {
        console.log('more than one grid with position')
        $('#autoloaderForm').get(0).setCustomValidity('Duplicate position')
        $('#autoloaderFormError').removeClass('collapse')
        $('#autoloaderFormError').html('Duplicate Position found')
    } else if (!has_error) {
        $('#autoloaderForm').get(0).setCustomValidity("")
        $('#autoloaderFormError').addClass('collapse')
    }


    if (form.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
        form.classList.add('was-validated');
        return false
    }

    form.classList.add('was-validated');
    return true;
}

$(document).ready(function () {
    $('input,textarea,select').filter('[required]:visible')
})