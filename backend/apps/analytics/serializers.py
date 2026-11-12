from rest_framework import serializers
from .models import DailyMetricSnapshot


class DailyMetricSnapshotSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.ReadOnlyField()

    class Meta:
        model = DailyMetricSnapshot
        fields = '__all__'
