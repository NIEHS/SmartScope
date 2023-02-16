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

from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
import glob
import argparse
from sklearn.preprocessing import StandardScaler
import time
from sklearn.decomposition import PCA
from pathlib import Path
import glob
import cv2
import torch
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
from PIL import Image 
from numpy import random
from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages, letterbox
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path, save_one_box, to_shape, convert_yolo_to_cv, check_if_square
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
from models.model_classification import resnet34

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

def detect_holes(square, weights_circle, imgsz=1280, thresh=0.2, iou=0.15, device='0',  method = 'rcnn'):
    """
    Detect holes on a square

    Parameters
    ---------------------
    square: numpy array of square (either 2d or 3d)
    weights_circle: weights for detector
    imgsz: resized square, default is 1280 (do not change it)
    thresh: confidence threshold for detection
    iou: non max suppression threshold
    device: '0' for gpu, 'cpu' for cpu
    method: 'rcnn' or 'yolo', 'rcnn' seems to perform better

    Return
    ---------------------
    detected hole coordinates
    """
    if method == 'rcnn':
        hole_coords = detect_holes_rcnn(square, imgsz, thresh=thresh, iou = iou, device = device, weights_circle=weights_circle)
    if method == 'yolo':
        hole_coords = detect_holes_yolo(square, imgsz, conf_thres = thresh, iou_thres = thresh, device=device, weights_circle = weights_circle)
    return hole_coords

def detect_and_classify_holes(square, weights_circle, weights_class, imgsz=1280,thresh=0.2, iou=0.15, device = '0', method = 'rcnn'):
    """
    Detect holes on a square

    Parameters
    ---------------------
    square: numpy array of square (either 2d or 3d)
    weights_circle: weights for detector
    weights_class: weights for classifier
    imgsz: resized square, default is 1280 (do not change it)
    thresh: confidence threshold for detection
    iou: non max suppression threshold
    device: '0' for gpu, 'cpu' for cpu
    method: 'rcnn' or 'yolo', 'rcnn' seems to perform better

    Return
    ---------------------
    detected hole coordinates, label for each hole
    """
    if method == 'rcnn':
        hole_coords = detect_holes_rcnn(square, imgsz, thresh=thresh, iou = iou, device = device, weights_circle=weights_circle)
    if method == 'yolo':
        hole_coords = detect_holes_yolo(square, imgsz, conf_thres = thresh, iou_thres = thresh, weights_circle = weights_circle)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = resnet34(num_classes=3).to(device)
    model_weights_path = weights_class
    model.load_state_dict(torch.load(model_weights_path, map_location=device))
    model.eval()
    labels = []
    data_transform = {
        "train": transforms.Compose([transforms.RandomResizedCrop(100),
                                     transforms.RandomHorizontalFlip(),
                                     transforms.ToTensor(),
                                     transforms.Normalize([0], [1])]),
        "val": transforms.Compose([
                                   transforms.ToTensor(),
                                   transforms.Normalize([0], [1])])}
    with torch.no_grad():
        for c in hole_coords:
            center_x, center_y = (c[0]+c[2])//2, (c[1]+c[3])//2
            ext = np.zeros((100,100))
            extracted_square = square[int(center_y)-50:int(center_y)+50, int(center_x)-50:int(center_x)+50]
            extracted_square = cv2.normalize(extracted_square,None, 0, 255,cv2.NORM_MINMAX)
            ext[:extracted_square.shape[0],:extracted_square.shape[1]] = extracted_square
            normed1 = cv2.normalize(ext, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
            normed1 = (normed1*255).astype(np.uint8)
            img = Image.fromarray(normed1,'L')
            img = data_transform["val"](img)
            # print(img.shape)
            img = img.unsqueeze(0)
            pred = model(img.to(device))
            # print(pred)
            pred = torch.max(pred, dim=1)[1]
            pred_c = pred.cpu().data.numpy()
            # print(pred_c)
            lb = pred_c[0]
            labels.append(lb)
    return hole_coords, labels

def detect_holes_rcnn(square, imgsz = 1280, thresh = 0.1, iou = 0.5, device = '0', weights_circle = ''):
    all_hole_coords = []
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 8   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = thresh
    cfg.MODEL.WEIGHTS = weights_circle
    cfg.INPUT.MIN_SIZE_TEST = imgsz
    cfg.INPUT.MAX_SIZE_TEST = imgsz
    cfg.TEST.DETECTIONS_PER_IMAGE = 500
    if device == 'cpu':
        cfg.MODEL.DEVICE='cpu'

    # square = cv2.normalize(square, None, 0, 255,cv2.NORM_MINMAX)
    dim_square = len(square.shape)
    if dim_square == 2:
        r, c = square.shape
        if r != c:
            max_shape = np.max([r,c])
            square = to_shape(square, (max_shape, max_shape))
        else:
            max_shape = r
        im_re = cv2.resize(square, (imgsz,imgsz))
    if dim_square == 3:
        if square.shape[0] == 1 or square.shape[0] == 3:
            # sp = square.shape[1:]
            r, c = square.shape[1:]
            if r != c:
                max_shape = np.max([r,c])
                square = to_shape(square[0], (max_shape, max_shape))
            else:
                max_shape = r
            im_re = cv2.resize(square, (imgsz, imgsz))
    im_re = cv2.normalize(im_re, None, 0, 255, cv2.NORM_MINMAX)
    resized = np.uint8(im_re)
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
        if_square = check_if_square(sq_coords[0],sq_coords[1],sq_coords[2],sq_coords[3], 1.5, 0.5)
        if if_square:
            all_hole_coords.append(sq_coords)
    torch.cuda.empty_cache()
    return all_hole_coords


    # img_re_multi = np.zeros((3, imgsz, imgsz))
    # img_re_multi[0,:,:] = im_re
    # img_re_multi[1,:,:] = im_re 
    # img_re_multi[2,:,:] = im_re


def detect_holes_yolo(square, imgsz = 1280, augment = False, conf_thres = 0.7, iou_thres = 0.45, classes = None, agnostic = False, device = '', weights_circle = ''):
    #input needs to be a numpy array
    all_hole_coords = []
    all_contam_coords = []
    dim_square = len(square.shape)
    device = select_device(device)
    half = device.type != 'cpu'
    # square = cv2.normalize(square, None, 0, 255,cv2.NORM_MINMAX)
    model = attempt_load(weights_circle, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    if half:
        model.half() 
    if dim_square == 2:
        square = cv2.normalize(square, None, 0, 255,cv2.NORM_MINMAX)
        square = auto_contrast(square)
        sp = square.shape
        im_re = letterbox(square, imgsz, stride = stride)[0]
        # print('im_re,', im_re.shape)
        # im_re = cv2.resize(square, (imgsz,imgsz))
    if dim_square == 3:
        if square.shape[0] == 1 or square.shape[0] == 3:
            sp = square.shape[1:]
            square = cv2.normalize(square[0], None, 0, 255,cv2.NORM_MINMAX)
            square = auto_contrast(square)
            im_re = letterbox(square, imgsz, stride = stride)[0]
            # im_re = cv2.resize(square, (imgsz, imgsz))
    # img_re_multi = np.zeros((sp[0],sp[1],3))
    img_re_multi = np.dstack((im_re, im_re, im_re))
    img_re_multi = img_re_multi.transpose(2,0,1)
    # img_re_multi[:,:,0] = im_re
    # img_re_multi[:,:,1] = im_re 
    # img_re_multi[:,:,2] = im_re
    # img = im_re[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
    # img = np.ascontiguousarray(img)
    img_s = torch.from_numpy(img_re_multi).to(device)
    img_s = img_s.half() if half else img_s.float()  # uint8 to fp16/32
    img_s /= 255.0  # 0 - 255 to 0.0 - 1.0
    if img_s.ndimension() == 3:
        img_s = img_s.unsqueeze(0)
    
    # half = device.type != 'cpu' 
    
    names = model.module.names if hasattr(model, 'module') else model.names

    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    with torch.no_grad():
        pred = model(img_s, augment=augment)[0]
    pred = non_max_suppression(pred, conf_thres, iou_thres, classes=classes, agnostic=agnostic)
    for i, det in enumerate(pred):
        gn = torch.tensor(sp)[[1, 0, 1, 0]]
        # print('gn,', gn)
        if len(det):
                # Rescale boxes from img_size to im0 size
            det[:, :4] = scale_coords(img_s.shape[2:], det[:, :4], sp).round()
            for *xyxy, conf, cls in reversed(det):  # detections per image
                xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()
                c = int(cls)
                # print(xywh)
                # print('c', c)
                if c == 0:
                    x,y,w,h = xywh[0],xywh[1],xywh[2],xywh[3]
                    l,t,r,b = convert_yolo_to_cv(x,y,w,h, sp[0], sp[1])
                    if l==r or t==b :
                            if_sq = False
                    else:
                        if_sq = check_if_square(l,t,r,b, 1.2, 0.8)
                    if if_sq:
                        all_hole_coords.append([l,t,r,b])
                else:
                    x,y,w,h = xywh[0],xywh[1],xywh[2],xywh[3]
                    l,t,r,b = convert_yolo_to_cv(x,y,w,h, sp[0], sp[1])
                    all_contam_coords.append([l,t,r,b])
    torch.cuda.empty_cache()
    return all_hole_coords, all_contam_coords



    

