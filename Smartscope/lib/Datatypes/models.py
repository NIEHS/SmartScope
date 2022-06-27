from pydantic import BaseModel
from abc import ABC


class Target(BaseModel, ABC):
    pass
