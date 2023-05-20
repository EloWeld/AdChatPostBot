from pymodm import MongoModel, fields
from pymongo.write_concern import WriteConcern


class TgUser(MongoModel):
    user_id = fields.IntegerField(primary_key=True)
    first_name = fields.CharField(blank=True)
    last_name = fields.CharField(blank=True)
    username = fields.CharField(blank=True)
    is_admin = fields.BooleanField(default=False)    
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'Users'

class TgGroup(MongoModel):
    chat_id = fields.IntegerField(primary_key=True)
    title = fields.CharField(blank=True, default="UnnamedGroup")
    owner_id = fields.ReferenceField(TgUser)
    keywords = fields.ListField(fields.CharField(), blank=True)
    bad_keywords = fields.ListField(fields.CharField(), blank=True)
    ubs = fields.ListField(fields.CharField(), blank=True)
    blacklist_users = fields.ListField(fields.CharField(), blank=True)
    forwarded_msgs = fields.ListField(fields.DictField(), blank=True)
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'Groups'
        
class UserbotSession(MongoModel):
    id = fields.CharField(primary_key=True)
    owner_id = fields.ReferenceField(TgUser)
    name = fields.CharField()
    login = fields.CharField()
    string_session = fields.CharField(blank=True)
    password = fields.CharField(blank=True)
    is_dead = fields.BooleanField(default=False)
    
    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'pymodm-conn'
        collection_name = 'UserbotSessions'
        
    