


from .base_model import *

class HoleType(BaseModel):
    name = models.CharField(max_length=100, primary_key=True)
    hole_size = models.FloatField(null=True, blank=True, default=None)
    hole_spacing = models.FloatField(null=True, blank=True, default=None)

    @property
    def pitch(self):
        return self.hole_size + self.hole_spacing

    class Meta(BaseModel.Meta):
        db_table = 'holetype'

    def __str__(self):
        return self.name