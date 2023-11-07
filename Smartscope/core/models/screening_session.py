import logging

from .base_model import *

from .custom_paths import CustomUserPath, CustomGroupPath
from Smartscope.lib.image.smartscope_storage import SmartscopeStorage
from Smartscope import __version__ as SmartscopeVersion

# from .microscope import Microscope
# from .detector import Detector
logger = logging.getLogger(__name__)

class ScreeningSessionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('microscope_id')\
            .prefetch_related('detector_id')
    

def root_directories(session):
    root_directories = []
    if settings.USE_CUSTOM_PATHS:
        # if session.custom_path is not None:
        #     root_directories.append(session.custom_path.path)
        custom_user_path = CustomUserPath.objects.filter(user=session.user).first()
        if custom_user_path is not None:
            root_directories.append(custom_user_path.path)
        custom_group_path = CustomGroupPath.objects.filter(group=session.group).first()
        if custom_group_path is not None:
            root_directories.append(custom_group_path.path)

    if settings.USE_STORAGE:
        root_directories.append(settings.AUTOSCREENDIR)
        if (groupname:=session.group.name) is not None:
            root_directories.append(os.path.join(settings.AUTOSCREENDIR,groupname))
        else: 
            root_directories.append(settings.AUTOSCREENDIR)
    if settings.USE_LONGTERMSTORAGE:      
        if (groupname:=session.group.name) is not None:
            root_directories.append(os.path.join(settings.AUTOSCREENSTORAGE,groupname))
        else:
            root_directories.append(settings.AUTOSCREENSTORAGE)
    ###FIX AWS STORAGE
    return root_directories
 
def find_screening_session(root_directories,directory_name):
    for directory in root_directories:
        logger.debug(f'Looking for {directory_name} in {directory}')
        if os.path.isdir(os.path.join(directory,directory_name)):
            return os.path.join(directory,directory_name)
    raise FileNotFoundError(f'Could not find {directory_name} in {root_directories}')

class ScreeningSession(BaseModel):
    from .microscope import Microscope
    from .detector import Detector
    
    session = models.CharField(max_length=30)
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.SET_NULL, to_field='username')
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
        cwd = find_screening_session(root_directories(self),self.working_directory)
        cache.set(cache_key,cwd,timeout=10800)
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

    # @property
    # def storage(self):
    #     return os.path.join(settings.AUTOSCREENSTORAGE, self.working_dir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.session_id:
            if not self.date:
                self.date = datetime.today().strftime('%Y%m%d')
            self.session_id = generate_unique_id(extra_inputs=[self.date, self.session])
    
    @property
    def working_directory(self):
        return f'{self.date}_{self.session}'

    def save(self, *args, **kwargs):
        self.session = self.session.replace(' ', '_')
        if not self.version:
            self.version = SmartscopeVersion
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.working_directory

