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
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path, save_one_box
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


def detect(opt):
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 8   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.05

    source, mrcs, weights_square, weights_circle, view_img, save_txt, imgsz = opt.source, opt.mrcs, opt.weights_square, opt.weights_circle, opt.view_img, opt.save_txt, opt.img_size
    cfg.MODEL.WEIGHTS = weights_square
    predictor_square = DefaultPredictor(cfg)
    save_img = not opt.nosave and not source.endswith('.txt')  # save inference images
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))
    all_pngs = glob.glob(source+'*.mrc')
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA
    trans = transforms.Compose([
            transforms.ToTensor(), 
            transforms.Normalize((0),(1))])

    backbone = resnet18()
    pretrain_path = '/nfs/bartesaghilab/qh36/Unsupervised-Classification/new_holes/new_44_diff_aug_100epoch/squares/pretext/model.pth.tar'
    state = torch.load(pretrain_path, map_location='cpu')
    model_c = ContrastiveModel(backbone, middle_dim = 128, features_dim = 64)
    # missing = model_c.load_state_dict(state, strict=False)
    model_c.load_state_dict(state)
    # print(missing)
    print('loaded previous weights')
    # assert(set(missing[1]) == {
    #     'contrastive_head.0.weight', 'contrastive_head.0.bias', 
    #     'contrastive_head.2.weight', 'contrastive_head.2.bias',
    #     'contrastive_head.4.weight', 'contrastive_head.4.bias'}
    #     or set(missing[1]) == {
    #     'contrastive_head.weight', 'contrastive_head.bias'})
    print(model_c)
    # model_c = torch.nn.DataParallel(model_c)
    model_c = model_c.cuda()
    # print(model_c)

    # model_checkpoint = torch.load('/nfs/bartesaghilab/qh36/Unsupervised-Classification/new_holes/padded_44_more_imgs_50epoch/squares/scan/model.pth.tar', map_location='cpu')
    # # model.load_state_dict(model_checkpoint['model'])
    # model_c.module.load_state_dict(model_checkpoint['model'])
    model_c.eval()

    # Load model
    model = attempt_load(weights_circle, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    if half:
        model.half() 
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(7)]
    color_dict = {0:(255,0,0),1:(0,255,0),2:(0,0,255),3:(80,80,80),4:(10,150,200),5:(255,100,10)}
    label_dict = ['squares','contaminated','cracked','dry','fraction','small','square']
    print(colors)
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    t0 = time.time()
    saved_dir = '/hpc/home/qh36/research/qh36/all_data/all_atlases/analysis/labeled/'
    all_circles = []
    all_labels = []
    all_features = []
    square_ind = []
    all_coords = []
    all_squares = []
    square_names = []
    locs = []
    ind = 0
    with mrcfile.open(mrcs) as mrc:
        atlas = mrc.data
    atlas = cv2.normalize(atlas, None, 0, 255, cv2.NORM_MINMAX)
    atlas_multi_channel = np.dstack((atlas, atlas, atlas))

    for im in all_pngs:
        # sq_coords =[]
        square_names.append(im.split('/')[-1][:-4])
        # img = cv2.imread(im)
        # name = im.split('/')[-1][:-4]
        # corresponding_mrc = mrcs+name+'.mrc'
        # if os.path.exists(corresponding_mrc):
        with mrcfile.open(im) as mrc:
            dat = mrc.data
            loc_y, loc_x = mrc.header.nxstart, mrc.header.nystart
        locs.append([loc_y, loc_x])
        loc_y, loc_x = loc_y-dat.shape[0]//2, loc_x-dat.shape[1]//2
            # print(mrc.header.nxstart)
            # print(mrc.header.nystart)
            # print(dat.shape)
        img = cv2.normalize(dat, None, 0, 255,cv2.NORM_MINMAX)
        # dat_re = cv2.resize(dat, (imgsz, imgsz))

        dat_multi_channel = np.dstack((img, img, img))
        all_squares.append(dat_multi_channel)
        # r, c = dat.shape 
        # max_side = np.max([r,c])
        # scale = max_side/img.shape[0]
        # outputs = predictor_square(img)
        # out_inst = outputs["instances"].to("cpu")
        # pred_box = out_inst.pred_boxes
        # scores = out_inst.scores
        # pred_classes = out_inst.pred_classes
        # box_tensor = pred_box.tensor
        # keep = torchvision.ops.nms(box_tensor, scores, 0.8)
        # pred_box_keep = pred_box[keep]
        # scores_keep = scores[keep]
        # pred_classes_keep = pred_classes[keep]
        # pred_box_keep.scale(scale, scale)
        # ind = 0 
        s = ''
        
        # for sq_coords in pred_box_keep:
        #     if_square = check_if_square(sq_coords[0],sq_coords[1],sq_coords[2],sq_coords[3], 1.7, 0.3)
        #     if if_square:
        #         extracted_sq = dat[int(sq_coords[1]):int(sq_coords[3]),int(sq_coords[0]):int(sq_coords[2])]
        #         extracted_sq = cv2.normalize(extracted_sq, None, 0, 255,cv2.NORM_MINMAX)
        #         labeled = int(pred_classes_keep[ind])
        #         cv2.rectangle(dat_multi_channel,(sq_coords[0],sq_coords[1]),(sq_coords[2],sq_coords[3]),colors[labeled],4)
        #         cv2.putText(dat_multi_channel, label_dict[labeled],(sq_coords[0]-2,sq_coords[1]-2), fontFace = cv2.FONT_HERSHEY_SIMPLEX, fontScale = 3, color = colors[labeled], thickness=2)
        # # cv2.imwrite(saved_dir+name+'.png',dat_multi_channel)
        #         max_h = np.max(extracted_sq.shape)
        #         padded = np.zeros((max_h, max_h))
        #         padded[:extracted_sq.shape[0],:extracted_sq.shape[1]] = extracted_sq
                # padded[1,:extracted_sq.shape[0],:extracted_sq.shape[1]] = extracted_sq
                # padded[2,:extracted_sq.shape[0],:extracted_sq.shape[1]] = extracted_sq
        im_re = cv2.resize(img, (imgsz,imgsz))
        img_re_multi = np.zeros((3, imgsz, imgsz))
        img_re_multi[0,:,:] = im_re
        img_re_multi[1,:,:] = im_re 
        img_re_multi[2,:,:] = im_re
        img_s = torch.from_numpy(img_re_multi).to(device)
        img_s = img_s.half() if half else img_s.float()  # uint8 to fp16/32
        img_s /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img_s.ndimension() == 3:
            img_s = img_s.unsqueeze(0)
        t1 = time_synchronized()
        # print(img_s.shape)
        pred = model(img_s, augment=opt.augment)[0]

                # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()
        
        for i, det in enumerate(pred):  # detections per image
            # if webcam:  # batch_size >= 1
            #     p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            # else:
            #     p, s, im0, frame = path, '', im0s.copy(), getattr(dataset, 'frame', 0)

            # p = Path(p)  # to Path
            # save_path = str(save_dir / p.name)  # img.jpg
            # txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
            s += '%gx%g ' % img_s.shape[2:]  # print string
            gn = torch.tensor(img.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img_s.shape[2:], det[:, :4], img.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):  # detections per image
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()
                    x,y,w,h = xywh[0],xywh[1],xywh[2],xywh[3]
                    l,t,r,b = convert_yolo_to_cv(x,y,w,h, img.shape[0], img.shape[1])
                    # print(l,t,r,b)
                    if l==r or t==b :
                        if_sq = False
                    else:
                        if_sq = check_if_square(l,t,r,b, 1.2, 0.8)

                    if if_sq:
                        # l_m,t_m,r_m,b_m = l + sq_coords[0], t + sq_coords[1], r + sq_coords[0], b + sq_coords[1]
                        l_m, t_m, r_m, b_m = l, t, r, b
                        center_x, center_y = int((l_m+r_m)//2), int((t_m+b_m)//2)
                        all_coords.append([l_m+loc_x, t_m+loc_y, r_m+loc_x, b_m+loc_y])
                        # cv2.rectangle(dat_multi_channel,(l_m, t_m),(r_m,b_m),(255,255,0),1)
                        # ext = dat[int(t_m):int(b_m), int(l_m):int(r_m)]
                        ext_2 = dat[center_y-22:center_y+22, center_x-22:center_x+22]
                        # h, w = ext.shape 
                        h, w = ext_2.shape
                        if h <=44 and w > 44:
                            ext_c = ext[:,:44]
                            ext_c = to_shape(ext_c, (44,44))
                        elif h > 44 and w <= 44:
                            ext_c = ext[:44,:]
                            ext_c = to_shape(ext_c, (44,44))
                        elif h <= 44 and w <= 44:
                            # ext_c = to_shape(ext[:,:], (44,44))
                            ext_2 = to_shape(ext_2[:,:],(44,44))
                        elif h > 44 and w > 44:
                            max_side = np.max([h,w])
                            ext_b = to_shape(ext, (max_side, max_side))
                            ext_c = cv2.resize(ext_b, (44, 44))
                        # ext_c = cv2.normalize(ext_c, None, 0, 255,cv2.NORM_MINMAX)
                        ext_2 = cv2.normalize(ext_2, None, 0, 255, cv2.NORM_MINMAX)
                        # all_circles.append(ext_2)
                        # all_labels.append(np.random.randint(5))
                        # img_flatten =ext_2.flatten()
                        stats = []
                        stats.append(np.mean(ext_2))
                        stats.append(np.median(ext_2))
                        stats.append(np.std(ext_2))
                        stats.append(np.quantile(ext_2, 0.25))
                        stats.append(np.quantile(ext_2, 0.75))
                        stats.append(np.mean(ext_2[22-5:22+5, 22-5:22+5]))
                        stats.append(np.std(ext_2[22-5:22+5, 22-5:22+5]))
                        stats.append(np.median(ext_2[22-5:22+5, 22-5:22+5]))
                        stats.append(np.quantile(ext_2[22-5:22+5, 22-5:22+5], 0.25))
                        stats.append(np.quantile(ext_2[22-5:22+5, 22-5:22+5], 0.75))
                        stats.append(np.mean(ext_2[22-10:22+10, 22-10:22+10]))
                        stats.append(np.std(ext_2[22-10:22+10, 22-10:22+10]))
                        stats.append(np.median(ext_2[22-10:22+10, 22-10:22+10]))
                        stats.append(np.quantile(ext_2[22-10:22+10, 22-10:22+10], 0.25))
                        stats.append(np.quantile(ext_2[22-10:22+10, 22-10:22+10], 0.75))

                        # im = Image.fromarray(ext_2,'L')
                        # trans_im = trans(im)
                        # trans_im = torch.unsqueeze(trans_im, 0)
                        # trans_im = trans_im.cuda(non_blocking=True)
                        # res = model_c(trans_im)
                        # # print(res.shape)
                        # res_np = res.cpu().numpy()
                        #         # cod_np = np.array([l,t,r,b])
                        #         # cod_np = np.expand_dims(cod_np, axis = 0)
                        #         # res_np_c = np.concatenate((res_np, cod_np),axis = 1)
                        #         # print(res_np_c.shape)
                        square_ind.append(ind)
                        # all_features.append(res_np)
                        # all_features.append(img_flatten)
                        all_features.append(stats)
        ind += 1
        # all_coords.append(sq_coords)                
                # ind += 1
    all_features = np.asarray(all_features)
        # print(all_features.shape)
                # all_features = np.squeeze(all_features)
                # print(all_features.shape)
    if all_features.shape[0]>= 3:
        all_features = np.squeeze(all_features)
        scaler = StandardScaler()
        all_features = scaler.fit_transform(all_features)
        pca = PCA(n_components=0.95, svd_solver='full')
        new_features = pca.fit_transform(all_features)
        kmeans = KMeans(n_clusters = 3, random_state = 0).fit(new_features)
        labels = kmeans.predict(new_features)
        # print(labels.shape)
        for idd, lbb in enumerate(labels):
            coords = all_coords[idd]
            l_m, t_m, r_m, b_m = coords[0],coords[1],coords[2],coords[3]
            # inds = square_names[square_ind[idd]]
            cv2.rectangle(atlas_multi_channel, (l_m, t_m),(r_m, b_m),color_dict[lbb],1)

    elif all_features.shape[0] < 3 and all_features.shape[0]>0:
        for coords in all_coords:
            l_m, t_m, r_m, b_m = coords[0],coords[1],coords[2],coords[3]
            cv2.rectangle(atlas_multi_channel, (l_m,t_m),(r_m,b_m),color_dict[0],1)
    for i,j in enumerate(locs):
        cv2.putText(atlas_multi_channel, square_names[i], (j[1]-5, j[0]-5),fontFace = cv2.FONT_HERSHEY_SIMPLEX, fontScale = 4, color=(0,255,0))

    # for ids, im in enumerate(all_squares):
    cv2.imwrite(saved_dir+'ARJB1-2'+'_atlas'+'.png', atlas_multi_channel)


                                    # print(res_np.shape)
                                    # output = res['output']
                                    # for i, output_i in enumerate(output):
                                    #        pred = torch.argmax(output_i, dim=1)
                                    #        pred_np = pred.cpu().numpy()
                                    #        # print(pred_np)
                                    # label = pred_np[0]
                                    # cv2.rectangle(dat_multi_channel, (l_m,t_m),(r_m,b_m),color_dict[label],1)




            # 
                # ind += 1
           
    # all_circles = np.asarray(all_circles)
    # all_labels = np.asarray(all_labels)
    # np.save('extracted_circles_new.npy',all_circles)
    # np.save('pseudo_labels_new.npy',all_labels)









    # # Directories
    # save_dir = increment_path(Path(opt.project) / opt.name, exist_ok=opt.exist_ok)  # increment run
    # (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Initialize
    # set_logging()
    # device = select_device(opt.device)
    # half = device.type != 'cpu'  # half precision only supported on CUDA

    # # Load model
    # model = attempt_load(weights, map_location=device)  # load FP32 model
    # stride = int(model.stride.max())  # model stride
    # imgsz = check_img_size(imgsz, s=stride)  # check img_size
    # if half:
    #     model.half()  # to FP16

    # # Second-stage classifier
    # classify = False
    # if classify:
    #     modelc = load_classifier(name='resnet101', n=2)  # initialize
    #     modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # # Set Dataloader
    # vid_path, vid_writer = None, None
    # if webcam:
    #     view_img = check_imshow()
    #     cudnn.benchmark = True  # set True to speed up constant image size inference
    #     dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    # else:
    #     dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # # Get names and colors
    # names = model.module.names if hasattr(model, 'module') else model.names
    # colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # # Run inference
    # if device.type != 'cpu':
    #     model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    # t0 = time.time()
    # for path, img, im0s, vid_cap in dataset:
    #     img = torch.from_numpy(img).to(device)
    #     img = img.half() if half else img.float()  # uint8 to fp16/32
    #     img /= 255.0  # 0 - 255 to 0.0 - 1.0
    #     if img.ndimension() == 3:
    #         img = img.unsqueeze(0)

    #     # Inference
    #     t1 = time_synchronized()
    #     pred = model(img, augment=opt.augment)[0]

    #     # Apply NMS
    #     pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
    #     t2 = time_synchronized()

    #     # Apply Classifier
    #     if classify:
    #         pred = apply_classifier(pred, modelc, img, im0s)

    #     # Process detections
    #     for i, det in enumerate(pred):  # detections per image
    #         if webcam:  # batch_size >= 1
    #             p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
    #         else:
    #             p, s, im0, frame = path, '', im0s.copy(), getattr(dataset, 'frame', 0)

    #         p = Path(p)  # to Path
    #         save_path = str(save_dir / p.name)  # img.jpg
    #         txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
    #         s += '%gx%g ' % img.shape[2:]  # print string
    #         gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
    #         if len(det):
    #             # Rescale boxes from img_size to im0 size
    #             det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

    #             # Print results
    #             for c in det[:, -1].unique():
    #                 n = (det[:, -1] == c).sum()  # detections per class
    #                 s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

    #             # Write results
    #             for *xyxy, conf, cls in reversed(det):
    #                 if save_txt:  # Write to file
    #                     xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
    #                     line = (cls, *xywh, conf) if opt.save_conf else (cls, *xywh)  # label format
    #                     with open(txt_path + '.txt', 'a') as f:
    #                         f.write(('%g ' * len(line)).rstrip() % line + '\n')

    #                 if save_img or opt.save_crop or view_img:  # Add bbox to image
    #                     c = int(cls)  # integer class
    #                     label = None if opt.hide_labels else (names[c] if opt.hide_conf else f'{names[c]} {conf:.2f}')

    #                     plot_one_box(xyxy, im0, label=label, color=colors[c], line_thickness=opt.line_thickness)
    #                     if opt.save_crop:
    #                         save_one_box(xyxy, im0s, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)

    #         # Print time (inference + NMS)
    #         print(f'{s}Done. ({t2 - t1:.3f}s)')

    #         # Stream results
    #         if view_img:
    #             cv2.imshow(str(p), im0)
    #             cv2.waitKey(1)  # 1 millisecond

    #         # Save results (image with detections)
    #         if save_img:
    #             if dataset.mode == 'image':
    #                 cv2.imwrite(save_path, im0)
    #             else:  # 'video' or 'stream'
    #                 if vid_path != save_path:  # new video
    #                     vid_path = save_path
    #                     if isinstance(vid_writer, cv2.VideoWriter):
    #                         vid_writer.release()  # release previous video writer
    #                     if vid_cap:  # video
    #                         fps = vid_cap.get(cv2.CAP_PROP_FPS)
    #                         w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    #                         h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    #                     else:  # stream
    #                         fps, w, h = 30, im0.shape[1], im0.shape[0]
    #                         save_path += '.mp4'
    #                     vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    #                 vid_writer.write(im0)

    # if save_txt or save_img:
    #     s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
    #     print(f"Results saved to {save_dir}{s}")

    # print(f'Done. ({time.time() - t0:.3f}s)')


def to_shape(a, shape):
    y_, x_ = shape
    if len(a.shape) == 3:
        y, x,c = a.shape
    else:
        y, x = a.shape
    y_pad = (y_-y)
    x_pad = (x_-x)
    if len(a.shape) == 3:
        return np.pad(a,((y_pad//2, y_pad//2 + y_pad%2), 
                         (x_pad//2, x_pad//2 + x_pad%2),(0,0)),
                      mode = 'constant')
    else:
        return np.pad(a,((y_pad//2, y_pad//2 + y_pad%2), 
                         (x_pad//2, x_pad//2 + x_pad%2)),
                      mode = 'constant')


def convert_yolo_to_cv(x,y,w,h, dh, dw):
    l = int((x - w / 2) * dw)
    r = int((x + w / 2) * dw)
    t = int((y - h / 2) * dh)
    b = int((y + h / 2) * dh)
    if l < 0:
        l = 0
    if r > dw - 1:
        r = dw - 1
    if t < 0:
        t = 0
    if b > dh - 1:
        b = dh - 1
    return l,t,r,b

def check_if_square(l,t,r,b, thresh1, thresh2):
    if (r-l)/(b-t) > thresh1 or (r-l)/(b-t) < thresh2:
        return False
    else:
        return True


def doOverlap(l1, r1, l2, r2):
     
    # To check if either rectangle is actually a line
      # For example  :  l1 ={-1,0}  r1={1,1}  l2={0,-1}  r2={0,1}
       
    if (l1.x == r1.x or l1.y == r2.y or l2.x == r2.x or l2.y == r2.y):
        # the line cannot have positive overlap
        return False
       
     
    # If one rectangle is on left side of other
    if(l1.x >= r2.x or l2.x >= r1.x):
        return False
 
    # If one rectangle is above other
    if(l1.y <= r2.y or l2.y <= r1.y):
        return False
 
    return True

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights_square', type=str, default='yolov5s.pt', help='model.pt path(s)')
    parser.add_argument('--weights_circle', type=str, default='yolov5s.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='data/pngs', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--mrcs', type=str, default='data/mrcs', help='pngs file')
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.2, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.4, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-crop', action='store_true', help='save cropped prediction boxes')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--line-thickness', default=3, type=int, help='bounding box thickness (pixels)')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='hide labels')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='hide confidences')
    opt = parser.parse_args()
    print(opt)
    check_requirements(exclude=('pycocotools', 'thop'))
    with torch.no_grad():
        detect(opt=opt)

