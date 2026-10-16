from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """分页参数 page、page_size；返回 {"total": ..., "results": [...]}。"""

    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({"total": self.page.paginator.count, "results": data})

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {"total": {"type": "integer"}, "results": schema},
        }
