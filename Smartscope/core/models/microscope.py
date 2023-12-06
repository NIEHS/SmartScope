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
    cold_FEG = models.BooleanField(default=False,help_text='Check if the microscope has a cold FEG to enable the flashing operations. Only works on CRYOARM at the moment.')
    microscope_id = models.CharField(
        max_length=30,
        primary_key=True,
        editable=False
    )
    aperture_control = models.BooleanField(default=False,help_text='Check box if serialEM is able to control the aperture selection. Check only if you have JEOL CRYOARM, or a TFS autoloader system.')
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
    @property
    def currentSession(self):
        from .screening_session import ScreeningSession
        if self.isLocked:
            session = ScreeningSession.objects.filter(pk=self.lockFile.read_text().strip()).first()
            logger.debug(f'Current session = {session}')
            if session is not None:
                return session
            logger.warning('Session from the lock file not found, perhaps it was deleted? Removing lock file to avoid other errors.')
            return self.lockFile.unlink()
        return None

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
