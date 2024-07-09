# from models import *
from pathlib import Path
import shutil
import os
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from django.db.models.signals import post_save, pre_save

from Smartscope.server.lib.worker_jobs import *
from Smartscope.core.status import status
from Smartscope.core.grid.grid_status import GridStatus
from Smartscope.core.models.screening_session import root_directories
from .session import *
from .misc_func import get_fields

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SquareModel)
@receiver(pre_save, sender=HoleModel)
def pre_update(sender, instance, **kwargs):
    if instance._state.adding:
        return instance
    original = sender.objects.get(pk=instance.pk)
    for new, old in zip(get_fields(instance), get_fields(original)):
        if new == old:
            continue
        col, new_val = new
        old_val = old[1]
        if col == 'selected':
            change = ChangeLog(date=timezone.now(), table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                column_name=col, initial_value=old_val.encode(), new_value=new_val.encode())
            change.save()
            continue
        if col == 'quality':
            items = ChangeLog.objects.filter(table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                                column_name=col)
            logger.debug([item.__dict__ for item in items])
            change, created = ChangeLog.objects.get_or_create(table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                                                column_name=col)
            change.date = timezone.now()
            change.new_value = new_val.encode()
            if created:
                change.initial_value = old_val.encode()
            change.save()
            continue
        if col == 'status':
            if old_val == status.SKIPPED and new_val != status.QUEUED:
                instance.status = status.SKIPPED
                logger.debug(f'Changing status of {instance} from to {status.SKIPPED}')   
            continue
    return instance


@ receiver(pre_save, sender=AutoloaderGrid)
def grid_modification(sender, instance, **kwargs):
    if instance._state.adding:
        return
    if instance.status == GridStatus.ABORTING:
        targets = list(instance.squaremodel_set.filter(status=status.QUEUED))
        targets += list(instance.holemodel_set.filter(status=status.QUEUED))
        targets += list(instance.highmagmodel_set.filter(status=status.QUEUED))
        with transaction.atomic():
            for target in targets:
                target.selected = False
                target.status = status.NULL
                target.save()
        return
    original = sender.objects.get(pk=instance.pk)
    if instance.name != original.name:
        logger.info(f'''
            Changing grid name. Moving the grid
            from {original.directory} To {instance.directory}
        ''')
        os.rename(original.directory, instance.directory)
        return

        # if instance.status == 'complete' and original.status != 'complete':
        #     export_grid(instance,instance.session_id.directory)

@ receiver(post_save, sender=HoleModel)
def queue_bis_group(sender,instance,created, **kwargs):
    if not created and instance.bis_type == 'center':
        if instance.selected:
            logger.debug("Updating status bis target to 'queued'")
            HoleModel.objects.filter(grid_id=instance.grid_id,bis_group=instance.bis_group,bis_type='is_area',status=None).update(status=status.QUEUED)
            return
        # logger.debug("Updating status bis target to 'null'")
        HoleModel.objects.filter(grid_id=instance.grid_id,bis_group=instance.bis_group,bis_type='is_area',status=status.QUEUED).update(status=status.NULL)

@ receiver(pre_save, sender=HoleModel)
@ receiver(pre_save, sender=SquareModel)
def grid_modification(sender, instance, **kwargs):
    if not instance._state.adding:
        if instance.status == GridStatus.COMPLETED and instance.completion_time is None:
            instance.completion_time = timezone.now()


# @ receiver(post_save, sender=HoleModel)
# @ receiver(post_save, sender=SquareModel)
# @ receiver(post_save, sender=HighMagModel)
# def clear_svg_cache_target(sender, instance, **kwargs):
#     key = '_'.join(['svg',instance.parent.pk,])
#     if cache.delete_many(f'{key}*'):
#         logger.debug(f'{instance.parent} svg key removed from cache after {instance} update')

# @ receiver(post_save, sender=Classifier)
# @ receiver(post_save, sender=Selector)
# def clear_svg_cache_label(sender, instance, **kwargs):
#     instance_to_update = instance.content_object.parent
#     key = '_'.join(['svg',instance_to_update.pk])
#     if cache.delete_many(f'{key}*'):
#         logger.debug(f'{instance_to_update} svg key removed from cache after {instance} update')

@ receiver(post_save, sender=Group)
def create_group_directory(sender, instance, created, *args, **kwargs):
    if created:
        wd = os.path.join(os.getenv('AUTOSCREENDIR'), instance.name)
        ltwd = None
        if settings.AUTOSCREENSTORAGE is not None:
            ltwd = os.path.join(settings.AUTOSCREENSTORAGE, instance.name)
        for d in [wd, ltwd]:
            if d is not None and not os.path.isdir(d):
                logger.info(f'Creating group dir at: ', d)
                os.mkdir(d)

@ receiver(pre_save, sender=ScreeningSession)
def change_group(sender, instance, **kwargs):
    if not instance._state.adding:
        original = sender.objects.get(pk=instance.pk)
        if instance.group != original.group:
            destination = '/'.join(original.directory.replace(original.working_dir, instance.working_dir).split('/'))
            logger.info(f'Changing group.\nMoving the session from:\n\t{original.directory}\nTo:\n\t{destination}')
            shutil.move(original.directory, destination)
            cache_key = f'{instance.session_id}_directory'
            cache.delete(cache_key)
    return instance

@receiver(post_save, sender=ScreeningSession)
def create_session_scope_directory(sender, instance, created, *args, **kwargs):
    if created:
        directory = Path(root_directories(instance)[0], instance.working_directory)
        logger.debug(f'Creating session {instance} directory at {directory}')
        create_scope_dirs(instance.microscope_id.scope_path)
        directory.mkdir(parents=True, exist_ok=True)

@receiver(post_save, sender=Microscope)
def create_scope_directory(sender, instance, created, *args, **kwargs):
    if created:

        create_scope_dirs(instance.scope_path)

def create_scope_dirs(scope_path):
    if not Path(scope_path).exists():
        logger.warning(f'Scope directory {scope_path} does not exist. Cannot create scope directories.')
        return  
    source = scope_path
    scope_dirs = [
        source,
        os.path.join(source, 'raw'),
        os.path.join(source, 'reference'),
        os.path.join(source, 'movies')
    ]
    for d in scope_dirs:
        if not os.path.isdir(d):
            os.mkdir(d)
