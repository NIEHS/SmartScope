import cv2
import numpy as np
from numpy.typing import ArrayLike
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from Smartscope.lib.Datatypes.models import generate_unique_id
from .mask_box import MaskBox
from .record_params import RecordParams

logger = logging.getLogger(__name__)



class MultiShot(BaseModel):
    n_shots:int
    shots: List
    in_hole: float
    coverage: float
    display: Optional[str] = None
    params: Optional[RecordParams] = None
    cache_id:str = Field(default_factory=generate_unique_id)

    class Config:
        arbitrary_types_allowed =True

    @property
    def in_hole_percent(self):
        return round(self.in_hole * 100,1)
    
    @property
    def coverage_percent(self):
        return round(self.coverage * 100,1)
    
    def convert_shots_to_pixel(self, pixel_size_in_um:float) -> ArrayLike:
        return np.int16(np.array(self.shots) / pixel_size_in_um)
    
    def set_display(self,record_params: RecordParams):
        stream = display_multishot_matplotlib(self.shots,record_params.hole_size,record_params.beam_size_um,record_params.detector_size_um)
        self.display=base64.b64encode(stream.getvalue()).decode()
        self.params = record_params


    
def display_multishot_matplotlib(shots, hole_size,beam_size_um,detector_size_um):
    fig, ax = plt.subplots( nrows=1, ncols=1 )  # create figure & 1 axis
    hole = Circle([0,0],hole_size/2,fill=False, edgecolor='black',label='Hole')
    ax.add_patch(hole)
    limit = hole_size * 1.5 / 2
    ax.set_xlim([-limit,limit])
    ax.set_ylim([-limit,limit])
    ax.set_aspect('equal')
    for shot in shots:
        ax.add_patch(Circle(shot,beam_size_um/2,fill=False,color='red',label='Beam'))
        ax.add_patch(Rectangle(shot-(detector_size_um/2), *detector_size_um,  label='Field of view'))
    output = io.BytesIO()
    fig.savefig(output, bbox_inches='tight')
    return output

def make_beam_and_fov_masks(shots,beam_size,fov_size,box:MaskBox, beam_padding=1.1):
    radius = int(beam_size*beam_padding/2//box.pix_size)
    half_fov = np.int8(fov_size/box.pix_size//2)
    beam_masks=[]
    fov_masks=[]
    for s in shots:
        beam_mask = box.box()
        fov_mask = box.box()
        s = s/box.pix_size + box.center
        cv2.circle(beam_mask,s.astype(int),radius,1,cv2.FILLED)
        cv2.rectangle(fov_mask,np.int8(s-half_fov),np.int8(s+half_fov),1,cv2.FILLED)
        beam_masks.append(beam_mask)
        fov_masks.append(fov_mask)
    return beam_masks, fov_masks


def check_for_beam_fov_overlap(beam_masks,fov_masks,box):
    for i,f in enumerate(fov_masks):
        sum_box=box.box()
        sum_box+=f
        bm = beam_masks.copy()
        bm.pop(i)
        for j in bm:
            sum_box += j
        sum_box*=f
        if np.any(sum_box[sum_box>1]):
            # logger.info('Found beam overlap')
            return True

def check_fov_overlap(fov_masks,box):
    sum_box = box.box()
    for fov in fov_masks:
        sum_box += fov
    if np.any(sum_box[sum_box>1]):
        return True
        
def check_fraction_in_hole(fov_masks,box):
    sum_box = box.box()
    for fov in fov_masks:
        sum_box = sum_box + fov
    init_sum = sum_box.sum()
    if init_sum == 0:
        return 0, 0, 0
    masked_sum = sum_box * box.hole_mask
    sum_in_hole= masked_sum.sum()
    return sum_in_hole/init_sum, sum_in_hole, init_sum


def set_shots_per_hole(
        number_of_shots:int,
        hole_size:float,
        beam_size:float,
        image_size:np.ndarray,
        radius_step:int=0.02,
        starting_angle:float=0,
        consider_aspect=True,
        min_efficiency=0.85
    ):
    hole_area = np.pi*(hole_size/2)**2
    min_allowed_coverage = np.prod(image_size)/hole_area
    angle_between_shots = 2*np.pi / number_of_shots
    aspect= 1
    aspect_step = 1
    steps=1
    if consider_aspect:
        aspect = image_size[0]/image_size[1] 
        aspect_step = 0.1
        steps=20

    # start_radius = (hole_size/2 - np.sqrt(np.sum(image_size**2))/2)
    #  if number_of_shots != 1 else 0
    start_radius = beam_size/2000 if number_of_shots != 1 else 0
    max_radius = hole_size/2
    box = MaskBox(hole_size=hole_size)
    best_shots = None
    best_fraction_in_hole = 0
    best_hole_coverage = 0
    best_aspect_val = 0
    
    while True:
        for extra_rotation in range(int(np.degrees(angle_between_shots/2))):
            center_shot = False
            hole_coverage=1
            in_hole=1
            radius=start_radius
            running=True
            while running:
                for i in range(steps):
                    aspect_val = 1+i*aspect_step
                    shots = []
                    remaining_number_of_shots = number_of_shots
                    new_angle_between_shots = angle_between_shots
                    if radius >= beam_size/2+np.max(image_size)/2:
                        shots.append(np.array([0,0]))
                        remaining_number_of_shots -= 1
                        new_angle_between_shots = 2*np.pi / remaining_number_of_shots
                        center_shot=True
                    for j in range(remaining_number_of_shots):
                        angle = j*new_angle_between_shots + np.radians(extra_rotation+starting_angle)
                        shots.append(np.array([np.cos(angle),np.sin(angle)/(aspect_val)])*radius)
                    beam_masks, fov_masks = make_beam_and_fov_masks(shots,beam_size,image_size,box)
                    if check_fov_overlap(fov_masks,box) or check_for_beam_fov_overlap(beam_masks,fov_masks,box):
                        continue
                    in_hole, init_in_hole, sum_in_hole = check_fraction_in_hole(fov_masks,box)
                    hole_coverage = (np.prod(image_size)*in_hole*number_of_shots)/hole_area
                    # print(f'Coverage: {hole_coverage:.2f}; Radius: {radius:.2f}; In Hole: {in_hole:.2f}; Init in Hole: {init_in_hole}; Sum in Hole: {sum_in_hole} ;Center hole: {center_shot};', end='\r')
                    if hole_coverage<=min_allowed_coverage and running:
                        # print('Stoppign iteration')
                        running=False
                    if in_hole > best_fraction_in_hole and in_hole > min_efficiency and hole_coverage > best_hole_coverage:
                        best_fraction_in_hole = in_hole
                        best_hole_coverage = hole_coverage
                        best_shots = shots.copy()
                        best_aspect_val=aspect_val
                        # print(f'New Best Shot! Shots: {number_of_shots}; Rotation: {extra_rotation}; Radius: {radius}; Efficiency: {best_fraction_in_hole*100:.1f} %; Hole coverage: {best_hole_coverage} %; In Hole: {in_hole:.2f}; Init in Hole: {init_in_hole}; Sum in Hole: {sum_in_hole} ;Center hole: {center_shot}; Aspect val: {best_aspect_val}')
                    # time.sleep(0.2)
                if radius >= max_radius:
                    break
                radius += radius_step
                # print('Breaking out of loop', end='\r')
                
        if best_shots is not None:
            logger.info(f'Shots: {number_of_shots}; Efficiency: {best_fraction_in_hole*100:.1f} %; Hole coverage: {best_hole_coverage*100:.1f} %; Aspect val: {best_aspect_val}')
            return MultiShot(n_shots=number_of_shots,
                        shots=[s.tolist() for s in best_shots],
                        in_hole= best_fraction_in_hole,
                        coverage= best_hole_coverage,
                        )
        else:
            logger.info(f'Shots: {number_of_shots}; No pattern statisfying the {min_efficiency*100:.1f} % minimum effeciency found')
            return


