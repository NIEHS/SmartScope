import logging
from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10000
    get_all_query_param = 'all'

    def get_page_size(self, request):
        logger.info(request.query_params)
        if self.get_all_query_param in request.query_params:
            return None
        return super().get_page_size(request=request)