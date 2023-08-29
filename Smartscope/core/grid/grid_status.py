


class GridStatus:
    """
    ENUMS don't play well with Django. 
    This is an attempt at creating something equivalent that works
    """
    NULL=None
    STARTED='started'
    ERROR='error'
    SKIPPED='skipped'
    ABORTING='aborting'
    PAUSED='paused'
    COMPLETED='complete'
