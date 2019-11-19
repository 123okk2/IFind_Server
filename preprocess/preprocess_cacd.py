import shutil

from keras.utils import get_file
from mtcnn.mtcnn import MTCNN
from PIL import Image
import numpy as np
import cv2
import os
from tqdm import tqdm
from skimage import transform as trans
import json
import requests
from pathlib import Path
from age_gender.wide_resnet import WideResNet

webhook_url = "https://hooks.slack.com/services/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"
pretrained_model = "https://github.com/yu4u/age-gender-estimation/releases/download/v0.5/weights.28-3.73.hdf5"
modhash = 'fbe63257a054c1c5466cfd7bf14646d6'

# weight_file = None
# if not weight_file:
#     weight_file = get_file("weights.28-3.73.hdf5", pretrained_model, cache_subdir="pretrained_models",
#                            file_hash=modhash, cache_dir=str(Path(__file__).resolve().parent))

img_size = 64;
depth = 16;
k = 8; #margin = 0.4
ok_domain = {'A':25, 'B':29, 'C':41, 'D':45, 'E':15, 'F':50}

def isbw(img):
    #img is a numpy.ndarray, loaded using cv2.imread
    if len(img.shape) > 2:
        looks_like_rgbbw = not False in ((img[:,:,0:1] == img[:,:,1:2]) == (img[:,:,1:2] ==  img[:,:,2:3]))
        looks_like_hsvbw = not (True in (img[:,:,0:1] > 0) or True in (img[:,:,1:2] > 0))
        return looks_like_rgbbw or looks_like_hsvbw
    else:
        return True

def write_log(msg, file='error_image.txt'):
    f = open(file, 'a', encoding='UTF8')
    f.write(msg + '\n')
    f.close()

def real_log(msg):
    f = open("real_log.txt", 'a', encoding='UTF8')
    f.write(msg + '\n')
    f.close()

def write_special_log(msg):
    f = open("special_image.txt", 'a', encoding='UTF8')
    f.write(msg + '\n')
    f.close()

def getMTCNN_result(npimage):
    # define some param for mtcnn
    src = np.array([
        [30.2946, 51.6963],
        [65.5318, 51.5014],
        [48.0252, 71.7366],
        [33.5493, 92.3655],
        [62.7299, 92.2041]], dtype=np.float32)
    threshold = [0.6, 0.7, 0.9]
    factor = 0.85
    minSize = 20
    imgSize = [120, 100]
    detector = MTCNN(steps_threshold=threshold, scale_factor=factor, min_face_size=minSize)

    # align,crop and resize
    keypoint_list = ['left_eye', 'right_eye', 'nose', 'mouth_left', 'mouth_right']
    count = 0

    dst = []


    # Image.fromarray(npimage.astype(np.uint8)).show()
    dictface_list = None
    try:
        dictface_list = detector.detect_faces(
            npimage)  # if more than one face is detected, [0] means choose the first face
    except ValueError:
        # real_log("Value Error : " + filename)
        # write_log(filename)
        return None

    if len(dictface_list) > 1:
        boxs = []
        for dictface in dictface_list:
            boxs.append(dictface['box'])

        center = np.array(npimage.shape[:2]) / 2
        boxs = np.array(boxs)
        face_center_y = boxs[:, 0] + boxs[:, 2] / 2
        face_center_x = boxs[:, 1] + boxs[:, 3] / 2
        face_center = np.column_stack((np.array(face_center_x), np.array(face_center_y)))
        distance = np.sqrt(np.sum(np.square(face_center - center), axis=1))
        min_id = np.argmin(distance)
        dictface = dictface_list[min_id]
    else:
        if len(dictface_list) == 0:
            return None
        else:
            dictface = dictface_list[0]
    face_keypoint = dictface['keypoints']
    # for keypoint in keypoint_list:
    #     dst.append(face_keypoint[keypoint])



    va = dictface['box'][2]
    if dictface['box'][3] > dictface['box'][2]:
        va = dictface['box'][3]
    crop_img = npimage[dictface['box'][1]:dictface['box'][1] + va, dictface['box'][0]:dictface['box'][0] + va]
    if crop_img is None or len(crop_img) is 0:
        crop_img = npimage[dictface['box'][1]:dictface['box'][1] + dictface['box'][3],
                   dictface['box'][0]:dictface['box'][0] + dictface['box'][2]]
        if crop_img is None or len(crop_img) is 0:
            crop_img = npimage
        # write_special_log(filename)

    try:
        crop_img = cv2.resize(crop_img, (400, 400))
    except Exception as ex:
        print(ex)
    return Image.fromarray(crop_img.astype(np.uint8))

def predictAgeAndGender(model, npimage, dictface, margin=0.4):
    '''
                            Age Predict
                        '''
    # input_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_h, img_w, _ = np.shape(npimage)

    faces = np.empty((1, img_size, img_size, 3))

    x1, y1, x2, y2, w, h = dictface['box'][0], dictface['box'][1], dictface['box'][0] + dictface['box'][2] + 1, \
                           dictface['box'][1] + dictface['box'][3] + 1, dictface['box'][2], dictface['box'][3]
    xw1 = max(int(x1 - margin * w), 0)
    yw1 = max(int(y1 - margin * h), 0)
    xw2 = min(int(x2 + margin * w), img_w - 1)
    yw2 = min(int(y2 + margin * h), img_h - 1)
    # cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
    # Image.fromarray(cv2.resize(npimage[yw1:yw2 + 1, xw1:xw2 + 1, :], (img_size, img_size)).astype(np.uint8)).show()
    # cv2.rectangle(img, (xw1, yw1), (xw2, yw2), (255, 0, 0), 2)
    faces[0, :, :, :] = cv2.resize(npimage[yw1:yw2 + 1, xw1:xw2 + 1, :], (img_size, img_size))

    # predict ages and genders of the detected faces
    results = model.predict(faces)
    predicted_genders = results[0]
    ages = np.arange(0, 101).reshape(101, 1)
    predicted_ages = results[1].dot(ages).flatten()

    return predicted_ages, predicted_genders

if __name__ == '__main__':
    dataset_names = ['10대2', '10대3']
    postfix = '_raw'
    op_resize = True

    idx = 0
    for dataset_name in dataset_names:
        root_data_dir=r"D:\Datasets\Korean"
        image_root_dir=os.path.join(root_data_dir,dataset_name)
        #define store path
        store_root_dir=r"D:\Datasets\Korean"
        store_image_dir=os.path.join(store_root_dir,dataset_name + postfix)
        if os.path.exists(store_image_dir) is False:
            os.makedirs(store_image_dir)
        if os.path.exists(os.path.join(root_data_dir, dataset_name + '_F')) is False:
            os.makedirs(os.path.join(root_data_dir, dataset_name + '_F'))
        if os.path.exists(os.path.join(root_data_dir, dataset_name + '_E')) is False:
            os.makedirs(os.path.join(root_data_dir, dataset_name + '_E'))

        #define some param for mtcnn
        src = np.array([
         [30.2946, 51.6963],
         [65.5318, 51.5014],
         [48.0252, 71.7366],
         [33.5493, 92.3655],
         [62.7299, 92.2041] ], dtype=np.float32 )
        threshold = [0.6,0.7,0.9]
        factor = 0.85
        minSize=20
        imgSize=[120, 100]
        detector=MTCNN(steps_threshold=threshold,scale_factor=factor,min_face_size=minSize)

        #align,crop and resize
        keypoint_list=['left_eye','right_eye','nose','mouth_left','mouth_right']
        count = 0

        # model = WideResNet(img_size, depth=depth, k=k)()
        # model.load_weights(weight_file)

        for filename in tqdm(os.listdir(image_root_dir)):
            try:
                dst = []
                filepath=os.path.join(image_root_dir,filename)
                storepath=os.path.join(store_image_dir, filename)


                width = -1;
                height = -1
                with Image.open(filepath) as img:
                    width, height = img.size

                # print(width, ", ", height)
                # if width <= 128 or height <= 128:  # F
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_F'), filename))
                #     continue
                # elif width <= 256 or height <= 256:  # E
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_E'), filename))
                #     continue

                if os.path.exists(storepath):
                    count+=1

                    if count % 5000 is 0 or count is len(os.listdir(image_root_dir)) - 1:
                        content = "[202.*.*.150] " + str(count) + " is finished - Cropping Process " + dataset_name
                        payload = {"text": content}

                        requests.post(
                            webhook_url, data=json.dumps(payload),
                            headers={'Content-Type': 'application/json'}
                        )
                    continue

                npimage = None
                try:
                    npimage=np.array(Image.open(filepath))
                except Exception as ex:
                    real_log("Exception - "+filename+ " "+ str(ex))
                    write_log(filename)
                    continue

                # Image.fromarray(npimage.astype(np.uint8)).show()
                dictface_list=None
                try:
                    dictface_list=detector.detect_faces(npimage)#if more than one face is detected, [0] means choose the first face
                except ValueError:
                    real_log("Value Error : " + filename)
                    write_log(filename)
                    continue

                if len(dictface_list)>1:
                    boxs=[]
                    for dictface in dictface_list:
                        boxs.append(dictface['box'])

                    center=np.array(npimage.shape[:2])/2
                    boxs=np.array(boxs)
                    face_center_y=boxs[:,0]+boxs[:,2]/2
                    face_center_x=boxs[:,1]+boxs[:,3]/2
                    face_center=np.column_stack((np.array(face_center_x),np.array(face_center_y)))
                    distance=np.sqrt(np.sum(np.square(face_center - center),axis=1))
                    min_id=np.argmin(distance)
                    dictface=dictface_list[min_id]
                else:
                    if len(dictface_list)==0:
                        continue
                    else:
                        dictface=dictface_list[0]
                face_keypoint = dictface['keypoints']
                # for keypoint in keypoint_list:
                #     dst.append(face_keypoint[keypoint])
                # predicted_ages, predicted_genders = predictAgeAndGender(model, npimage, dictface)

                # age = int(predicted_ages[0])
                # if ok_domain['B'] <= age <= ok_domain['C']:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_BC'), filename))
                # elif ok_domain['A'] <= age < ok_domain['B']:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_AB'), filename))
                # elif ok_domain['C'] < age <= ok_domain['D']:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_CD'), filename))
                # elif ok_domain['E'] >= age:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_E'), filename))
                # elif ok_domain['F'] <= age:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_F'), filename))
                # else:
                #     shutil.move(filepath, os.path.join(os.path.join(root_data_dir, dataset_name + '_0'), filename))
                # label = "{}, {}, {}".format(filename, int(predicted_ages[0]),
                #                                 "M" if predicted_genders[0][0] < 0.5 else "F")
                # write_log(label, "age_log.txt")
                        # draw_label(img, (d.left(), d.top()), label)

                va = dictface['box'][2]
                if dictface['box'][3] > dictface['box'][2]:
                    va = dictface['box'][3]
                crop_img = npimage[dictface['box'][1]:dictface['box'][1]+va, dictface['box'][0]:dictface['box'][0]+va]
                if crop_img is None or len(crop_img) is 0:
                    crop_img = npimage[dictface['box'][1]:dictface['box'][1] + dictface['box'][3], dictface['box'][0]:dictface['box'][0] + dictface['box'][2]]
                    if crop_img is None or len(crop_img) is 0:
                        crop_img = npimage
                    write_special_log(filename)

                # dst = np.array(dst).astype(np.float32)
                # tform = trans.SimilarityTransform()
                # tform.estimate(dst, src)
                # M = tform.params[0:2, :]
                # warped = cv2.warpAffine(npimage, M, (imgSize[1], imgSize[0]), borderValue=0.0)
                # warped=cv2.resize(warped,(400,400))
                if isbw(crop_img):
                    real_log("Grayscale : " + filename)
                    write_log(filename)
                    continue

                if op_resize:
                    crop_img=cv2.resize(crop_img,(400,400))
                Image.fromarray(crop_img.astype(np.uint8)).save(storepath)

                count += 1
                if count % 5000 is 0 or count is len(os.listdir(image_root_dir))-1:
                    content = "[202.*.*.150] "+str(count) + " is finished - Cropping Process "+dataset_name
                    payload = {"text": content}

                    requests.post(
                        webhook_url, data=json.dumps(payload),
                        headers={'Content-Type': 'application/json'}
                    )

                npimage = None; crop_img = None
            except Exception as ex:
                real_log("Big Exception - "+ filename+ " "+ str(ex))
                write_log(filename)
        idx += 1