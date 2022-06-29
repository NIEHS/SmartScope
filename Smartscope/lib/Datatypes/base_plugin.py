import importlib
from abc import ABC
from typing import Any, Optional, Protocol, List, Dict
from pydantic import BaseModel, Field


class classLabel(BaseModel):
    value: int
    name: str
    color: str


class FeatureAnalyzer(Protocol):
    description: Optional[str]
    kwargs: Optional[dict]


class BaseFeatureAnalyzer(BaseModel, ABC):
    description: Optional[str] = ''
    method: Optional[str] = ''
    module: Optional[str] = ''
    kwargs: Optional[Dict[str, Any]]

    @property
    def is_classifer(self) -> bool:
        """Check wheter this class is a classifier"""

    def run(self, *args, **kwargs):
        """Where the main logic for the algorithm is"""


class Finder(BaseFeatureAnalyzer):

    @property
    def is_classifier(self):
        return False


class Classifier(BaseFeatureAnalyzer):
    classes: Dict[(str, classLabel)]
    target_class = 'Classifier'

    def is_classifier(self):
        return True

    def get_label(self, label):
        return self.classes[label].color, self.classes[label].name, ''


class Finder_Classifier(Classifier):
    target_class = 'Classifier'

    @property
    def is_classifier(self):
        return True


class Selector(BaseFeatureAnalyzer):
    clusters: Dict[(str, Any)]
    exclude: List[str] = Field(default_factory=list)
    target_class: str = 'Selector'

    def get_label(self, label):
        return self.clusters['colors'][int(label)], label, 'Cluster'
