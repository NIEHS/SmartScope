
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from Smartscope.lib.autoscreen import update
from Smartscope.lib.db_manipulations import update_target, viewer_only
from asgiref.sync import async_to_sync, sync_to_async

logger = logging.getLogger(__name__)


class MetadataConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        grid_id = self.scope['url_route']['kwargs']['grid_id']
        logger.info(f'Socket is connected: {grid_id}')
        await self.channel_layer.group_add(
            grid_id,
            self.channel_name
        )
        self.groups.append(grid_id)
        await self.accept()

    async def receive(self, text_data):
        response = json.loads(text_data)
        user = self.scope["user"]

        logger.info(f'{self.groups[0]}, received: {response}, user: {user}, {type(user)}')
        is_viewer_only = await sync_to_async(viewer_only)(user)
        # This needs to be changed, implemented quickly for the demo server
        if is_viewer_only:
            return await self.send(text_data='Cannot edit, user is part of the viewer_only group')
        return await self.channel_layer.group_send(self.groups[0], response)

    async def update_target(self, event):
        response = await sync_to_async(update_target)(event['data'])
        # response.setdefault('type', 'update')
        await self.send(text_data=json.dumps(
            response))

    async def update_metadata(self, event):
        await self.send(text_data=json.dumps(
            {'type': 'update',
             'fullmeta': event['update'],
             }
        ))

    async def disconnect(self, event):
        logger.info(f'Socket {self.groups[0]} disconnected', event)
        await self.send(
            {"type": "websocket.close"}
        )
