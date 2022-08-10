from enum import Enum
import importlib
from abc import ABC
from typing import Any, Optional, Protocol, List, Dict
from pydantic import BaseModel, Field
import importlib


class TargetClass(Enum):
    FINDER = 'Finder'
    CLASSIFIER = 'Classifier'
    SELECTOR = 'Selector'
    METADATA = 'Metadata'


class classLabel(BaseModel):
    value: int
    name: str
    color: str


class FeatureAnalyzer(Protocol):
    description: Optional[str]
    kwargs: Optional[dict]


class BaseFeatureAnalyzer(BaseModel, ABC):
    name: str
    description: Optional[str] = ''
    method: Optional[str] = ''
    module: Optional[str] = ''
    kwargs: Optional[Dict[str, Any]]

    @property
    def is_classifer(self) -> bool:
        """Check wheter this class is a classifier"""

    def run(self, *args, **kwargs):
        """Where the main logic for the algorithm is"""
        module = importlib.import_module(self.module)
        function = getattr(module, self.method)
        output = function(*args, **kwargs, **self.kwargs)
        return output


class Finder(BaseFeatureAnalyzer):
    target_class = TargetClass.FINDER

    @property
    def is_classifier(self):
        return False


class Classifier(BaseFeatureAnalyzer):
    classes: Dict[(str, classLabel)]
    target_class = TargetClass.CLASSIFIER

    @property
    def is_classifier(self):
        return True

    def get_label(self, label):
        return self.classes[label].color, self.classes[label].name, ''


class Finder_Classifier(Classifier):
    target_class = TargetClass.CLASSIFIER


class Selector(BaseFeatureAnalyzer):
    clusters: Dict[(str, Any)]
    exclude: List[str] = Field(default_factory=list)
    target_class: str = TargetClass.SELECTOR
    kwargs: Dict[str, Any] = Field(default_factory=dict)

    def get_label(self, label):
        return self.clusters['colors'][int(label)], label, 'Cluster'


class ImagingProtocol(BaseModel):
    squareFinders: List[str]
    holeFinders: List[str]
    squareSelectors: List[str]
    holeSelectors: List[str]
