import os
import numpy as np
import logging
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.apps import apps
from datetime import datetime
from Smartscope import __version__ as SmartscopeVersion
from Smartscope.lib.s3functions import *
from Smartscope.core.svg_plots import drawAtlas, drawSquare, drawHighMag, drawMediumMag
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.lib.image_manipulations import embed_image
from Smartscope.lib.Datatypes.models import generate_unique_id
from .misc_func import Cached_model_property, set_shape_values, cached_model_property


logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    """
    For future abstraction.
    """
    class Meta:
        abstract = True
        app_label = 'API'


class MicroscopeManager(models.Manager):
    def get_by_natural_key(self, location, name):
        return self.get(location=location, name=name)


class DetectorManager(models.Manager):
    def get_by_natural_key(self, microscope_id, name):
        return self.get(microscope_id=microscope_id, name=name)


class GridManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('session_id')


class ImageManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id')


class HoleImageManager(models.Manager):
    use_for_related_fields = True

    def __init__(self):
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id').prefetch_related('highmagmodel_set')


class DisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors')


class HoleDisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors').prefetch_related('highmagmodel_set')

class SquareDisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors').prefetch_related('holemodel_set')

class SquareImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id').prefetch_related('holemodel_set')


class HighMagImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id')


class ScreeningSessionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('microscope_id').prefetch_related('detector_id')


class GridCollectionParamsManager(models.Manager):
    def get_by_natural_key(self, microscope_id, name):
        return self.get(microscope_id=microscope_id, name=name)


class ExtraPropertyMixin:
    def get_full_path(self, data):
        if self.is_aws:
            storage = SmartscopeStorage()
            if isinstance(data, dict):
                for k, v in data.items():
                    data[k] = storage.url(v)
                return data
            else:
                return storage.url(data)
        return data

    @ property
    def is_aws(self):
        if os.path.isabs(self.directory):
            return False
        return True

    @property
    def working_dir(self):
        cache_key = f'{self.pk}_working_dir'
        if (wd := cache.get(cache_key)) is not None:
            logger.debug(f'{self} loading from cache.')
            return wd
        
        cache.set(cache_key, self.grid_id.directory, timeout=7200)
        return self.grid_id.directory

    @ property
    def directory(self):
        return os.path.join(self.working_dir, self.name)


    @ property
    def png(self):
        return self.get_full_path(os.path.join(self.working_dir, 'pngs', f'{self.name}.png'))

    @ property
    def mrc(self):
        return os.path.join(self.directory, f'{self.name}.mrc')

    @ property
    def raw_mrc(self):
        return os.path.join(self.working_dir, 'raw', f'{self.name}.mrc')

    @ property
    def ctf_img(self):
        return self.get_full_path(os.path.join(self.working_dir, self.name, 'ctf.png'))


class Microscope(BaseModel):
    name = models.CharField(max_length=100, help_text='Name of your microscope')
    location = models.CharField(max_length=30, help_text='Name of the institute, departement or room for the microscope.')
    voltage = models.IntegerField(default=200)
    spherical_abberation = models.FloatField(default=2.7)
    microscope_id = models.CharField(max_length=30, primary_key=True, editable=False)
    VENDOR_CHOICES = (
        ('TFS', 'TFS / FEI'),
        ('JEOL', 'JEOL')
    )
    vendor = models.CharField(max_length=30, default='TFS', choices=VENDOR_CHOICES)
    loader_size = models.IntegerField(default=12)
    # Worker location
    worker_hostname = models.CharField(max_length=30, default='localhost')
    executable = models.CharField(max_length=30, default='smartscope.py')
    # SerialEM connection
    serialem_IP = models.CharField(max_length=30, default='xxx.xxx.xxx.xxx')
    serialem_PORT = models.IntegerField(default=48888)
    windows_path = models.CharField(max_length=200, default='X:\\\\auto_screening\\')
    scope_path = models.CharField(max_length=200, default='/mnt/scope')

    objects = MicroscopeManager()

    class Meta(BaseModel.Meta):
        db_table = 'microscope'

    @ property
    def lockFile(self):
        return Path(settings.TEMPDIR,f'{self.microscope_id}.lock')
    
    @property
    def isLocked(self):
        if self.lockFile.exists():
            return True
        return False
    
    @property
    def isPaused(self):
        return Path(settings.TEMPDIR, f'paused_{self.microscope_id}').exists()
    
    @property
    def currentSession(self):
        if self.isLocked:
            return ScreeningSession.objects.get(pk=self.lockFile.read_text())
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


class Detector(BaseModel):
    name = models.CharField(max_length=100)
    microscope_id = models.ForeignKey(Microscope, on_delete=models.CASCADE, to_field='microscope_id')
    DETECTOR_CHOICES = (
        ('K2', 'Gatan K2'),
        ('K3', 'Gatan K3'),
        ('Ceta', 'FEI Ceta'),
        ('Falcon3', 'TFS Falcon 3'),
        ('Falcon4', 'TFS Falcon 4')
    )
    detector_model = models.CharField(max_length=30, choices=DETECTOR_CHOICES)
    atlas_mag = models.IntegerField(default=210)
    atlas_max_tiles_X = models.IntegerField(default=6)
    atlas_max_tiles_Y = models.IntegerField(default=6)
    spot_size = models.IntegerField(default=None, null=True)
    c2_perc = models.FloatField(default=100)
    atlas_to_search_offset_x = models.FloatField(
        default=0, help_text='X stage offset between the atlas and Search mag. Similar to the Shift to Marker offset')
    atlas_to_search_offset_y = models.FloatField(
        default=0, help_text='Y stage offset between the atlas and Search mag. Similar to the Shift to Marker offset')
    frame_align_cmd = models.CharField(max_length=30, default='alignframes')
    gain_rot = models.IntegerField(default=0, null=True)
    gain_flip = models.BooleanField(default=True)
    energy_filter = models.BooleanField(default=False)

    frames_windows_directory = models.CharField(
        max_length=200, default='movies', help_text='Location of the frames from the perspective of SerialEM. This values will use the SetDirectory command.')
    frames_directory = models.CharField(max_length=200, default='/mnt/scope/movies/',
                                        help_text='Location of the frames directory from SmartScope that point to the same location as frames_windows_directory.')

    objects = DetectorManager()

    class Meta(BaseModel.Meta):
        db_table = 'detector'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.microscope_id} - {self.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def natural_key(self):
        return (self.microscope_id, self.name)


class GridCollectionParams(BaseModel):
    params_id = models.CharField(max_length=30, primary_key=True, editable=False)
    atlas_x = models.IntegerField(default=3)
    atlas_y = models.IntegerField(default=3)
    square_x = models.IntegerField(default=1)
    square_y = models.IntegerField(default=1)
    squares_num = models.IntegerField(default=3)
    holes_per_square = models.IntegerField(default=3)  # If -1 means all
    bis_max_distance = models.FloatField(default=3)  # 0 means not BIS
    min_bis_group_size = models.IntegerField(default=1)
    target_defocus_min = models.FloatField(default=-2)
    target_defocus_max = models.FloatField(default=-2)
    step_defocus = models.FloatField(default=0)  # 0 deactivates step defocus
    drift_crit = models.FloatField(default=-1)
    tilt_angle = models.FloatField(default=0)
    save_frames = models.BooleanField(default=True)
    force_process_from_average = models.BooleanField(default=False)
    offset_targeting = models.BooleanField(default=True)
    offset_distance = models.FloatField(default=-1)
    zeroloss_delay = models.IntegerField(default=-1)
    multishot_per_hole = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = 'gridcollectionparams'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.params_id:
            self.params_id = generate_unique_id()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return f'Atlas:{self.atlas_x}X{self.atlas_y} Sq:{self.squares_num} H:{self.holes_per_square} BIS:{self.bis_max_distance} Def:{self.target_defocus_min},{self.target_defocus_max},{self.step_defocus}'


class ScreeningSession(BaseModel):
    session = models.CharField(max_length=30)
    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL, to_field='name')
    date = models.CharField(max_length=8)
    version = models.CharField(max_length=20, editable=False)
    microscope_id = models.ForeignKey(Microscope, null=True, on_delete=models.SET_NULL, to_field='microscope_id')
    detector_id = models.ForeignKey(Detector, null=True, on_delete=models.SET_NULL)
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

    @ property
    def stop_file(self):
        return os.path.join(os.getenv('TEMPDIR'), f'{self.session_id}.stop')
    
    @ property
    def progress(self):
        statuses= self.autoloadergrid_set.all().values_list('status', flat=True)
        completed = list(filter(lambda x: x == 'complete',statuses))
        return len(completed), len(statuses), int(len(completed)/len(statuses)*100)

    @property
    def currentGrid(self):
        return self.autoloadergrid_set.all().order_by('position').exclude(status='complete').first()

    @ property
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


class Process(BaseModel):
    session_id = models.ForeignKey(ScreeningSession, on_delete=models.CASCADE, to_field='session_id')
    PID = models.IntegerField()
    start_time = models.DateTimeField(auto_now=True)
    end_time = models.DateTimeField(null=True, default=None)
    status = models.CharField(max_length=10)

    class Meta(BaseModel.Meta):
        db_table = 'process'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self


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


class AutoloaderGrid(BaseModel):
    position = models.IntegerField()
    name = models.CharField(max_length=100)
    grid_id = models.CharField(max_length=30, primary_key=True, editable=False)
    session_id = models.ForeignKey(ScreeningSession, on_delete=models.CASCADE, to_field='session_id')
    holeType = models.ForeignKey(HoleType, null=True, on_delete=models.SET_NULL, to_field='name', default=None)
    meshSize = models.ForeignKey(MeshSize, null=True, on_delete=models.SET_NULL, to_field='name', default=None)
    meshMaterial = models.ForeignKey(MeshMaterial, null=True, on_delete=models.SET_NULL, to_field='name', default=None)
    hole_angle = models.FloatField(null=True)
    mesh_angle = models.FloatField(null=True)
    quality = models.CharField(max_length=10, null=True, default=None)
    notes = models.CharField(max_length=10000, null=True, default=None)
    status = models.CharField(max_length=10, null=True, default=None)
    start_time = models.DateTimeField(default=None, null=True)
    last_update = models.DateTimeField(default=None, null=True)
    params_id = models.ForeignKey(GridCollectionParams, null=True, on_delete=models.SET_NULL, to_field='params_id',)

    objects = GridManager()
    # aliases

    @ property
    def id(self):
        return self.grid_id

    @ property
    def parent(self):
        return self.session_id

    @property
    def group(self):
        return self.session_id.group

    @ parent.setter
    def set_parent(self, parent):
        self.session_id = parent
    # endaliases

    @ property
    def collection_mode(self):
        if self.params_id.holes_per_square <= 0:
            return 'collection'
        return 'screening'

    @ property
    def atlas(self):
        query = self.atlasmodel_set.all()
        return query

    @ property
    def squares(self):
        return self.squaremodel_set.all()

    @ property
    def count_acquired_squares(self):
        return self.squaremodel_set.filter(status='completed').count()

    @ property
    def holes(self):
        return self.holemodel_set.all()

    @ property
    def count_acquired_holes(self):
        return self.holemodel_set.filter(status='completed').count()

    @ property
    def high_mag(self):
        return self.highmagmodel_set.all()

    @ property
    def end_time(self):
        try:
            hole = self.highmagmodel_set.filter(status='completed').order_by('-completion_time').first()

            if hole is None:
                raise
            logger.debug(f'End time: {self.grid_id}, hole:{hole.hole_id}, {hole.completion_time}')
            return hole.completion_time
        except:
            return self.last_update

    @ property
    def time_spent(self):
        timeSpent = self.end_time - self.start_time
        logger.debug(f'Time spent: {self.grid_id}, {timeSpent}')
        return timeSpent

    
    @ property
    def protocol(self):
        return Path(self.directory , 'protocol.yaml')


    @ property
    def directory(self):
        self_wd = f'{self.position}_{self.name}'
        wd = self.parent.directory
        return os.path.join(wd, self_wd)

    class Meta(BaseModel.Meta):
        unique_together = ('position', 'name', 'session_id')
        db_table = "autoloadergrid"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.grid_id and self.position is not None and self.name is not None:
            self.grid_id = generate_unique_id(extra_inputs=[str(self.position), self.name])

    def save(self, export=False, *args, **kwargs):
        if self.status != 'complete':
            self.last_update = timezone.now()
        super().save(*args, **kwargs)
        if export:
            self.session_id.export()
        return self

    def __str__(self):
        return f'{self.position}_{self.name}'


class AtlasModel(BaseModel, ExtraPropertyMixin):
    atlas_id = models.CharField(max_length=30, primary_key=True, editable=False)
    name = models.CharField(max_length=100, null=False)
    pixel_size = models.FloatField(null=True)
    binning_factor = models.FloatField(null=True)
    shape_x = models.IntegerField(null=True)
    shape_y = models.IntegerField(null=True)
    stage_z = models.FloatField(null=True)
    grid_id = models.ForeignKey(AutoloaderGrid, on_delete=models.CASCADE, to_field='grid_id')
    status = models.CharField(max_length=20, null=True, default=None)
    completion_time = models.DateTimeField(null=True)

    # aliases

    @property
    def group(self):
        return self.grid_id.session_id.group

    @ property
    def alias_name(self):
        return 'Atlas'

    @property
    def prefix(self):
        return 'Atlas'

    @ property
    def api_viewset_name(self):
        return 'atlas'

    @ property
    def targets_prefix(self):
        return 'square'

    @ property
    def id(self):
        return self.atlas_id

    @ property
    def parent(self):
        return self.grid_id

    @ parent.setter
    def set_parent(self, parent):
        self.grid_id = parent

    @ property
    def targets(self):
        return self.squaremodel_set.all()

    # @cached_model_property(key_prefix='svg', extra_suffix_from_function=['method'], timeout=3600)
    def toSVG(self, display_type, method):
        targets = list(SquareModel.display.filter(atlas_id=self.atlas_id))
        return drawAtlas(self,targets , display_type, method)

    class Meta(BaseModel.Meta):
        unique_together = ('grid_id', 'name')
        db_table = 'atlasmodel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.atlas_id:
            self.name = f'{self.grid_id.name}_atlas'
            self.atlas_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name


class TargetLabel(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=30)
    content_object = GenericForeignKey('content_type', 'object_id')
    method_name = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True
        app_label = 'API'


class Finder(TargetLabel):
    x = models.IntegerField()
    y = models.IntegerField()
    stage_x = models.FloatField()
    stage_y = models.FloatField()
    stage_z = models.FloatField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'finder'


class Classifier(TargetLabel):
    label = models.CharField(max_length=30, null=True)

    class Meta(BaseModel.Meta):
        db_table = 'classifier'


class Selector(TargetLabel):
    label = models.CharField(max_length=30, null=True)
    value = models.FloatField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'selector'


class Target(BaseModel):
    name = models.CharField(max_length=100, null=False)
    number = models.IntegerField()
    pixel_size = models.FloatField(null=True)
    shape_x = models.IntegerField(null=True)
    shape_y = models.IntegerField(null=True)
    selected = models.BooleanField(default=False)
    status = models.CharField(max_length=20, null=True, default=None)
    grid_id = models.ForeignKey(AutoloaderGrid, on_delete=models.CASCADE, to_field='grid_id')
    completion_time = models.DateTimeField(null=True)
    # Generic Relations, not fields
    finders = GenericRelation(Finder, related_query_name='target')
    classifiers = GenericRelation(Classifier, related_query_name='target')
    selectors = GenericRelation(Selector, related_query_name='target')

    display = DisplayManager()

    class Meta:
        abstract = True

    @property
    def group(self):
        return self.grid_id.session_id.group

    @property
    def stage_coords(self) -> np.ndarray:
        finder = self.finders.first()
        return np.array([finder.stage_x, finder.stage_y])
    
    @property
    def coords(self) -> np.ndarray:
        finder = self.finders.first()
        return np.array([finder.x, finder.y])

    def is_excluded(self):
        for selector in self.selectors.all():

            plugin = PLUGINS_FACTORY[selector.method_name]
            if selector.label in plugin.exclude:
                return True, selector.label

        return False, selector.label

    def is_good(self):
        """Looks at the classification labels and return if all the classifiers returned the square to be good for selection

        Args:
            plugins (dict): Dictionnary or sub-section from the loaded pluging.yaml.

        Returns:
            boolean: Whether the target is good for selection or not.
        """
        for label in self.classifiers.all():
            if PLUGINS_FACTORY[label.method_name].classes[label.label].value < 1:
                return False
        return True

    # def css_color(self, display_type, method):

    #     if method is None:
    #         return 'blue', 'target', ''

    #     # Must use list comprehension instead of a filter query to use the prefetched data
    #     # Reduces the amount of queries subsitantially.
    #     labels = list(getattr(self, display_type).all())
    #     label = [i for i in labels if i.method_name == method]
    #     if len(label) == 0:
    #         return 'blue', 'target', ''
    #     return PLUGINS_FACTORY[method].get_label(label[0].label)


class SquareModel(Target, ExtraPropertyMixin):
    square_id = models.CharField(max_length=30, primary_key=True, editable=False)
    area = models.FloatField(null=True)
    atlas_id = models.ForeignKey(AtlasModel, on_delete=models.CASCADE, to_field='atlas_id')

    # Managers
    withholes = SquareImageManager()
    objects = ImageManager()
    display = SquareDisplayManager()
    # aliases

    @ property
    def alias_name(self):
        return f'Area {self.number}'

    @ property
    def api_viewset_name(self):
        return 'squares'

    @property
    def prefix(self):
        return 'Square'

    @ property
    def targets_prefix(self):
        return 'hole'

    @ property
    def id(self):
        return self.square_id

    @ property
    def parent(self):
        return self.atlas_id

    @ parent.setter
    def set_parent(self, parent):
        self.atlas_id = parent
    # endaliases

    @ property
    def parent_stage_z(self):
        return self.parent.stage_z

    @ property
    def targets(self):
        return self.holemodel_set.all()


    # @cached_model_property(key_prefix='svg', extra_suffix_from_function=['method'], timeout=3600)
    def toSVG(self, display_type, method):
        holes = list(HoleModel.display.filter(square_id=self.square_id))
        sq = drawSquare(self, holes, display_type, method)
        
        return sq

    @ property
    def has_queued(self):
 
        return self.holemodel_set(manager='just_holes').filter(status='queued').exists()

    @ property
    def has_completed(self):

        return self.holemodel_set(manager='just_holes').filter(status='completed').exists()

    @ property
    def has_active(self):
        return self.holemodel_set(manager='just_holes').filter(status__in=['acquired', 'processed', 'targets_picked', 'started']).exists()


    @ property
    def initial_quality(self):
        try:
            return ChangeLog.objects.get(grid_id=self.grid_id, line_id=self.hole_id, column_name='quality').initial_value
        except:
            return self.quality

    @ property
    def extracted_file(self):
        logger.debug('Getting extracted file')

    class Meta(BaseModel.Meta):
        unique_together = ('name', 'atlas_id')
        db_table = 'squaremodel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.square_id:
            self.name = f'{self.grid_id.name}_square{self.number}'
            self.square_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name


class HoleModel(Target, ExtraPropertyMixin):

    hole_id = models.CharField(max_length=30, primary_key=True, editable=False)
    radius = models.IntegerField()  # Can be removed and area can be put in the target class
    area = models.FloatField()
    square_id = models.ForeignKey(SquareModel, on_delete=models.CASCADE, to_field='square_id')

    bis_group = models.CharField(max_length=30, null=True)
    bis_type = models.CharField(max_length=30, null=True)

    objects = HoleImageManager()
    just_holes = models.Manager()
    display = HoleDisplayManager()

    def generate_bis_group_name(self):
        if self.bis_group is None:
            self.bis_group = f'{self.parent.number}_{self.number}'
            self.bis_type = 'center'
        return self.bis_group

    @ property
    def alias_name(self):
        return f'Target {self.number}'

    @property
    def prefix(self):
        return 'Hole'

    @ property
    def targets(self):
        if self.bis_group is None:
            return HighMagModel.objects.filter(hole_id=self.hole_id)

        holes_in_group = HoleModel.objects.filter(square_id=self.square_id,bis_group=self.bis_group).values_list('hole_id', flat=True)
        return HighMagModel.display.filter(hole_id__in=holes_in_group)

    @ property
    def targets_prefix(self):
        return 'high_mag'

    @ property
    def api_viewset_name(self):
        return 'holes'

    @ property
    def id(self):
        return self.hole_id

    # @cached_model_property(key_prefix='svg', extra_suffix_from_function=['method'], timeout=3600)
    def toSVG(self, display_type, method):
        holes = list(self.targets)
        if self.shape_x is None:  # There was an error in previous version where shape wasn't set.
            set_shape_values(self)
        radius = 0.5
        if self.grid_id.holeType.hole_size is not None:
            radius = self.grid_id.holeType.hole_size/2 
        
        sq = drawMediumMag(self, holes, display_type, method, radius=radius)
        return sq

    @ property
    def bisgroup_acquired(self):
        if self.bis_group is not None:
            status_set = set(list(self.targets.values_list('status', flat=True)))
        else:
            if self.high_mag is None:
                return False
            status_set = set([self.high_mag.status])
        logger.debug(f'Status set = {status_set}')
        if list(status_set) in [['acquired'], ['processed']] or len(status_set) > 1:
            return True
        elif status_set == set(['completed']):
            self.status = 'completed'
            self.save()
            return True
        return False

    @ property
    def parent(self):
        return self.square_id

    @ parent.setter
    def set_parent(self, parent):
        self.square_id = parent

    @ property
    def stage_z(self):
        return self.parent.stage_z

    @ property
    def high_mag(self):
        return self.highmagmodel_set.first()

    class Meta(BaseModel.Meta):
        unique_together = ('name', 'square_id')
        db_table = 'holemodel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hole_id:
            self.name = f'{self.parent.name}_hole{self.number}'
            self.hole_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name


class HighMagModel(Target, ExtraPropertyMixin):
    hm_id = models.CharField(max_length=30, primary_key=True, editable=False)
    hole_id = models.ForeignKey(HoleModel, on_delete=models.CASCADE, to_field='hole_id')
    is_x = models.FloatField(null=True)
    is_y = models.FloatField(null=True)
    offset = models.FloatField(default=0)
    frames = models.CharField(max_length=120, null=True, default=None)
    defocus = models.FloatField(null=True)
    astig = models.FloatField(null=True)
    angast = models.FloatField(null=True)
    ctffit = models.FloatField(null=True)
    # aliases
    objects = HighMagImageManager()
    display = DisplayManager()

    class Meta(BaseModel.Meta):
        db_table = 'highmagmodel'

    @ property
    def id(self):
        return self.hm_id

    @ property
    def api_viewset_name(self):
        return 'highmag'

    @ property
    def parent(self):
        return self.hole_id

    @ parent.setter
    def set_parent(self, parent):
        self.hole_id = parent
    # endaliases

    @property
    def SVG(self):
        return drawHighMag(self)
    
    @property
    def power_spectrum(self):
        if self.is_aws:
            return self.ctf_img
        return embed_image(self.ctf_img)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hm_id:
            self.name = f'{self.parent.name}_{self.number}_hm'
            self.hm_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')
        if self.status == 'completed' and (self.shape_x is None or self.pixel_size is None):
            set_shape_values(self)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name


class ChangeLog(BaseModel):
    table_name = models.CharField(max_length=60)
    grid_id = models.ForeignKey(AutoloaderGrid, on_delete=models.CASCADE, to_field='grid_id')
    line_id = models.CharField(max_length=30)
    column_name = models.CharField(max_length=20)
    initial_value = models.BinaryField()
    new_value = models.BinaryField()
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, to_field='username', on_delete=models.SET_NULL, null=True, default=None)

    class Meta(BaseModel.Meta):
        db_table = 'changelog'

    @ property
    def table_model(self):
        for model in apps.get_models():
            if model._meta.db_table == self.table_name:
                return model
