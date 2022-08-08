from django.contrib.auth.models import Group
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


def is_in_group(user, group_name):
    """
    Takes a user and a group name, and returns `True` if the user is in that group.
    """
    try:
        return Group.objects.get(name=group_name).user_set.filter(id=user.id).exists()
    except Group.DoesNotExist:
        return None


class HasGroupPermission(permissions.BasePermission):
    """
    Ensure user is in required groups.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            logger.debug(f'{request.user} is staff, permission granted')
            return True
        group_name = obj.group
        logger.debug(f'Checking if user is in group {group_name}')

        return is_in_group(request.user, group_name)
