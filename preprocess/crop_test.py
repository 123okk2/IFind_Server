from mtcnn.mtcnn import MTCNN
from PIL import Image
import numpy as np
import cv2
import os
from tqdm import tqdm
from skimage import transform as trans
import json
import requests

webhook_url = "https://hooks.slack.com/services/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"
#define read path
dataset_names = ['20대', '30대', '40대', '50대']

for dataset_name in dataset_names:
    root_data_dir=r"D:\Datasets\Korean"
    image_root_dir=os.path.join(root_data_dir,dataset_name)
    #define store path
    store_root_dir=r"D:\Datasets\Korean"
    store_image_dir=os.path.join(store_root_dir,dataset_name + "_edit")
    if os.path.exists(store_image_dir) is False:
        os.makedirs(store_image_dir)

    cascadefile = "haarcascade_frontalface_default.xml"
    count = 0

    def imwrite(filename, img, params=None):
        try:
            ext = os.path.splitext(filename)[1]
            result, n = cv2.imencode(ext, img, params)
            if result:
                with open(filename, mode='w+b') as f:
                    n.tofile(f)
                    return True
            else:
                return False
        except Exception as e:
            print(e)
            return False

    for filename in tqdm(os.listdir(image_root_dir)):
        try:
            dst = []
            filepath=os.path.join(image_root_dir,filename)
            storepath=os.path.join(store_image_dir,filename)

            if os.path.exists(storepath):
                count+=1

                if count % 50000 is 0 or count is len(os.listdir(image_root_dir)) - 1:
                    content = "[202.*.*.150] " + str(count) + " is finished - Cropping Process " + dataset_name
                    payload = {"text": content}

                    requests.post(
                        webhook_url, data=json.dumps(payload),
                        headers={'Content-Type': 'application/json'}
                    )
                continue
            img = cv2.imdecode(np.fromfile(os.path.join(image_root_dir, filename), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cascade = cv2.CascadeClassifier(cascadefile)
            facelist = cascade.detectMultiScale(imgray, scaleFactor=1.03, minNeighbors=1)
            # print(facelist)
            # if len(facelist) >= 1:
            #     for i in facelist:
            #         crop_img = img[facelist[-1][1]:facelist[-1][1] + facelist[-1][3],
            #                    facelist[-1][0]:facelist[-1][0] + facelist[-1][2]]
            crop_img = img[facelist[0][1]:facelist[0][1] + facelist[0][3], facelist[0][0]:facelist[0][0] + facelist[0][2]]
            # crop_img = img[78:78+216,123:123+216]
            # cv2.rectangle(img, (123, 78), (123+216, 78+216), (255, 0, 0), 2)
            resize_img = cv2.resize(crop_img, (400, 400))
            # cv2.imshow("cropped",resize_img)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            # resize_img.tofile(os.path.join(store_image_dir, filename))
            a = os.path.join(store_image_dir, filename)
            imwrite(a, resize_img)
            # cv2.imwrite(a, resize_img)
            # Image.fromarray(resize_img.astype(np.uint8)).save(storepath)

            count += 1
            if count % 50000 is 0 or count is len(os.listdir(image_root_dir))-1:
                content = "[202.*.*.150] "+str(count) + " is finished - Cropping Process "+dataset_name
                payload = {"text": content}

                requests.post(
                    webhook_url, data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'}
                )
        except Exception as E:
            print(E)
