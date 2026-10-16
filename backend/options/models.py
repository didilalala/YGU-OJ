from django.conf import settings
from django.db import models


class SiteSetting(models.Model):
    """网站参数（M6）。只存管理员改过的值；未保存的参数使用 options.site.SETTINGS 中的默认值。"""

    key = models.CharField("参数名", max_length=64, primary_key=True)
    value = models.JSONField("参数值")
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="修改人"
    )

    class Meta:
        db_table = "site_setting"
        verbose_name = verbose_name_plural = "网站参数"

    def __str__(self):
        return self.key
