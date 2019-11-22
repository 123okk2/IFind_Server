import os

'''
단독실행 시에는 
36_이정재_00,36_이정재_01,36_이정재_02,36_이정재_03,36_이정재_04 0,1,2,3,4 0,0,0,0,0
'''

# import firebase_admin
# from firebase_admin import credentials
# from firebase_admin import firestore
# from preprocess.firebase_manager import FBManager
# import preprocess.if_executor as ie
# from preprocess.aws_manager import AWSManager as am

# from time import sleep
import numpy as np
from PIL import Image
# from datetime import datetime
# from tqdm import tqdm

from preprocess.preprocess_cacd import getMTCNN_result

import sys

a = sys.argv

print(a)

root_path = r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\posts'

target = []
for idx, i in enumerate(a[1].split(',')):
    target.append((i, a[2].split(',')[idx], a[3].split(',')[idx]))

mt_results = []
for idx, (key, category, type2) in enumerate(target):
    filename = os.path.join(root_path, key + ('_1' if type2 == '0' else '_2') + '.jpg')
    if os.path.isdir(filename):
        continue

    img = Image.open(filename)
    image = getMTCNN_result(np.array(img))
    if image:
        mt_results.append((idx, image, filename))


import torch
import torchvision
from model.IPCGANs import IPCGANs
from utils.io import Img_to_zero_center,Reverse_zero_center

class Demo:
    def __init__(self,generator_state_pth):
        self.model = IPCGANs()
        state_dict = torch.load(generator_state_pth)
        self.model.load_generator_state_dict(state_dict)

    def demo(self,image,target=0):
        img_size = 400
        assert target<5 and target>=0, "label shoule be less than 5"

        transforms = torchvision.transforms.Compose([
            torchvision.transforms.Resize((img_size,img_size)),
            torchvision.transforms.ToTensor(),
            Img_to_zero_center()
        ])
        label_transforms = torchvision.transforms.Compose([
            torchvision.transforms.ToTensor(),
        ])
        image=transforms(image).unsqueeze(0)
        full_one = np.ones((img_size, img_size), dtype=np.float32)
        full_zero = np.zeros((img_size, img_size, 5), dtype=np.float32)
        full_zero[:, :, target] = full_one
        label=label_transforms(full_zero).unsqueeze(0)

        img=image.cuda()
        lbl=label.cuda()
        self.model.cuda()

        res=self.model.test_generate(img,lbl)

        res=Reverse_zero_center()(res)
        res_img=res.squeeze(0).cpu().numpy().transpose(1,2,0)
        return Image.fromarray((res_img*255).astype(np.uint8))


# models = {'g_w_90':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight65_18_2\gepoch_2_iter_3000.pth'}
# models = {'g_w_90':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight65_18_1\gepoch_1_iter_6000.pth'}
models = {
    'w65_18_1_4':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_1_iter_4000.pth',
    'w65_18_1_6':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_1_iter_6000.pth',
    'w65_18_2_4':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_2_iter_4000.pth',
    'w65_18_3_5':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_5000.pth',
    'w65_18_3_6':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_6000.pth',
    'w65_18_3_7':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_7000.pth',
    'w65_18_3_9':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_9000.pth',
    'w65_18_3_95':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_9500.pth',
    'w65_18_3_10':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_10000.pth',
    'w65_18_3_105':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_10500.pth',
    'w65_18_3_11':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_11000.pth',
    'w65_18_3_115':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\w65_18\gepoch_3_iter_11500.pth',
    'w75_2_0_6':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight75_2_0\gepoch_0_iter_6000.pth',
    'g_w_90':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight65_18_1\gepoch_1_iter_6000.pth',
    'w65_18_b64_e10':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight65_18_b64_e10\depoch_7_iter_6000.pth'
}
# models = {'g_w_90':r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\pretrained_models\weight60_2_0\gepoch_0_iter_9000.pth'}

main_model = 'w65_18_3_9'
isCategoryModel = True

category_main_model = {
    0:('w65_18_3_7', False),
    1:('w65_18_3_115', True),
    2:('w65_18_3_5', False),
    3:('w65_18_b64_e10', False), #7 # 115
    4:('w65_18_b64_e10', False) #95 # 115
}
# with open('model_setting.json') as json_file:
#     json_data = json.load(json_file)
#
#     for k, v in json_data.items():
#         print(k, " : ", v)


if isCategoryModel:
    for idx, image, filename in mt_results:
        target_category = int(target[idx][1])
        target_model = models[category_main_model[target_category][0]]
        D = Demo(target_model)

        print("Demo Start! ==>", target_model)


        # t=  4
        # if target[idx][2] == '1':
        #     t = 2
        result = D.demo(image, target=target_category + (1 if category_main_model[target_category][1] else 0))
        result.save(os.path.join(root_path, target[idx][0] + ('_1' if target[idx][2] == '1' else '_2') + '.jpg'))

        print("Finish! ==> ", category_main_model[target_category][0])

else:
    target_model = models[main_model]
    D = Demo(target_model)

    for idx, image, filename in mt_results:
        target_category = int(target[idx][1])
        print("Demo Start! ==>", target_model)

        # t=  4
        # if target[idx][2] == '1':
        #     t = 2
        result = D.demo(image, target=target_category)
        result.save(os.path.join(root_path, target[idx][0] + ('_1' if target[idx][2] == '1' else '_2') + '.jpg'))

        print("Finish! ==> ", main_model)
