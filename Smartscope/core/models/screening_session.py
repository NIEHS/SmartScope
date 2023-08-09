from .base_model import *
from Smartscope.lib.image.smartscope_storage import SmartscopeStorage
from Smartscope import __version__ as SmartscopeVersion

# from .microscope import Microscope
# from .detector import Detector

class ScreeningSessionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('microscope_id')\
            .prefetch_related('detector_id')


class ScreeningSession(BaseModel):
    from .microscope import Microscope
    from .detector import Detector
    
    session = models.CharField(max_length=30)
    group = models.ForeignKey(
        Group,
        null=True,
        on_delete=models.SET_NULL,
        to_field='name'
    )
    date = models.CharField(max_length=8)
    version = models.CharField(max_length=20, editable=False)
    microscope_id = models.ForeignKey(
        Microscope,
        null=True,
        on_delete=models.SET_NULL,
        to_field='microscope_id'
    )
    detector_id = models.ForeignKey(
        Detector,
        null=True,
        on_delete=models.SET_NULL
    )
    working_dir = models.CharField(max_length=300, editable=False)
    session_id = models.CharField(max_length=30, primary_key=True, editable=False)

    objects = ScreeningSessionManager()

    class Meta(BaseModel.Meta):
        db_table = "screeningsession"

    @property
    def directory(self):
        cache_key = f'{self.session_id}_directory'
        if (directory:=cache.get(cache_key)) is not None:
            logger.info(f'Session {self} directory from cache.')
            return directory

        if settings.USE_STORAGE:
            cwd = os.path.join(settings.AUTOSCREENDIR, self.working_dir)
            if os.path.isdir(cwd):
                cache.set(cache_key,cwd,timeout=21600)
                return cwd

        if settings.USE_LONGTERMSTORAGE:
            cwd_storage = os.path.join(settings.AUTOSCREENSTORAGE, self.working_dir)
            if os.path.isdir(cwd_storage):
                cache.set(cache_key,cwd_storage,timeout=21600)
                return cwd_storage

        if settings.USE_AWS:
            storage = SmartscopeStorage()
            if storage.dir_exists(self.working_dir):
                cache.set(cache_key,self.working_dir,timeout=21600)
                return self.working_dir

        if settings.USE_STORAGE:
            cache.set(cache_key,cwd,timeout=21600)
            return cwd

    @property
    def stop_file(self):
        return os.path.join(os.getenv('TEMPDIR'), f'{self.session_id}.stop')
    
    @property
    def progress(self):
        statuses= self.autoloadergrid_set.all().values_list('status', flat=True)
        completed = list(filter(lambda x: x == 'complete',statuses))
        return len(completed), len(statuses), int(len(completed)/len(statuses)*100)

    @property
    def currentGrid(self):
        return self.autoloadergrid_set.all().order_by('position')\
            .exclude(status='complete').first()

    @property
    def storage(self):
        return os.path.join(settings.AUTOSCREENSTORAGE, self.working_dir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.session_id:
            if not self.date:
                self.date = datetime.today().strftime('%Y%m%d')
            self.session_id = generate_unique_id(extra_inputs=[self.date, self.session])

    def save(self, *args, **kwargs):
        self.session = self.session.replace(' ', '_')
        if not self.version:
            self.version = SmartscopeVersion
        self.working_dir = os.path.join(self.group.name, f'{self.date}_{self.session}')
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return f'{self.date}_{self.session}'

