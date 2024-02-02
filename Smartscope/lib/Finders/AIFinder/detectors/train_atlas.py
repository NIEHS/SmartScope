from detectron2.structures import BoxMode
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader
from detectron2.data.datasets import register_coco_instances
import detectron2
from detectron2.data import detection_utils as utils
from detectron2.utils.logger import setup_logger
from detectron2.data import detection_utils as utils
import detectron2.data.transforms as T
import argparse
from detectron2.modeling import build_model
from detectron2.engine import DefaultTrainer
from detectron2.checkpoint import DetectionCheckpointer
setup_logger()
import glob
# import some common libraries
import numpy as np
import copy
import torch
import os, json, cv2, random


# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog, build_detection_test_loader, build_detection_train_loader
import torchvision
from custom_data import get_custom_dicts
import mrcfile


def squarify(M,val):
    (a,b)=M.shape
    if a>b:
        padding=((0,0),(0,a-b))
    else:
        padding=((0,b-a),(0,0))
    return np.pad(M,padding,mode='constant',constant_values=val)


class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        return build_detection_train_loader(cfg, mapper=custom_mapper)

def custom_mapper(dataset_dict):
    dataset_dict = copy.deepcopy(dataset_dict)  # it will be modified by code below
    # image = utils.read_image(dataset_dict["file_name"], format="BGR")
    if dataset_dict["file_name"].endswith('.mrc'):
        with mrcfile.open(dataset_dict["file_name"]) as mrc:
            atlas = mrc.data 

        atlas = squarify(atlas, 0)
        norm_atlas = cv2.normalize(atlas, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        norm_atlas = np.uint8(norm_atlas*255)
        norm_atlas = np.dstack((norm_atlas, norm_atlas, norm_atlas))
    else:
        norm_atlas = utils.read_image(dataset_dict["file_name"], format="BGR")
    transform_list = [
        T.ResizeScale(0.25,1.95, 2048, 2048),
        # T.RandomBrightness(0.8, 1.2),
        # T.RandomContrast(0.8, 1.2),
        T.RandomRotation(angle=[90, 90]),
        # T.RandomLighting(0.3),
        T.RandomFlip(prob=0.4, horizontal=False, vertical=True),
    ]
    image, transforms = T.apply_transform_gens(transform_list, norm_atlas)
    dataset_dict["image"] = torch.as_tensor(image.transpose(2, 0, 1).astype("float32"))
    annos = [
        utils.transform_instance_annotations(obj, transforms, image.shape[:2])
        for obj in dataset_dict.pop("annotations")
        if obj.get("iscrowd", 0) == 0
    ]
    instances = utils.annotations_to_instances(annos, image.shape[:2])
    dataset_dict["instances"] = utils.filter_empty_instances(instances)
    return dataset_dict

def train_coco(input_dir, output_dir, label='_annotations.coco.json', lr=0.001, max_iter=3000):
    for d in ["train", "val"]:
        input_file = os.path.join(input_dir,d,label)
        input_imgs = os.paht.join(input_dir,d)
        register_coco_instances("my_dataset_train", {}, input_file, input_imgs)


def train(input_dir, output_dir, is_coco = False, label = '_annotations.coco.json', lr = 0.001, max_iter = 3000):
    # get training and validation dataset
    for d in ["train", "val"]:
        if is_coco:
            print(label)
            input_file = os.path.join(input_dir,d,label)
            input_imgs = os.path.join(input_dir,d)
            register_coco_instances("atlas_"+ d, {}, input_file, input_imgs)
        else:
            DatasetCatalog.register("atlas_" + d, lambda d = d: get_custom_dicts(os.path.join(input_dir, d)))
            # MetadataCatalog.get("atlas_" + d).set(thing_classes = ["square"])
            MetadataCatalog.get("atlas_" + d)
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_1x.yaml"))
    cfg.DATASETS.TRAIN = ("atlas_train",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.SOLVER.LR_SCHEDULER_NAME="WarmupCosineLR"
    cfg.SOLVER.IMS_PER_BATCH = 1
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.BASE_LR = lr  # pick a good LR
    cfg.SOLVER.MAX_ITER = max_iter
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 100   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7  # only has one class (ballon). (see https://detectron2.readthedocs.io/tutorials/datasets.html#update-the-config-for-new-datasets)
    # NOTE: this config means the number of classes, but a few popular unofficial tutorials incorrect uses num_classes+1 here.
    cfg.MODEL.ANCHOR_GENERATOR.ASPECT_RATIOS=[[0.85, 1.0, 1.25]]
    cfg.MODEL.RPN.POST_NMS_TOPK_TEST = 6000  # originally 1000
    cfg.MODEL.RPN.PRE_NMS_TOPK_TEST = 6000  # originally 1000
    cfg.MODEL.ANCHOR_GENERATOR.ANGLES=[[-90,0,90]]
    cfg.OUTPUT_DIR=output_dir
    if os.path.isdir(cfg.OUTPUT_DIR):
        print('directory exists')
    else:
        os.makedirs(cfg.OUTPUT_DIR)
        print('created folder: ', cfg.OUTPUT_DIR)
    cfg.INPUT.MIN_SIZE_TEST = 2048
    cfg.INPUT.MAX_SIZE_TEST = 2048
    # cfg.INPUT.RANDOM_FLIP="horizontal"
    # cfg.INPUT.CROP.ENALBED=True 
    # cfg.INPUT.CROP.TYPE="relative_range"
    # cfg.INPUT.CROP.SIZE=[0.9,0.9] 
    cfg.INPUT.MIN_SIZE_TRAIN = (2048,)
    cfg.INPUT.MAX_SIZE_TRAIN = 2048
    cfg.TEST.DETECTIONS_PER_IMAGE = 500
    # os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    # print(cfg)
    trainer = CustomTrainer(cfg) 
    trainer.resume_or_load(resume=False)
    trainer.train()

    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, help='input directory for yaml file for both train and validation folders. ')
    parser.add_argument('--output_dir', type=str, help='output directory for outputs and weights')
    parser.add_argument('--lr', type=float, default = 0.001, help='learning rate for training')
    parser.add_argument('--max_iter', type=int, default = 3000, help='max iteration for training')
    parser.add_argument('--is_coco', action='store_true', help='if input label is in default coco format')
    parser.add_argument('--label', type=str, default='_annotations.coco.json', help='label file name')

    opt = parser.parse_args()
    # register_coco_instances("my_dataset_train", {}, "/nfs/bartesaghilab2/qh36/all_data/detectors/data/training_square/train/_annotations.coco.json", "/nfs/bartesaghilab2/qh36/all_data/no_aug_data/train")
    train(opt.input_dir, opt.output_dir, opt.is_coco, opt.label, opt.lr, opt.max_iter)
    # train_metadata = MetadataCatalog.get("my_dataset_train")
    # print(train_metadata)

