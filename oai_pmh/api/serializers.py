from rest_framework import serializers
from rest_framework_mongoengine.serializers import MongoEngineModelSerializer
from mgi.models import Record, Registry, UpdateRecord, DeleteRecord, SelectRecord, DeleteRegistry

################################################################################
#
# Class Name: RegistrySerializer
#
# Description:   Serializer for OAI-PMH Registries
#
################################################################################
class RegistrySerializer(MongoEngineModelSerializer):
    class Meta:
        model = Registry
        exclude = (['identity', 'metadataformats', 'sets'])

class UpdateRegistrySerializer(MongoEngineModelSerializer):
    class Meta:
        model = Registry
        exclude = (['identity','sets', 'metadataformats', 'name', 'url'])

class DeleteRegistrySerializer(MongoEngineModelSerializer):
    class Meta:
        model = DeleteRegistry

class ListRecordsSerializer(serializers.Serializer):
    url  = serializers.URLField(required=True)
    metadataprefix = serializers.CharField(required=True)
    set = serializers.CharField(required=False)
    resumptionToken = serializers.CharField(required=False)
    fromDate = serializers.DateField(required=False)
    untilDate  = serializers.DateField(required=False)

class RegistryURLSerializer(serializers.Serializer):
    url = serializers.URLField(required=True)
    metadataprefix = serializers.CharField(required=True)
    set = serializers.CharField(required=False)
    fromDate = serializers.DateField(required=False)
    untilDate = serializers.DateField(required=False)

class RecordSerializer(MongoEngineModelSerializer):
    class Meta:
        model = Record

class IdentifySerializer(serializers.Serializer):
    url = serializers.URLField(required=True)

class SaveRecordSerializer(MongoEngineModelSerializer):
    class Meta:
        model = Record

class UpdateRecordSerializer(MongoEngineModelSerializer):
    class Meta:
        model = UpdateRecord

class DeleteRecordSerializer(MongoEngineModelSerializer):
    class Meta:
        model = DeleteRecord

class SelectRecordSerializer(MongoEngineModelSerializer):
    class Meta:
        model = SelectRecord

class SetSerializer(serializers.Serializer):
    setName = serializers.CharField()
    setSpec = serializers.CharField()
    raw = serializers.CharField()

class MetadataFormatSerializer(serializers.Serializer):
    metadataPrefix = serializers.CharField()
    metadataNamespace = serializers.CharField()
    schema = serializers.CharField()
    raw = serializers.CharField()
