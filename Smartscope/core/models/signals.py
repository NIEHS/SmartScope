# from models import *
from django.conf import settings
import shutil
import os
from django.contrib.auth.models import User, Group

from Smartscope.lib.file_manipulations import create_scope_dirs
from .session import *
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
import subprocess as sub
import shlex
from Smartscope.server.lib.worker_jobs import *
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SquareModel)
@receiver(pre_save, sender=HoleModel)
# @receiver(pre_save, sender=HighMagModel)
def pre_update(sender, instance, **kwargs):
    if not instance._state.adding:
        original = sender.objects.get(pk=instance.pk)
        for new, old in zip(get_fields(instance), get_fields(original)):
            if new != old:
                col, new_val = new
                old_val = old[1]
                if col == 'selected':
                    # print('New_val: ', new_val, 'Status: ', instance.status is None)
                    if new_val and instance.status is None:
                        # print('Setting status to queued')
                        instance.status = 'queued'
                    else:
                        instance.status = None
                        # print('Setting status to none')
                    change = ChangeLog(date=timezone.now(), table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                       column_name=col, initial_value=old_val.encode(), new_value=new_val.encode())
                    change.save()
                elif col == 'quality':
                    items = ChangeLog.objects.filter(table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                                     column_name=col)
                    logger.debug([item.__dict__ for item in items])
                    change, created = ChangeLog.objects.get_or_create(table_name=instance._meta.db_table, grid_id=instance.grid_id, line_id=instance.pk,
                                                                      column_name=col)
                    change.date = timezone.now()
                    change.new_value = new_val.encode()
                    if created:
                        # print('New change log entry.')
                        change.initial_value = old_val.encode()
                    # else:
                        # print('Modifying change log entry.')
                    change.save()
    return instance


@ receiver(pre_save, sender=AutoloaderGrid)
def grid_modification(sender, instance, **kwargs):
    if not instance._state.adding:
        original = sender.objects.get(pk=instance.pk)
        if instance.status == 'aborting':
            targets = list(instance.squaremodel_set.filter(status='queued'))
            targets += list(instance.holemodel_set.filter(status='queued'))
            for target in targets:
                target.selected = False
                target.save()

        if instance.name != original.name:
            print(f'Changing grid name.\nMoving the grid from:\n\t{original.directory}\nTo:\n\t{instance.directory}')
            os.rename(original.directory, instance.directory)

        if instance.status == 'complete' and original.status != 'complete':
            instance.export()
            if settings.USE_STORAGE:
                try:
                    com = f'rsync -au {instance.session_id.directory}/ {instance.session_id.storage}/'
                    print(com)
                    sub.Popen(shlex.split(com))
                except Exception as err:
                    print(err)
            if settings.USE_AWS:
                try:
                    com = f'aws s3 sync {instance.session_id.directory} s3://{settings.AWS_STORAGE_BUCKET_NAME}/{settings.AWS_DATA_PREFIX}/{instance.session_id.working_dir}'
                    print(com)
                    sub.Popen(shlex.split(com))
                except Exception as err:
                    print(err)

        # if instance.status == 'started' and original.status is None:
        #     instance.start_time = timezone.now()


@ receiver(pre_save, sender=HoleModel)
@ receiver(pre_save, sender=SquareModel)
def grid_modification(sender, instance, **kwargs):
    if not instance._state.adding:
        # original = sender.objects.get(pk=instance.pk)
        if instance.status == 'completed' and instance.completion_time is None:
            instance.completion_time = timezone.now()


@ receiver(post_save, sender=Group)
def create_group_directory(sender, instance, created, *args, **kwargs):
    if created:
        wd = os.path.join(os.getenv('AUTOSCREENDIR'), instance.name)
        ltwd = None
        if settings.AUTOSCREENSTORAGE is not None:
            ltwd = os.path.join(settings.AUTOSCREENSTORAGE, instance.name)
        for d in [wd, ltwd]:
            if d is not None and not os.path.isdir(d):
                print(f'Creating group dir at: ', d)
                os.mkdir(d)


@ receiver(pre_save, sender=ScreeningSession)
def change_group(sender, instance, **kwargs):
    if not instance._state.adding:
        original = sender.objects.get(pk=instance.pk)
        if instance.group != original.group:
            destination = '/'.join(original.directory.replace(original.working_dir, instance.working_dir).split('/'))
            print(f'Changing group.\nMoving the session from:\n\t{original.directory}\nTo:\n\t{destination}')
            shutil.move(original.directory, destination)
    return instance


@receiver(post_save, sender=ScreeningSession)
def create_scope_directory(sender, instance, created, *args, **kwargs):
    if created:
        create_scope_dirs(instance.microscope_id.scope_path)


# @ receiver(post_save, sender=Process)
# def clean_scope_dir(sender, instance, created, **kwargs):
#     if created:
#         print('Starting new session, Cleaning scope directory')
#         send_to_worker(os.getenv('SMARTSCOPE_EXE'), arguments=['clean_scope_dir'])
#     else:
#         print('Reloading existing session')