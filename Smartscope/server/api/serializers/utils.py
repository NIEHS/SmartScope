from typing import List
from .. import models
import logging

logger = logging.getLogger(__name__)


def extract_targets(data, label_types:List[str]=['__all__']):
    if label_types == ['__all__']:
        logger.debug(f'Label types: {label_types}. Using all available label types')
        label_types = ['finders','classifiers','selectors']
    target_labels= dict()
    output_labels = []
    target_labels['finders'] = [(item,models.Finder) for item in data.pop('finders',[])]
    target_labels['classifiers'] = [(item,models.Classifier) for item in data.pop('classifiers',[])]
    target_labels['selectors'] = [(item,models.Selector) for item in data.pop('selectors',[])]
    targets = data.pop('targets',[])
    for label_type in label_types:
        output_labels += target_labels[label_type]
    return output_labels, data, targets

def create_target_label_instances(target_labels,instance,content_type):
    target_labels_models = []
    # logger.info(f'Creating target labels for {instance}')
    # logger.debug(f'Target_labels: \n{target_labels}')
    for label,label_class in target_labels:
        target_labels_models.append(label_class(**label,object_id=instance,content_type=content_type))    
    return target_labels_models