import shutil
from pyagender import PyAgender
from PIL import Image
import os
import numpy as np
from tqdm import tqdm

dataset_names = ['30대2_raw']
postfix = '_F'
op_resize = False

idx = 0
for dataset_name in dataset_names:
    root_data_dir = r"D:\Datasets\Korean"
    image_root_dir = os.path.join(root_data_dir, dataset_name)
    # define store path
    store_root_dir = r"D:\Datasets\Korean"
    store_image_dir = os.path.join(store_root_dir, dataset_name + postfix)
    if os.path.exists(store_image_dir) is False:
        os.makedirs(store_image_dir)
    if os.path.exists(os.path.join(root_data_dir,dataset_name +  '_F')) is False:
        os.makedirs(os.path.join(root_data_dir,dataset_name +  '_F'))
    if os.path.exists(os.path.join(root_data_dir,dataset_name +  '_E')) is False:
        os.makedirs(os.path.join(root_data_dir, dataset_name + '_E'))
    for filename in tqdm(os.listdir(image_root_dir)):
        filepath = os.path.join(image_root_dir, filename)
        if os.path.isdir(filepath):
            continue
        width=-1; height=-1
        with Image.open(filepath) as img:
            width, height = img.size

            

            agender = PyAgender()
            # see available options in __init__() src

            faces = agender.detect_genders_ages(cv2.imread(MY_IMAGE))

        
        # print(width, ", ", height)
        # if width <= 128 or height <= 128: #F
        #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_F'), filename))
        # elif width <= 256 or height <= 256: #E
        #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_E'), filename))
