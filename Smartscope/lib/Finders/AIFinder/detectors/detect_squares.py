from detectron2.structures import BoxMode
import argparse
from detectron2.data.datasets import register_coco_instances
import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()

# import some common libraries
import numpy as np
import os, json, cv2, random

from detectron2.engine import DefaultTrainer

# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
import detectron2.data.transforms as T
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.modeling import build_model
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.data import MetadataCatalog, DatasetCatalog
import glob
import argparse
# from sklearn.preprocessing import StandardScaler
import time
# from sklearn.decomposition import PCA
from pathlib import Path
import glob
import cv2
import torch
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
from PIL import Image 
from numpy import random
from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path, save_one_box, to_shape, check_if_square
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized
import mrcfile
import torchvision
from utils.common_config import get_train_transformations, get_val_transformations,\
                                get_train_dataset, get_train_dataloader,\
                                get_val_dataset, get_val_dataloader,\
                                get_optimizer, get_model, get_criterion,\
                                adjust_learning_rate
from models.resnet_squares import resnet18
from models.models import ClusteringModel
from models.models import ContrastiveModel
from sklearn.cluster import KMeans

class GrayscalePredictor:
    def __init__(self, cfg):
        self.cfg = cfg.clone()  # cfg can be modified by model
        self.model = build_model(self.cfg)
        self.model.eval()
        if len(cfg.DATASETS.TEST):
            self.metadata = MetadataCatalog.get(cfg.DATASETS.TEST[0])

        checkpointer = DetectionCheckpointer(self.model)
        checkpointer.load(cfg.MODEL.WEIGHTS)

        self.aug = T.ResizeShortestEdge(
            [cfg.INPUT.MIN_SIZE_TEST, cfg.INPUT.MIN_SIZE_TEST], cfg.INPUT.MAX_SIZE_TEST
        )

        self.input_format = cfg.INPUT.FORMAT

    def __call__(self, original_image):
        """
        original image input is H * W * C

        """
        with torch.no_grad():
            image = self.aug.get_transform(original_image).apply_image(original_image)
            image = np.expand_dims(image, -1)
            height, width = image.shape[:2]
            image = torch.as_tensor(image.astype("float32").transpose(2, 0, 1))

            inputs = {"image": image, "height": height, "width": width}
            predictions = self.model([inputs])[0]
            return predictions


def auto_contrast(img, cutperc=[0.05, 0.01], to_8bits=True):
    hist, x = np.histogram(img.flatten(), bins=256)
    total = np.sum(hist)
    min_side = 0
    min_accum = 0
    max_side = 255
    max_accum = 0
    while min_accum < cutperc[0]:
        min_accum += hist[min_side] / total * 100
        min_side += 1

    while max_accum < cutperc[1]:
        max_accum += hist[max_side] / total * 100
        max_side -= 1
    # print(f'Using auto_contrast {min_side} ({x[min_side]}), {max_side} ({x[max_side]})')
    max_side = x[max_side] - x[min_side]
    img = (img.astype('float32') - x[min_side]) / max_side
    img[img < 0] = 0
    img[img > 1] = 1
    if to_8bits is True:
        return np.round(img * 255).astype('uint8')
    else:
        return img

def detect_grayscale(atlas, device = '0', imgsz = 2048, thresh = 0.2, iou = 0.3, weights = 'runs/square_weights/best_square.pth'):

    """
    Detect squares on a atlas
    
    Parameters
    --------------
    atlas: the atlas.mrc file or a numpy array of the atlas
    device: optional, '0' for gpu and 'cpu' for cpu 
    imgsz: resized atlas size, 2048 is the default
    thresh: confidence threshold for detection, 0.2 for default
    weights: weights for detector


    Return
    --------------
    square coordinates and type 


    """
    label_dict = ['squares','contaminated','cracked','dry','fraction','small','square']
    all_coords = []
    all_labels = []
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_1x.yaml"))
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 8   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = thresh
    cfg.MODEL.RPN.PRE_NMS_TOPK_TEST = 6000
    cfg.MODEL.WEIGHTS = weights 
    cfg.INPUT.MIN_SIZE_TEST = 2048
    cfg.INPUT.MAX_SIZE_TEST = 2048
    cfg.TEST.DETECTIONS_PER_IMAGE = 800
    cfg.INPUT.FORMAT = "L"
    cfg.MODEL.PIXEL_MEAN = [26.0]
    cfg.MODEL.PIXEL_STD = [1.0]
    if device == 'cpu':
        cfg.MODEL.DEVICE='cpu'
    
    if isinstance(atlas, str):
        with mrcfile.open(atlas) as mrc:
            atlas = mrc.data 
    else:
        atlas = atlas 
    # print('atlas,', atlas.shape)
    r, c = atlas.shape
    atlas = cv2.normalize(atlas, None, 0, 255,cv2.NORM_MINMAX)
    atlas = auto_contrast(atlas)
    if r != c:
        max_shape = np.max([r, c])
        holder = np.zeros((max_shape, max_shape))
        holder[:r, :c] = atlas 
        img = holder
        # img = to_shape(atlas, (max_shape, max_shape))
    else:
        img = atlas 
        max_shape = r
    resized = cv2.resize(img, (imgsz, imgsz))
    resized = cv2.normalize(resized, None, 0, 255, cv2.NORM_MINMAX)
    resized = np.uint8(resized)
    scale = max_shape / imgsz 
    img_mult = np.dstack((resized, resized, resized))

    with torch.no_grad():
        predictor_square = GrayscalePredictor(cfg)
        outputs = predictor_square(resized)
    out_inst = outputs["instances"].to("cpu")
    pred_box = out_inst.pred_boxes
    scores = out_inst.scores
    pred_classes = out_inst.pred_classes
    box_tensor = pred_box.tensor
    keep = torchvision.ops.nms(box_tensor, scores, iou)
    pred_box_keep = pred_box[keep]
    scores_keep = scores[keep]
    pred_classes_keep = pred_classes[keep]
    pred_box_keep.scale(scale, scale)
    ind = 0
    for sq_coords in pred_box_keep:
        if_square = check_if_square(sq_coords[0],sq_coords[1],sq_coords[2],sq_coords[3], 1.7, 0.3)
        if 1:
            all_coords.append(sq_coords)
            lb = pred_classes_keep[ind]
            all_labels.append(label_dict[lb])
        ind += 1
    torch.cuda.empty_cache()
    return all_coords, all_labels, img_mult, scale

def detect(atlas, device = '0', imgsz = 2048, thresh = 0.2, iou = 0.3, weights = 'runs/square_weights/best_square.pth'):
    """
    Detect squares on a atlas
    
    Parameters
    --------------
    atlas: the atlas.mrc file or a numpy array of the atlas
    device: optional, '0' for gpu and 'cpu' for cpu 
    imgsz: resized atlas size, 2048 is the default
    thresh: confidence threshold for detection, 0.2 for default
    weights: weights for detector


    Return
    --------------
    square coordinates and type 


    """
    label_dict = ['squares','contaminated','cracked','dry','fraction','small','square']
    all_coords = []
    all_labels = []
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_1x.yaml"))
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 8   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = thresh
    cfg.MODEL.RPN.PRE_NMS_TOPK_TEST = 10000
    cfg.MODEL.RPN.POST_NMS_TOPK_TEST = 10000
    cfg.MODEL.WEIGHTS = weights 
    cfg.INPUT.MIN_SIZE_TEST = 2048
    cfg.INPUT.MAX_SIZE_TEST = 2048
    cfg.TEST.DETECTIONS_PER_IMAGE = 5000
    if device == 'cpu':
        cfg.MODEL.DEVICE='cpu'
    
    if isinstance(atlas, str):
        with mrcfile.open(atlas) as mrc:
            atlas = mrc.data 
    else:
        atlas = atlas 
    # print('atlas,', atlas.shape)
    r, c = atlas.shape
    atlas = cv2.normalize(atlas, None, 0, 255,cv2.NORM_MINMAX)
    atlas = auto_contrast(atlas)
    if r != c:
        max_shape = np.max([r, c])
        holder = np.zeros((max_shape, max_shape))
        holder[:r, :c] = atlas 
        img = holder
        # img = to_shape(atlas, (max_shape, max_shape))
    else:
        img = atlas 
        max_shape = r
    resized = cv2.resize(img, (imgsz, imgsz))
    resized = cv2.normalize(resized, None, 0, 255, cv2.NORM_MINMAX)
    resized = np.uint8(resized)
    scale = max_shape / imgsz 
    img_mult = np.dstack((resized, resized, resized))

    with torch.no_grad():
        predictor_square = DefaultPredictor(cfg)
        outputs = predictor_square(img_mult)
    out_inst = outputs["instances"].to("cpu")
    pred_box = out_inst.pred_boxes
    scores = out_inst.scores
    pred_classes = out_inst.pred_classes
    box_tensor = pred_box.tensor
    keep = torchvision.ops.nms(box_tensor, scores, iou)
    pred_box_keep = pred_box[keep]
    scores_keep = scores[keep]
    pred_classes_keep = pred_classes[keep]
    pred_box_keep.scale(scale, scale)
    ind = 0
    for sq_coords in pred_box_keep:
        if_square = check_if_square(sq_coords[0],sq_coords[1],sq_coords[2],sq_coords[3], 1.7, 0.3)
        if 1:
            all_coords.append(sq_coords)
            lb = pred_classes_keep[ind]
            all_labels.append(label_dict[lb])
        ind += 1
    torch.cuda.empty_cache()
    return all_coords, all_labels, img_mult, scale


# detect()





