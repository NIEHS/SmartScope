$(document).ready(async function () {

    checkState()
    await loadSidePanelState()
    pushState()
    selected()
})

$('#sidebarCollapse').on('click', function () {
    console.log($(this).attr('aria-expanded'), $(this).attr('aria-expanded') == "false")
    let tooltip = $(this).parent().attr('aria-describedby')
    console.log(tooltip,  $(this).parent())
    $(this).parent().removeAttr('aria-describedby')
    $(`#${tooltip}`).remove()
    if ($(this).attr('aria-expanded') == "false") {
        $('#sidebar-container').removeClass('col-12 col-md-2')
        $('#main').removeClass('col-md-10')
    } else {
        $('#sidebar-container').addClass('col-12 col-md-2')
        $('#main').addClass('col-md-10')
    }
})