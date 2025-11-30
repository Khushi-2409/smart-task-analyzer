from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    dependencies = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(), many=True, required=False)

    class Meta:
        model = Task
        fields = ['id','title','due_date','estimated_hours','importance','dependencies']
