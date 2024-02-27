
import importlib
from enum import Enum
from abc import ABC, abstractclassmethod
from typing import Any, Optional, Protocol, List, Dict, Union, Callable
from pydantic import BaseModel, Field
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.image.targets import Targets
import sys

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
    reference: Optional[str]= ''
    method: Optional[str] = ''
    module: Optional[str] = ''
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    importPaths: Union[str,List] = Field(default_factory=list)

    @property
    def is_classifer(self) -> bool:
        """Check wheter this class is a classifier"""
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        [sys.path.insert(0, path) for path in self.importPaths]


    def run(self,
            montage:Montage,
            create_targets_method:Callable=Targets.create_targets_from_box,
            *args, **kwargs):
        """Where the main logic for the algorithm is"""
        module = importlib.import_module(self.module)
        function = getattr(module, self.method)
        output = function(montage,*args, **kwargs, **self.kwargs)
        targets = create_targets_method(output[0],montage)

        return targets, output[1],output[2]


class Finder(BaseFeatureAnalyzer):
    target_class: str = TargetClass.FINDER

    @property
    def is_classifier(self):
        return False


class Classifier(BaseFeatureAnalyzer):
    classes: Dict[(str, classLabel)]
    target_class: str = TargetClass.CLASSIFIER

    @property
    def is_classifier(self):
        return True

    def get_label(self, label):
        return self.classes[label].color, self.classes[label].name, ''


class Finder_Classifier(Classifier):
    target_class:str = TargetClass.CLASSIFIER


class Selector(BaseFeatureAnalyzer):
    clusters: Dict[(str, Any)]
    exclude: List[str] = Field(default_factory=list)
    target_class: str = TargetClass.SELECTOR
    limits: List[float] = [0.0,1.0]
    kwargs: Dict[str, Any] = Field(default_factory=dict)

    def get_label(self, label):
        return self.clusters['colors'][int(label)], int(label), 'Cluster'

    def run(self, *args, **kwargs):
        """Where the main logic for the algorithm is"""
        module = importlib.import_module(self.module)
        function = getattr(module, self.method)
        output = function(*args, **kwargs, **self.kwargs)

        return output


class ImagingProtocol(BaseModel):
    squareFinders: List[str]
    holeFinders: List[str]
    highmagFinders: List[str] = Field(default_factory=list)
    squareSelectors: List[str]
    holeSelectors: List[str]
    
