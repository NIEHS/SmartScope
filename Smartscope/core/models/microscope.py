from pathlib import Path
from .base_model import *

VENDOR_CHOICES = (
    ('TFS', 'TFS / FEI'),
    ('JEOL', 'JEOL')
)


class MicroscopeManager(models.Manager):
    def get_by_natural_key(self, location, name):
        return self.get(location=location, name=name)


class Microscope(BaseModel):
    name = models.CharField(
        max_length=100,
        help_text='Name of your microscope'
    )
    location = models.CharField(
        max_length=30,
        help_text='Name of the institute, departement or room for the microscope.'
    )
    voltage = models.IntegerField(default=200)
    spherical_abberation = models.FloatField(default=2.7)
    microscope_id = models.CharField(
        max_length=30,
        primary_key=True,
        editable=False
    )
    vendor = models.CharField(
        max_length=30,
        default='TFS',
        choices=VENDOR_CHOICES
    )
    loader_size = models.IntegerField(default=12)
    # Worker location
    worker_hostname = models.CharField(
        max_length=30,
        default='localhost'
    )
    executable = models.CharField(
        max_length=30,
        default='smartscope.py'
    )
    # SerialEM connection
    serialem_IP = models.CharField(
        max_length=30,
        default='xxx.xxx.xxx.xxx'
    )
    serialem_PORT = models.IntegerField(default=48888)
    windows_path = models.CharField(
        max_length=200,
        default='X:\\\\auto_screening\\'
    )
    scope_path = models.CharField(
        max_length=200,
        default='/mnt/scope'
    )

    objects = MicroscopeManager()

    class Meta(BaseModel.Meta):
        db_table = 'microscope'

    @property
    def lockFile(self):
        return Path(settings.TEMPDIR, f'{self.microscope_id}.lock')

    @property
    def isLocked(self):
        if self.lockFile.exists():
            return True
        return False

    @property
    def isPaused(self):
        return Path(settings.TEMPDIR, f'paused_{self.microscope_id}').exists()

    # TODO fix: circular import
    # @property
    # def currentSession(self):
    #     from .screening_session import ScreeningSession
    #     if self.isLocked:
    #         return ScreeningSession.objects.get(pk=self.lockFile.read_text())
    #     return None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.microscope_id:
            self.microscope_id = generate_unique_id()

    def __str__(self):
        return f'{self.location} - {self.name}'

    def natural_key(self):
        return (self.location, self.name)
