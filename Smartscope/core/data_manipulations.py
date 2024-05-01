
from typing import List, Optional, Dict
import logging
import random
from copy import copy
from Smartscope.lib.image.target import Target
from smartscope_connector.Datatypes.querylist import QueryList
from Smartscope.core.selector_sorter import SelectorSorter, SelectorValueParser, initialize_selector
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


def get_target_methods(targets, method_type:['selectors','finders','classifiers']='selectors'):
    def get_selector_methods_names(target):
        items = getattr(target, method_type)
        if isinstance(items, list):
            return map(lambda x: x.method_name, items)
        return map(lambda x: x.method_name ,list(items.all()))

    return set().union(*map(get_selector_methods_names, targets))


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
    if indices == []:
        return None
    choice = random.choice(indices)
    del lst[choice]
    return choice


def filter_out_of_range(target):
    return 0 if target.is_out_of_range() else 1


def filter_targets(parent, targets):
    classifiers = get_target_methods(targets, 'classifiers')
    selectors = get_target_methods(targets, 'selectors')

    ##Filter out of range targets
    filtered = list(map(filter_out_of_range, targets))
    logger.debug(f'Filtering {len(filtered)} targets.')
    
    for classifier in classifiers:
        for ind, target in enumerate(targets):
            if filtered[ind] == 0:
                continue
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
        sorter = initialize_selector(parent.grid_id, selector, targets)
        filtered *= np.array(sorter.classes)
    logger.debug(f'Filtered classes against classifiers {classifiers} and selectors {selectors}: {filtered}')
    
    return filtered.tolist()

def apply_filter(targets, filtered):
    return [target for target, filt in zip(targets, filtered) if filt > 0]

def select_random_areas(targets, filtered, n):
    filtered_set = set(filtered)
    if filtered_set == {0} or len(filtered_set) == 0:
        return []
    filtered_set.discard(0) 
    logger.debug(f'Selecting from {len(filtered_set)} subsets.')
    choices = randomized_choice(filtered_set, n)
    logger.debug(f'Randomized choices: {choices}')
    output = []
    for choice in choices:
        ind = choose_get_index(filtered, choice)
        if ind is None:
            break
        output.append(targets[ind])
    return output

def select_n_areas(parent, n, is_bis=False):
    additional_filters = dict()
    if is_bis:
        additional_filters['bis_type'] = 'center'
    additional_filters['status__isnull'] = True
    targets = list(parent.targets.filter(**additional_filters))
    filtered= filter_targets(parent, targets)
    if n <=0:
        return apply_filter(targets, filtered)
    return select_random_areas(targets, filtered, n)

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
