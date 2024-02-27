import detectron2
from detectron2.structures import BoxMode
from detectron2.utils.logger import setup_logger

import numpy as np
import os, json, cv2, random
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog
import yaml
import glob 

setup_logger()


def get_custom_dicts(file_dir):
	category_dict = {"squares": 0, "contaminated": 1, "cracked": 2, "dry": 3, "fraction":4, "small": 5, "square": 6}
	
	dataset_dicts = []
	yaml_file = os.path.join(file_dir, 'metadata.yaml')
	with open(yaml_file) as file:
		metadata = yaml.load(file, Loader = yaml.FullLoader)
	for idx, atlas in enumerate(metadata):
		record = {}
		record["file_name"] = os.path.join(file_dir, atlas["image"])
		record["image_id"] = idx
		record["height"] = atlas["shape_y"]
		record["width"] = atlas["shape_x"]
		objs = []
		annos = atlas["targets"]
		for sq in annos:
			bbox = sq["coordinates"]
			category = category_dict[sq["label"]]
			obj = {
				"bbox": bbox,
				"bbox_mode":BoxMode.XYXY_ABS,
				"segmentation": [],
				"category_id": category,
			}

			objs.append(obj)
		record["annotations"] = objs 
	
		dataset_dicts.append(record)

	return dataset_dicts


if __name__ == "__main__":
	dataset_dicts = get_custom_dicts('data/new_training/train/')
	print(dataset_dicts)
