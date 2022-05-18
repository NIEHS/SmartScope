$(document).ready(async function () {

    checkState()
    await loadSidePanelState()
    pushState()
    selected()

    // groups = await fetchAsync("/api/sidepanel/")
    // $("#sidebarGroups").append(groups)
})