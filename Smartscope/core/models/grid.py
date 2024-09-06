from pathlib import Path
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone
from .base_model import *
from .tags import ProjectTag, SampleTag, SampleTypeTag, TagGrid

class GridManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('session_id')


class AutoloaderGrid(BaseModel):
    from .screening_session import ScreeningSession
    from .grid_collection_params import GridCollectionParams
    from .hole_type import HoleType
    from .mesh import MeshMaterial, MeshSize

    position = models.IntegerField()
    name = models.CharField(max_length=100)
    grid_id = models.CharField(max_length=30, primary_key=True, editable=False)
    session_id = models.ForeignKey(
        ScreeningSession,
        on_delete=models.CASCADE,
        to_field='session_id'
    )
    holeType = models.ForeignKey(
        HoleType,
        null=True,
        on_delete=models.SET_NULL,
        to_field='name',
        default=None
    )
    meshSize = models.ForeignKey(
        MeshSize,
        null=True,
        on_delete=models.SET_NULL,
        to_field='name',
        default=None
    )
    meshMaterial = models.ForeignKey(
        MeshMaterial,
        null=True,
        on_delete=models.SET_NULL,
        to_field='name',
        default=None
    )
    hole_angle = models.FloatField(null=True)
    mesh_angle = models.FloatField(null=True)
    quality = models.CharField(max_length=10, null=True, default=None)
    notes = models.CharField(max_length=10000, null=True, default=None)
    status = models.CharField(max_length=10, null=True, default=None)
    start_time = models.DateTimeField(default=None, null=True)
    last_update = models.DateTimeField(default=None, null=True)
    params_id = models.ForeignKey(
        GridCollectionParams,
        null=True,
        on_delete=models.SET_NULL,
        to_field='params_id'
    )
    # project_tags = GenericRelation(ProjectTag, related_query_name='grid_id')
    # sample_tags = GenericRelation(SampleTag, related_query_name='grid_id')
    # sample_type_tags = GenericRelation(TagGrid, related_query_name='grid_id')

    objects = GridManager()
    # aliases

    @property
    def id(self):
        return self.grid_id

    @property
    def parent(self):
        return self.session_id

    @property
    def group(self):
        return self.session_id.group

    @parent.setter
    def set_parent(self, parent):
        self.session_id = parent
    # endaliases

    @property
    def collection_mode(self):
        if self.params_id.holes_per_square <= 0:
            return 'collection'
        return 'screening'
    
    def frames_dir(self, prefix:str=''):
        if 'Falcon' in self.session_id.detector_id.detector_model:
            logger.debug('Settings frames directory for Falcon detectors')
            if prefix:
                return Path(f'{prefix}_{self.parent.working_directory}_{self.position}_{self.name}')
            return Path(f'{self.parent.working_directory}_{self.position}_{self.name}')
        logger.debug('Settings frames directory for non-Falcon detectors')
        if prefix:
            return Path(f'{prefix}_{self.parent.working_directory}', f'{self.position}_{self.name}')
        return Path(self.parent.working_directory, f'{self.position}_{self.name}')

    @property
    def atlas(self):
        query = self.atlasmodel_set.all()
        return query

    @property
    def squares(self):
        return self.squaremodel_set.all()

    @property
    def count_acquired_squares(self):
        return self.squaremodel_set.filter(status='completed').count()

    @property
    def holes(self):
        return self.holemodel_set.all()

    @property
    def count_acquired_holes(self):
        return self.holemodel_set.filter(status='completed').count()

    @property
    def high_mag(self):
        return self.highmagmodel_set.all()

    @property
    def end_time(self):
        try:
            hole = self.highmagmodel_set.order_by('-completion_time').first()

            if hole is None:
                raise
            logger.debug(f'End time: {self.grid_id}, hole:{hole.hole_id}, {hole.completion_time}')
            return hole.completion_time
        except:
            return self.last_update

    @property
    def time_spent(self):
        timeSpent = self.end_time - self.start_time
        logger.debug(f'Time spent: {self.grid_id}, {timeSpent}')
        return timeSpent

    
    @property
    def protocol(self):
        return Path(self.directory , 'protocol.yaml')


    @property
    def directory(self) -> Path:
        self_wd = f'{self.position}_{self.name}'
        wd = self.parent.directory
        return Path(wd, self_wd)

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
