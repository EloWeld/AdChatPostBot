from uuid import uuid4
from pymodm import MongoModel, fields
from pymongo.write_concern import WriteConcern


class TgUser(MongoModel):
    user_id = fields.IntegerField(primary_key=True)
    first_name = fields.CharField(blank=True)
    last_name = fields.CharField(blank=True)
    username = fields.CharField(blank=True)
    is_admin = fields.BooleanField(default=False)    
    is_authenticated = fields.BooleanField(default=False)    
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'Users'
        
class UserbotSession(MongoModel):
    id = fields.CharField(primary_key=True)
    owner_id = fields.ReferenceField(TgUser)
    name = fields.CharField()
    login = fields.CharField()
    string_session = fields.CharField(blank=True)
    password = fields.CharField(blank=True)
    is_dead = fields.BooleanField(default=False)
    chats = fields.DictField(blank=True)
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'UserbotSessions'


class PostingField(MongoModel):
    id = fields.CharField()
    name = fields.CharField(blank=True, default="Сообщ.")
    text = fields.CharField()
    sent_count = fields.IntegerField(default=0)

class AutopostSlot(MongoModel):
    STATUS_CHOICES = {
        'active': '♻️ Включен',
        'inactive': '❌ Выключен',
        'banned': '🚩 Сломан'
    }
    
    id = fields.CharField(primary_key=True)
    name = fields.CharField()
    owner_id = fields.ReferenceField(TgUser)
    emoji = fields.CharField(max_length=2)
    status = fields.CharField(choices=list(STATUS_CHOICES.keys()), verbose_name='Status', default='inactive')
    ubots = fields.ListField(fields.ReferenceField(UserbotSession), blank=True)
    postings = fields.ListField(fields.EmbeddedDocumentField(PostingField), blank=True)
    chats = fields.DictField(blank=True)
    schedule = fields.ListField(fields.DictField(), blank=True)
    date_schedule = fields.ListField(fields.DictField(), blank=True)
    reports_group_id = fields.BigIntegerField()
    
    def get_verbose_status(self):
        return AutopostSlot.STATUS_CHOICES.get(self.status)
    
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'Slots'
    