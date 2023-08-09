from .base_model import *
from Smartscope.lib.image.smartscope_storage import SmartscopeStorage

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
