from .base_model import *
from .screening_session import ScreeningSession



class Process(BaseModel):
    session_id = models.ForeignKey(
        ScreeningSession,
        on_delete=models.CASCADE,
        to_field='session_id'
    )
    PID = models.IntegerField()
    start_time = models.DateTimeField(auto_now=True)
    end_time = models.DateTimeField(null=True, default=None)
    status = models.CharField(max_length=10)

    class Meta(BaseModel.Meta):
        db_table = 'process'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self