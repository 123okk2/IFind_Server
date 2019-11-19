import json

import requests
import torch
import torchvision
import torch.utils.data as data
import os
from os.path import join
import argparse
import logging
from tqdm import tqdm
#user import
from data_generator.DataLoader_Pretrain_Alexnet import CACD
from model.faceAlexnet import AgeClassify
from utils.io import check_dir,Img_to_zero_center
webhook_url = "https://hooks.slack.com/services/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"

#step1: define argument
parser = argparse.ArgumentParser(description='pretrain age classifier')
# Optimizer
# parser.add_argument('--learning_rate', '--lr', type=float, help='learning rate', default=1e-4)
parser.add_argument('--learning_rate', '--lr', type=float, help='learning rate', default=1e-3)
parser.add_argument('--batch_size', '--bs', type=int, help='batch size', default=128)
parser.add_argument('--max_epoches', type=int, help='Number of epoches to run', default=110)
parser.add_argument('--val_interval', type=int, help='Number of steps to validate', default=20000)
parser.add_argument('--save_interval', type=int, help='Number of batches to save model', default=150000)

# Model
# Data and IO
parser.add_argument('--cuda_device', type=str, help='which device to use', default='0')
parser.add_argument('--checkpoint_epoch', type=int, help='checkpoint epoch (where do you want to start)', default=0)
parser.add_argument('--checkpoint', type=str, help='logs and checkpoints directory', default='./checkpoint/pretrain_alexnet')
parser.add_argument('--saved_model_folder', type=str,
                    help='the path of folder which stores the parameters file',
                    default='./checkpoint/pretrain_alexnet/saved_parameters/')
parser.add_argument('--log_overwrite', type=int, help='do you want to overwrite your previous log?', default=1)
args = parser.parse_args()
os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda_device

args.checkpoint_model = args.saved_model_folder + 'epoch_'+str(args.checkpoint_epoch)+'_iter_0.pth'
start_epoch = args.checkpoint_epoch + 1
check_dir(args.checkpoint)
check_dir(args.saved_model_folder)



#step2: define logging output
logger = logging.getLogger("Age classifer")
file_handler = logging.FileHandler(join(args.checkpoint, 'log.txt'), "w" if args.log_overwrite > 0 else "a")
stdout_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.setLevel(logging.INFO)


def main():
    logger.info("Start to train:\n arguments: %s" % str(args))
    #step3: define transform
    transforms = torchvision.transforms.Compose([
        torchvision.transforms.Resize((227, 227)),
        torchvision.transforms.ToTensor(),
        Img_to_zero_center()
    ])
    #step4: define train/test dataloader
    train_dataset = CACD("train", transforms, None)
    test_dataset = CACD("test", transforms, None)
    train_loader = torch.utils.data.DataLoader(
        dataset=train_dataset,
        batch_size=args.batch_size,
        shuffle=True
    )
    test_loader = torch.utils.data.DataLoader(
        dataset=test_dataset,
        batch_size=args.batch_size,
        shuffle=True
    )
    #step5: define model,optim
    model=AgeClassify(True, args.checkpoint_model)
    optim=model.optim

    #step5-2: load checkpoints
    # model.load_state_dict(torch.load(args.checkpoint))


    for epoch in range(start_epoch, args.max_epoches):
        average_t_loss = 0; count = 0
        for train_idx, (img,label) in enumerate(train_loader):
            img=img.cuda()
            label=label.cuda()

            #train
            optim.zero_grad()
            model.train(img,label)
            loss=model.loss
            loss.backward()
            optim.step()
            format_str = ('epoch %d, step %d/%d, cls_loss = %.3f')
            logger.info(format_str % (epoch, train_idx, len(train_loader), loss))
            average_t_loss += loss


            # save the parameters at the end of each save interval
            if train_idx*args.batch_size % args.save_interval == 0:
                model.save_model(dir=args.saved_model_folder,
                                 filename='epoch_%d_iter_%d.pth'%(epoch, train_idx))
                logger.info('checkpoint has been created!')

            #val step
            count += 1
            # if train_idx % args.val_interval == 0:
            if (train_idx+1) % 1149 == 0:
                average_t_loss = average_t_loss / count

                train_correct=0
                train_total=0
                with torch.no_grad():
                    for val_img,val_label in tqdm(test_loader):
                        val_img=val_img.cuda()
                        val_label=val_label.long().cuda()
                        output=model.val(val_img)
                        train_correct += (output == val_label).sum()
                        train_total += val_img.size()[0]

                logger.info('validate has been finished!')
                format_str = ('val_acc = %.3f, train_loss = %.3f')
                logger.info(format_str % ((train_correct.cpu().numpy()/train_total), average_t_loss))

                content = "[202.*.*.150 IPCGANs-Pytorch] epoch " + str(epoch) + ", "+format_str % ((train_correct.cpu().numpy()/train_total, average_t_loss))
                payload = {"text": content}

                requests.post(
                    webhook_url, data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'}
                )



if __name__ == '__main__':
    main()
