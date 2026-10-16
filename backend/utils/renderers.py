from rest_framework.renderers import JSONRenderer


class UnifiedJSONRenderer(JSONRenderer):
    """
    把视图返回的数据包装成统一格式 {"code": 0, "message": "ok", "data": ...}。

    出错时的响应已由 utils.exceptions.exception_handler 包装好，这里原样输出。
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response is not None and not getattr(response, "exception", False):
            data = {"code": 0, "message": "ok", "data": data}
        return super().render(data, accepted_media_type, renderer_context)
