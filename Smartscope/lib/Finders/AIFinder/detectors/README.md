## SmartScopeAI
[SmartScope](https://github.com/NIEHS/SmartScope/) is the first framework to streamline, standardize, and automate specimen evaluation in cryo-electron microscopy. SmartScope employs deep-learning-based object detection to identify and classify features suitable for imaging, allowing it to perform thorough specimen screening in a fully automated manner. This repository contains the AI feature recognition engine for SmartScope. The atlas level square identification and classification is done using Detectron2 and the square level hole detection is done using YOLOv5. 

## Citation
Bouvette J., Huang Q., Riccio A. A., Copeland W. C., Bartesaghi A., Borgnia M. J. (2022). **Automated systematic evaluation of cryo- EM specimens with SmartScope.** eLife 2022;11:e80047, https://doi.org/10.7554/eLife.80047.

 ## Licensing
This work is licensed under the [BSD 3-Clause License](LICENSE).

## Python requirements
This code requires:
- Python 3.7
- Pytorch 1.8.0
- CUDA 10.1

## Installation
Please follow the following steps to install:

1. Create an python virtual environment using ```python3 -m venv env```, activate the environment using ```source your_vm_name/bin/activate```, and update setuptools using ```pip install --upgrade pip setuptools wheel```. 

2. Install required packages using the ```requirements.txt``` file provided:  ```pip install -r requirements.txt```

3. Install Detectron2: ```python -m pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu101/torch1.8/index.html```

Make sure you have CUDA/10.1 installed!

## Preparing datasets

### Training set format for atlas trainer
The atlas trainer allows two data formats: 1. coco format (a standard format for object detection tasks); 2. a more customized yaml format that includes the following information: grid_type, image name, shape x and y, and labeled coordinates (in absolute value). A sample yaml file can be found in the `examples` folder. 

```
- grid_type: Carbon
  image: OR15_1_atlas3fRtwRNGrGy9jDOkt2.mrc
  shape_x: 14200
  shape_y: 13680
  targets:
  - coordinates: [3380.0, 11312.0, 4426.0, 12358.0]
    label: square
  - coordinates: [-104.0, 3878.0, 718.0, 4700.0]
    label: cracked
  - coordinates: [11833.0, 10349.0, 12715.0, 11231.0]
    label: square
  - coordinates: [4317.0, 1029.0, 5035.0, 1747.0]
    label: square
  - coordinates: [1400.0, 1803.0, 2442.0, 2845.0]
    label: square
  - coordinates: [6059.0, 6417.0, 7181.0, 7539.0]
  ```
  
  ### Training set format for square trainer
  Currently, the atals trainer takes in yolo training data format.  More details can be seen [here](https://roboflow.com/formats/yolo-darknet-txt#:~:text=YOLO%20Darknet%20TXT%20Annotation%20Format&text=This%20format%20contains%20one%20text,IDs%20to%20human%20readable%20strings.) This site also offers you the option to convert coco format to yolo format.
  
  ## Custom Training for atlas 
  ### Data organization
  If using the coco format, first create a directory for all the `.mrc` or `.jpg/png` atlases (for example `atlases`). Then, create `train` and `val` (optional) folder. Within each folder, there should be one `_annotations.json` file and all the `.mrc` or `.jpg/png` atlas data. 
  
  If using the custom format, also create the same directory/subdirectories, the only difference is that instead of `_annotations.json` file, we have label information in the `metadata.yaml` file. 
  
  ### Square detector training
  Once we have the training files ready, the atlas detector can be retrained using `train_atlas.py`. A  sample training command is:
  ```
  python train_atlas.py --input_dir path_to_input --output_dir path_to_outputs
  ```
[--input_dir]: path to all input files

[--output_dir]: path to all output files

[--lr]: learning rate, default is 0.0001

[--max_iter]: the maximum number of iterations for training

[--is_coco]: whether the file is in coco format

[--label]: label file name, default is _annotations.coco.json, but you can change it based on the actual name

More details can be found using ```python train_atlas.py -h```.

### Hole detector training
The hole detector can be retrained using `train_hole_detector.py`. A sample training command is:

  ```
 python train_hole_detector.py --img 1280 --epochs 300 --batch 4 --data path_to_data_file --weights yolov5x.pt --project path_to_output
 ```
 [--img]: size to resize input images
 
 [--epochs]: total number of training epochs 
 
 [--batch]: batch size for training
 
 [--data]: path to yaml file that contains training data information
 
 [--weights]: pretrained weights initialization
 
 [--project]: path to all saved outputs
 
 This training script contains many optional arguments, for more information, use ```python train_hole_detector.py -h```.

 ## Data availability
- Pre-trained models for square and hole detection are available to download from [10.5281/zenodo.6842025](https://zenodo.org/record/6842025). 
- Atlas and square images (and corresponding labels) used for training are available from [10.5281/zenodo.6814642](https://zenodo.org/record/6814642) and [10.5281/zenodo.6814652](https://zenodo.org/record/6814652), respectively.
