from django_filters import rest_framework as filters
from auditlog.models import LogEntry

class LogEntryFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    end_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")
    action = filters.CharFilter(field_name="action")
    actor = filters.CharFilter(field_name="actor__document")
    content_type = filters.CharFilter(field_name="content_type__model")

    class Meta:
        model = LogEntry
        fields = ["action", "content_type", "actor"]