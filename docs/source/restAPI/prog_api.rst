Accessing the REST API programatically
######################################

This option is more suited for developper who would like to interact with SmartScope from another software.

Obtaining an API token
======================

First, a user who wished to access the REST API needs to obtain a token from an admin user.

#. Access the admin portal `http://smartscopeURL/admin/`
#. Navigate to the :code:`AUTH TOKEN` section in the side panel list
#. Select the user for whom the token should be created and click save.

    .. figure:: /_static/restAPI_token.png
        :width: 70%
        :align: center
        :figclass: align-center

#. Send the token to the user

Using the request library to query the database
===============================================

After obtaining a token, it is possible to use the python request library to query data.

.. code-block:: python
    
    ## Basic example
    import request
    # Set a few base settings
    API = 'http://smartscopeURL/api/'
    TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    AUTH_HEADER={'Authorization':f'Token {TOKEN}'}

    #Basic query function
    def get_from_API(route:str,filters:Dict) -> List[Dict]:
        request_hole = f'{API}{route}/?'
        for i,j in filters.items():
            request_hole += f'{i}={j}&'
        resp = requests.get(request_hole,headers=AUTH_HEADER)
        return json.loads(resp.content)['results']

    # Query the holes from a specific square that were not selected or acquired
    data = get_from_API('holes',filters=dict(square_id='mySquareId8782367',status='null'))

