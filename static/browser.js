$(document).ready(async function () {

    checkState()
    await loadSidePanelState()
    pushState()
    selected()
})

$('#sidebarCollapse').on('click', function () {
    console.log($(this).attr('aria-expanded'), $(this).attr('aria-expanded') == "false")
    if ($(this).attr('aria-expanded') == "false") {
        document.getElementById("sidebarCollapseLogo").style.transform = "rotate(180deg)";
        $('#sidebar-container').removeClass('col-12 col-md-2')
        $('#main').removeClass('col-md-10')
    } else {
        document.getElementById("sidebarCollapseLogo").style.transform = ""
        $('#sidebar-container').addClass('col-12 col-md-2')
        $('#main').addClass('col-md-10')
    }
})