from rest_framework import serializers
from .models import Skill, SkillRequest, Review
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','username','email')

class SkillSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    class Meta:
        model = Skill
        fields = '__all__'

class SkillRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillRequest
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
