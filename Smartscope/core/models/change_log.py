from .base_model import *


class ChangeLog(BaseModel):
    from .grid import AutoloaderGrid
    
    table_name = models.CharField(max_length=60)
    grid_id = models.ForeignKey(
        AutoloaderGrid,
        on_delete=models.CASCADE,
        to_field='grid_id'
    )
    line_id = models.CharField(max_length=30)
    column_name = models.CharField(max_length=20)
    initial_value = models.BinaryField()
    new_value = models.BinaryField()
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        to_field='username',
        on_delete=models.SET_NULL,
        null=True,
        default=None
    )

    class Meta(BaseModel.Meta):
        db_table = 'changelog'

    @ property
    def table_model(self):
        for model in apps.get_models():
            if model._meta.db_table == self.table_name:
                return model