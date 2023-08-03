from .base_model import *

class MeshSize(BaseModel):
    name = models.CharField(max_length=100, primary_key=True)
    square_size = models.IntegerField()
    bar_width = models.IntegerField()
    pitch = models.IntegerField()

    class Meta(BaseModel.Meta):
        db_table = 'meshsize'

    def __str__(self):
        return self.name


class MeshMaterial(BaseModel):
    name = models.CharField(max_length=100, primary_key=True)

    class Meta(BaseModel.Meta):
        db_table = 'meshmaterial'

    def __str__(self):
        return self.name
