
from typing import List, Optional
import logging
import random
from copy import copy
from Smartscope.lib.image.target import Target
from smartscope_connector.Datatypes.querylist import QueryList
from Smartscope.lib.Datatypes.selector_sorter import SelectorSorter
from Smartscope.core.settings.worker import PLUGINS_FACTORY
import numpy as np

from smartscope_connector import models

logger = logging.getLogger(__name__)

def create_target(target:models.target.Target, model:models.target.Target, finder:str, classifier:Optional[str]=None, start_number:int=0, **extra_fields):
    target_dict = target.to_dict()
    context = dict(number=start_number)
    context['finders'] = [models.target_label.Finder.model_validate(target_dict | dict(method_name=finder))]
    if classifier is not None:
        context['classifiers'] = [models.target_label.Classifier(method_name=classifier,label=target.quality)]
    data = target_dict | context | extra_fields
    obj = model.model_validate(data)
    return obj

def add_targets(targets:List[Target], model:Target, finder:str, classifier:Optional[str]=None, start_number:int=0, **extra_fields):
    output = []
    for ind, target in enumerate(targets):
        number = ind + start_number
        output.append(create_target(target, model, finder, classifier, number, **extra_fields))
    return QueryList(output)


def get_target_methods(parent, method_type:['selectors','finders','classifiers']='selectors'):
    def get_selector_methods_names(target):
        items = getattr(target, method_type)
        if isinstance(items, list):
            return map(lambda x: x.method_name, items)
        return map(lambda x: x.method_name ,list(items.all()))

    return set().union(*map(get_selector_methods_names, parent.targets))


def randomized_choice(filtered_set: set, n: int):
    choices = []
    while n >= len(filtered_set):
        choices += list(filtered_set)
        n -= len(filtered_set)
        logger.debug(f'More choices than length of filtered set, choosing one of each {choices}. {n} left to randomly choose from.')
    for i in range(n):
        
        choice = random.choice(list(filtered_set))
        logger.debug(f'For {i}th choice, choosing {choice} from {filtered_set}.')
        choices.append(choice)
        filtered_set.remove(choice)
    return choices

def choose_get_index(lst, value):
    indices = [i for i, x in enumerate(lst) if x == value]
    choice = random.choice(indices)
    del lst[choice]
    return choice

def filter_targets(parent):
    classifiers = get_target_methods(parent, 'classifiers')
    selectors = get_target_methods(parent, 'selectors')
    filtered = [1] * len(parent.targets)
    for classifier in classifiers:
        for ind, target in enumerate(parent.targets):
            t_classifiers = target.classifiers
            if not isinstance(t_classifiers, list):
                t_classifiers = list(t_classifiers.all())
            label = next(filter(lambda x: x.method_name == classifier, t_classifiers),None)
            if label is None:
                continue
            if PLUGINS_FACTORY[classifier].classes[label.label].value <= 0:
                filtered[ind] = 0
                continue

    filtered = np.array(filtered)
    for selector in selectors: 
        sorter = SelectorSorter(PLUGINS_FACTORY[selector], parent.targets, n_classes=5)
        filtered *= np.array(sorter.classes)
    
    filtered_set = set(filtered[filtered > 0].tolist())
    logger.debug(f'Filtered classes against classifiers {classifiers} and selectors {selectors}: {filtered}')
    logger.debug(f'Selecting from {len(filtered_set)} subsets.')
    return filtered, filtered_set


def select_n_areas(parent, n, is_bis=False):
    filtered, filtered_set = filter_targets(parent)
    choices = randomized_choice(filtered_set, n)
    logger.debug(f'Randomized choices: {choices}')
    output = []
    for choice in choices:
        ind = choose_get_index(filtered, choice)
        output.append(parent.targets[ind])
    return output

def set_or_update_refined_finder(instance, stage_x, stage_y, stage_z):
    refined = next(filter(lambda x: x.method_name == 'Recentering',instance.finders), None)
    if refined is None:
        original_finder = instance.finders[0]
        refined = models.target_label.Finder(method_name='Recentering',
                                x= original_finder.x,
                                y= original_finder.y,
                                stage_x=stage_x,
                                stage_y=stage_y,
                                stage_z=stage_z,)
        instance.finders.insert(0,refined)
        return instance
    index = instance.finders.index(refined)
    instance.finders[index].set_stage_position(x=stage_x, y=stage_y, z=stage_z)
    return instance