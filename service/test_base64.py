import base64

usrImg = '.\\source.jpg'
usrImg_result = open(usrImg, 'rb').read()
usrImg_64_decode = base64.urlsafe_b64encode(usrImg_result)

print(usrImg_64_decode)

usrImg = '.\\target.png'
usrImg_result = open(usrImg, 'rb').read()
usrImg_64_decode = base64.urlsafe_b64encode(usrImg_result)

print(usrImg_64_decode)