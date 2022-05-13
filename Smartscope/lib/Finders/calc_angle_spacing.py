import cv2
import numpy as np
from skimage.util import img_as_ubyte
from skimage.morphology import convex_hull_image
from scipy.spatial import distance
import math


def output_pattern(img):
    rat = img.shape[0] // 128
    resized = cv2.resize(img, (128, 128), interpolation=cv2.INTER_AREA)
    img_normed = cv2.normalize(resized, None, 0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    img_int = img_as_ubyte(img_normed)
    ret, thresh = cv2.threshold(img_int, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    chull = convex_hull_image(thresh)
    chull_num = chull.astype(int) * 255.0
    contours, h = cv2.findContours(chull_num.astype(np.uint8), 1, 2)
    cnt = contours[0]
    cnt_orig = cnt * rat
    rect = cv2.minAreaRect(cnt_orig)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    width = int(rect[1][0])
    height = int(rect[1][1])
    ratio = np.mean(img.shape / np.array([width, height]))
    src_pts = box.astype("float32")
    dst_pts = np.array([[0, height - 1],
                        [0, 0],
                        [width - 1, 0],
                        [width - 1, height - 1]], dtype="float32")

    # the perspective transformation matrix
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # directly warp the rotated rectangle to get the straightened rectangle
    warped = cv2.warpPerspective(img, M, (width, height))
    img_normed = cv2.normalize(warped, None, 0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    img_int = img_as_ubyte(img_normed)
    equ2 = cv2.equalizeHist(img_int)
    warped_fft = np.log(np.abs(np.fft.fftshift(np.fft.fft2(equ2))))
    centered = warped_fft[warped_fft.shape[0] // 2 - 200:warped_fft.shape[0] //
                          2 + 200, warped_fft.shape[1] // 2 - 200:warped_fft.shape[1] // 2 + 200]
    flattened = centered.flatten()
    sorted_flatten = np.sort(flattened)
    init = np.zeros((400, 400))
    indc = np.argwhere(centered > sorted_flatten[-1] * 0.77)
    print(len(indc))
    # print(indc)
    for i in indc:
        #         print(np.linalg.norm(i-[200,200]))
        #     print(i[0],i[1])
        #     print(init[i[0],i[1]])
        if centered[i[0], i[1]] == np.max(centered[i[0] - 5:i[0] + 5, i[1] - 5:i[1] + 5]):
            #         if np.linalg.norm(i-[200, 200]) > 30:
            init[i[0], i[1]] = 255
            init[i[0], i[1] - 1] = 255
            init[i[0] + 1, i[1]] = 255
            init[i[0], i[1] + 1] = 255
            init[i[0] - 1, i[1]] = 255
    init = init.astype(np.uint8)
    filt = cv2.medianBlur(init, 3)
    connectivity = 8
    # Perform the operation
    output = cv2.connectedComponentsWithStats(filt, connectivity)
    centers = output[3]
    centers = np.ceil(centers).astype(np.uint8)
    # print(centers)
    remained = []
    remained.append(np.array([200, 200], dtype=np.uint8))
    for i in centers:
        # print(i)
        if not np.linalg.norm(i - [200, 200]) < 3:
            remained.append(i)

    init2 = np.zeros((400, 400))
    for j in remained:
        init2[j[1], j[0]] = 255
    return init2, remained, box, ratio


def closest_pt(dist, pat1):
    closest_pt = {}
    for i in dist:
        sr_i = np.sort(i)
        dist1 = sr_i[0]
        dist2 = sr_i[1]
        dist3 = sr_i[2]
        pt1 = pat1[np.where(i == dist1)][0]
        pt1 = tuple(pt1)
        if dist2 == dist3:
            pts = pat1[np.where(i == dist2)]
            pt2 = pts[0]
            pt3 = pts[1]
            closest_pt[pt1] = np.array([pt2, pt3])
        else:
            if abs(dist3 - dist2) < 2:
                pt2 = pat1[np.where(i == dist2)][0]
                pt3 = pat1[np.where(i == dist3)][0]
                closest_pt[pt1] = np.array([pt2, pt3])
            else:
                pt2 = pat1[np.where(i == dist2)][0]
                closest_pt[pt1] = np.array(pt2)
    return closest_pt


def calc_angle_dist(k, v):
    if k[0] >= v[0] and k[1] >= v[1]:
        dx = float(k[0]) - float(v[0])
        dy = float(k[1]) - float(v[1])
        theta = math.atan2(dx, dy)
        angle = math.degrees(theta)  # angle is in (-180, 180]
        if angle < 0:
            angle = 360 + angle
        angle = round(angle, 2)
        dist = np.sqrt(dx**2 + dy**2)

    elif k[0] <= v[0] and k[1] <= v[1]:
        dx = float(v[0]) - float(k[0])
        dy = float(v[1]) - float(k[1])
        theta = math.atan2(dx, dy)
        angle = math.degrees(theta)  # angle is in (-180, 180]
        if angle < 0:
            angle = 360 + angle
        angle = round(angle, 2)
        dist = np.sqrt(dx**2 + dy**2)

    else:
        dx = abs(float(k[0]) - float(v[0]))
        dy = abs(float(k[1]) - float(v[1]))
        theta = math.atan2(dy, dx)
        angle = math.degrees(theta)
        if angle < 0:
            angle = 360 + angle
        angle = round(angle, 2)
        dist = np.sqrt(dx**2 + dy**2)
    return angle, dist


def check_if_key_in_dict(k, d):
    k_range = np.arange(k - 4, k + 4)
    for i in k_range:
        if np.round(i) in d.keys():
            exist = True
            key = i
            return exist, key

        else:
            exist = False
            key = None
    return exist, key


def get_all_angles_dict(closest_pt):
    all_angles = {}
    for k, v in closest_pt.items():
        if len(v.shape) > 1:
            # more than 1 closest pt
            num_of_closest_pt = v.shape[0]
            pt1 = v[0]
            # print(pt1)
            pt2 = v[1]
            # print(np.array([k[0],k[1]]))
            angle1, dist1 = calc_angle_dist(k, pt1)
            angle2, dist2 = calc_angle_dist(k, pt2)
            if abs(angle1 - angle2) < 4 or abs(dist1 - dist2) < 2:
                ang = np.round(angle1)
                exist, key = check_if_key_in_dict(ang, all_angles)
                if not exist:
                    all_angles[ang] = {}
                    all_angles[ang]['freq'] = 2
                    all_angles[ang]['dist'] = [dist1, dist2]
                    all_angles[ang]['angle'] = [angle1, angle2]
                else:
                    all_angles[key]['freq'] += 2
                    all_angles[key]['dist'].append(dist1)
                    all_angles[key]['dist'].append(dist2)
                    all_angles[key]['angle'].append(angle1)
                    all_angles[key]['angle'].append(angle2)
            else:
                ang1 = np.round(angle1)
                ang2 = np.round(angle2)
                exist1, key1 = check_if_key_in_dict(ang1, all_angles)
                exist2, key2 = check_if_key_in_dict(ang2, all_angles)
                if not exist1:
                    all_angles[ang1] = {}
                    all_angles[ang1]['freq'] = 1
                    all_angles[ang1]['dist'] = [dist1]
                    all_angles[ang1]['angle'] = [angle1]
                if exist1:
                    all_angles[key1]['freq'] += 1
                    all_angles[key1]['dist'].append(dist1)
                    all_angles[key1]['angle'].append(angle1)
                if not exist2:
                    all_angles[ang2] = {}
                    all_angles[ang2]['freq'] = 1
                    all_angles[ang2]['dist'] = [dist2]
                    all_angles[ang2]['angle'] = [angle2]
                if exist2:
                    all_angles[key2]['freq'] += 1
                    all_angles[key2]['dist'].append(dist2)
                    all_angles[key2]['angle'].append(angle2)
        else:
            # print(angle)
            angle, dist = calc_angle_dist(k, v)
            ang = np.round(angle)
            exist, key = check_if_key_in_dict(ang, all_angles)
            if not exist:
                all_angles[ang] = {}
                all_angles[ang]['freq'] = 1
                all_angles[ang]['dist'] = [dist]
                all_angles[ang]['angle'] = [angle]
            else:
                all_angles[key]['freq'] += 1
                all_angles[key]['dist'].append(dist)
                all_angles[key]['angle'].append(angle)
    return all_angles


def calc_angle_spacing(img):
    pat_s, pat_p, square, ratio = output_pattern(img)
    dist = distance.cdist(pat_p, pat_p, 'euclidean')
    pat_p = np.array(pat_p)
    close_pt = closest_pt(dist, pat_p)
    angles = get_all_angles_dict(close_pt)
    max_freq = 0
    orientation = 0
    spacing = 0
    # print(angles)
    for k, v in angles.items():
        freq = v['freq']
        if freq > max_freq:
            max_freq = freq
            print(freq)
            spacing = np.mean(v['dist'])
            orientation = np.mean(v['angle'])
    return orientation, spacing, square, ratio
