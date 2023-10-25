from .base_model import *

class CustomGroupPath(BaseModel):
    group = models.OneToOneField(
        Group,
        null=True,
        on_delete=models.SET_NULL,
        to_field='name'
    )
    path = models.CharField(max_length=300)

    class Meta(BaseModel.Meta):
        db_table = 'customgrouppath'

    def __str__(self):
        return f'{self.group.name}: {self.path}'

class CustomUserPath(BaseModel):
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL, to_field='username')
    path = models.CharField(max_length=300)

    class Meta(BaseModel.Meta):
        db_table = 'customuserpath'

    def __str__(self):
        return f'{self.user.username}: {self.path}'