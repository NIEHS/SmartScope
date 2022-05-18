from detect_squares import detect
from detect_holes import detect_holes_yolo, detect_holes_rcnn, detect_holes, detect_and_classify_holes
import cv2
import numpy as np
# from model import resnet34
import torch
print('gpu', torch.cuda.is_available())
from torchvision import transforms, datasets
import mrcfile


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


data_transform = {
    "train": transforms.Compose([transforms.RandomResizedCrop(100),
                                 transforms.RandomHorizontalFlip(),
                                 transforms.ToTensor(),
                                 transforms.Normalize([0], [1])]),
    "val": transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0], [1])])}
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
# model = resnet34(num_classes=3).to(device)
# model_weights_path = "/nfs/bartesaghilab2/qh36/all_data/ctf_analysis/resNet34_newlabel2.pth"
# model.load_state_dict(torch.load(model_weights_path, map_location=device))
# model.eval()
# print(model)

# square_weights = '/opt/smartscope/Template_files/weights/square_weights/model_new_weights_env.pth'

# if not torch.cuda.is_available():

#     coord, labels, img_mult, scale = detect(
#         '/mnt/data/testing/20220510_demo_test/1_grid_1/grid_1_atlas/grid_1_atlas.mrc', device='cpu', weights=square_weights)
# else:
#     coord, labels, img_mult, scale = detect(
#         '/mnt/data/testing/20220510_demo_test/1_grid_1/grid_1_atlas/grid_1_atlas.mrc', device='0', weights=square_weights)

# np.random.seed(10)
# label_dict = {'squares': 0, 'contaminated': 1, 'cracked': 2, 'dry': 3, 'fraction': 4, 'small': 5, 'square': 6}
# # color = [list(np.random.choice(range(100,256), size=3)) for i in range(7)]
# color = [[0, 0, 0], [29, 148, 247], [140, 0, 236], [63, 198, 141], [157, 167, 0], [145, 45, 102], [36, 28, 237]]
# # print('color,', color)
# # color = [int(i) for i in color]
# # color = [[int(i) for i in j] for j in color]
# # print('color,', color)
# # img_mult = cv2.resize(img_mult, (img_mult.shape[0]//4, img_mult.shape[1]//4))
# # dat_multi_channel = np.dstack((img_mult,img_mult,img_mult))
# dat_multi_channel = img_mult
# ind = 0
# for sq_coords in coord:
#     # print(sq_coords)
#     # print(color[label_dict[labels[ind]]])
#     cv2.rectangle(dat_multi_channel, (int(sq_coords[0] // scale), int(sq_coords[1] // scale)),
#                   (int(sq_coords[2] // scale), int(sq_coords[3] // scale)), color[label_dict[labels[ind]]], 5)
#     cv2.putText(dat_multi_channel, labels[ind], (int(sq_coords[0] // scale), int(sq_coords[1] // scale - 10)),
#                 fontFace=cv2.FONT_HERSHEY_COMPLEX, fontScale=1, color=color[label_dict[labels[ind]]], thickness=2)
#     ind += 1
# # # # dat_multi_channel = cv2.resize(dat_multi_channel, (4096, 4096))
# cv2.imwrite('AR3-0528-3_atlas.png', dat_multi_channel)

square_path = '/mnt/data/CopelandW/20220506_Twinkle-0504/4_AR1-0504_3/raw/AR1-0504_3_square89.mrc'
with mrcfile.open(square_path) as mrc:
    square = mrc.data

square = cv2.normalize(square, None, 0, 255, cv2.NORM_MINMAX)
square = auto_contrast(square)
# # print(square.shape)
# # square_path = '/hpc/home/qh36/research/qh36_2/all_data/newer_group/20210812_0804_T2-3/2_T2-2/pngs/T2-2_square15.png'
# # square = cv2.imread(square_path, 0)
hole_coords, _ = detect_holes_yolo(square, conf_thres=0.2, iou_thres=0.15,
                                   weights_circle='/opt/smartscope/Template_files/weights/circle_weights/circle_weight_12_7_21.pt')
print(hole_coords)
# # # # hole_coords = detect_holes_rcnn(square, weights_circle = 'runs/circle_weights/rcnn_circle_weights.pth')
# # # # color_dict = [(255,0,0),(0,255,0),(0,0,255)]
# # # # # square = (square - square.mean())/square.std()
# # # # # square = quantize(square)
# # square = cv2.normalize(square, None, 0, 255,cv2.NORM_MINMAX)
# # square = auto_contrast(square)
# # # # # square = cv2.equalizeHist(np.uint8(square))
sq_multi_channel = np.dstack((square, square, square))
# # # # hole_coords, lbs  = detect_and_classify_holes(square, weights_circle = 'runs/circle_weights/added_circle_yolo.pt', weights_class ='/nfs/bartesaghilab2/qh36/all_data/ctf_analysis/resNet34_newlabel2.pth', method='yolo')
# idx = 0
for c in hole_coords:
    cv2.rectangle(sq_multi_channel, (int(c[0]), int(c[1])), (int(c[2]), int(c[3])), (200, 60, 185), 8)
    # idx += 1
# # # print(hole_coords)
# # square = cv2.normalize(square, None, 0, 255,cv2.NORM_MINMAX)
# # sq_multi_channel = np.dstack((square, square, square))
# # all_squares = []
# # color_dict = [(255,0,0),(0,255,0),(0,0,255)]
# # for c in hole_coords:
# #     center_x, center_y = (c[0]+c[2])//2, (c[1]+c[3])//2
# #     ext = np.zeros((100,100))
# #     extracted_square = square[int(center_y)-50:int(center_y)+50, int(center_x)-50:int(center_x)+50]
# #     extracted_square = cv2.normalize(extracted_square,None, 0, 255,cv2.NORM_MINMAX)
# #     ext[:extracted_square.shape[0],:extracted_square.shape[1]] = extracted_square
# #     normed1 = cv2.normalize(ext, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
# #     normed1 = (normed1*255).astype(np.uint8)
# #     img = Image.fromarray(normed1,'L')
# #     img = data_transform["val"](img)
# #     # print(img.shape)
# #     img = img.unsqueeze(0)
# #     pred = model(img.to(device))
# #     # print(pred)
# #     pred = torch.max(pred, dim=1)[1]
# #     pred_c = pred.cpu().data.numpy()
# #     # print(pred_c)
# #     lb = pred_c[0]

# #     # print(img.shape)
# #     # all_squares.append(ext)
# #     # print(extracted_square.shape)
# #     cv2.rectangle(sq_multi_channel,(c[0],c[1]),(c[2],c[3]),color_dict[lb],2)
# # cv2.putText(sq_multi_channel,'<7',(100,150),fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=3,color = (255,0,0),thickness=2)
# # cv2.putText(sq_multi_channel,'7<=res<12',(100,250),fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=3,color = (0,255,0),thickness=2)
# # cv2.putText(sq_multi_channel,'>12',(100,350),fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=3,color = (0,0,255),thickness=2)
# # with open('ctf2.pickle', 'rb') as handle:
# #     ctf_dict2 = pickle.load(handle)
# # # print(b)
# # # for k,v in ctf_dict2.items():
# # #     pos = v['pos']
# # #     fit = v['fit']
# # #     # print(fit[:4])
# # #     cv2.putText(sq_multi_channel,fit[:4],(pos[0],pos[1]),fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1,color = (0,255,0),thickness=2)

cv2.imwrite('misalign_square13.png', sq_multi_channel)
# # all_squares = np.asarray(all_squares)
# # print(all_squares.shape)
# # np.save('extract.npy',all_squares)
