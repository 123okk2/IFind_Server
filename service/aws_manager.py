import base64

import boto3
from botocore.exceptions import ClientError
from os import environ
import logging


# AWS Manager : AWS 관련 전반의 기능을 하는 객체.
#    Singleton Class이며 S3 Manager와 Rekognition Manager를 멤버변수로 사용.
class AWSManager:
    __instance = None

    @staticmethod
    def getInstance():
        if AWSManager.__instance == None:
            AWSManager()
        return AWSManager.__instance

    def __init__(self):
        if AWSManager.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            AWSManager.__instance = self
            self.s3m = S3Manager(boto3.client('s3'))
            self.rekom = RekognitionManager(boto3.client('rekognition'))
            self.isConnected = False

    def connect(self, bucket, collection):
        self.s3m.setBucket(bucket)
        self.rekom.setCollection(collection)
        self.isConnected = True
        print("S3 and Rekognition are connected")

    def disconnect(self):
        self.s3m.setBucket(None)
        self.rekom.setCollection(None)
        self.isConnected = False
        print("S3 and Rekognition are disconnected")

    def searchFaces(self, files):
        if self.isConnected:
            if not isinstance(files, list):
                files = [files]
            resultArray = []
            for file in files:
                s3file = "_search_" + file.split('\\')[-1]
                self.s3m.upload(file, s3file)
                results = self.rekom.searchFace(self.s3m.getBucket(), s3file)
                resultArray.append(results)
                if not self.s3m.delete(s3file):
                    return False, resultArray
            return True, resultArray
        return False, None

    def registerFaces(self, files):
        if self.isConnected:
            if not isinstance(files, list):
                files = [files]
            for file in files:
                s3file = file.split('\\')[-1]
                self.s3m.upload(file, s3file)
                indexed = self.rekom.addFace(s3file, self.s3m.getBucket(), s3file)
                print("Register Success")

    # 아직 사용불가
    def deleteFaces(self, ids, files):
        if self.isConnected:
            if not isinstance(files, list):
                files = [files]
            if not isinstance(ids, list):
                ids = [ids]
            if len(files) != len(ids):
                return False

            # 1. Reko에서 FaceId 삭제
            dfaces, dfcount = rekom.deleteFaces(ids)
            # for file in files:
                # 2. S3에서 Object 삭제
                # if not self.s3m.delete(file):
                #     pass
            print("delete face : ", dfcount, " | id : ", dfaces)
            return True
        return False

    # 아직 미구현
    def getFacesAsBinary(self, s3file):
        if self.isConnected:
            self.s3m.download(s3file, 'download\\'+s3file)
            with open('download\\'+s3file, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string

    # Test 용
    def getS3M(self):
        return self.s3m
    def getRekoM(self):
        return self.rekom

    def compareFaces(self, sourceFile, targetFile):
        client = boto3.client('rekognition')

        imageSource = open(sourceFile, 'rb')
        imageTarget = open(targetFile, 'rb')

        response = client.compare_faces(SimilarityThreshold=70,
                                        SourceImage={'Bytes': imageSource.read()},
                                        TargetImage={'Bytes': imageTarget.read()})

        for faceMatch in response['FaceMatches']:
            position = faceMatch['Face']['BoundingBox']
            confidence = str(faceMatch['Face']['Confidence'])
            # similarity = str(faceMatch['Face']['Similarity'])
            print('The face at ' +
                  str(position['Left']) + ' ' +
                  str(position['Top']) +
                  ' matches with ' + confidence + '% confidence')

        imageSource.close()
        imageTarget.close()

        return response['FaceMatches']

    def checkConnected(self):
        return self.isConnected

    # S3 Manager : AWS S3 관련 전반의 기능을 하는 객체.
#    주 bucket을 설정하고 그 bucket에서 upload, download, delete 수행
class S3Manager:
    def __init__(self, client=None, bucket=None):
        self.client = client
        self.bucket = bucket

    def upload(self, file, s3file=None):
        if s3file is None:
            s3file = file
        self.client.upload_file(file, self.bucket, s3file)
        print("Uploading Complete - ", self.bucket, 'path=',s3file)

    def delete(self, s3file):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3file)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def download(self, s3file, file=None):
        if file == None:
            file = s3file
        self.client.download_file(self.bucket, s3file, file)
        print("Downloading Complete")

    # Getter & Setter
    def setBucket(self, bucket):
        self.bucket = bucket

    def getBucket(self):
        return self.bucket

    def isExist(self, s3file):
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3file)
        except ClientError:
            # Not found
            return False
        return True


# Rekognition Manager : AWS Rekognition 관련 전반의 기능을 하는 객체.
#    주 collection을 설정하고 그 collection에서 makeCollection, deleteCollection, addFace, deleteFaces,
#    searchFace, searchFaceById 수행
#         deleteFaces 는 api에서 한번에 여러개의 Face를 삭제해주기 때문에 이 객체도 그렇게 동작.
class RekognitionManager:
    def __init__(self, client=None, collection=None):
        self.client = client
        self.collection = collection

    def addFace(self, file, bucket, s3file=None):
        if s3file == None:
            s3file = file
        a = file.split('/')[-1]
        response = self.client.index_faces(CollectionId=self.collection,
                                      Image={'S3Object': {'Bucket': bucket, 'Name': s3file}},
                                      ExternalImageId=file.split('/')[-1],
                                      MaxFaces=1,
                                      QualityFilter="AUTO",
                                      DetectionAttributes=['ALL'])

        print('Results for ' + file)
        print('Faces indexed:')
        if len(response['FaceRecords']) > 0:
            for faceRecord in response['FaceRecords']:
                print('  Face ID: ' + faceRecord['Face']['FaceId'])
                print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

        print('Faces not indexed:')
        if len(response['UnindexedFaces']) > 0:
            for unindexedFace in response['UnindexedFaces']:
                print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
                print(' Reasons:')
                for reason in unindexedFace['Reasons']:
                    print('   ' + reason)
        # 둘다 없다면 사물이므로 등록 실패?

        return response['FaceRecords'], response['UnindexedFaces']

    def deleteFaces(self, ids):
        response = self.client.delete_faces(CollectionId=self.collection,
                                       FaceIds=ids)

        print(str(len(response['DeletedFaces'])) + ' faces deleted:')
        for faceId in response['DeletedFaces']:
            print(faceId)

        return response['DeletedFaces'], len(response['DeletedFaces'])

    def searchFace(self, bucket, s3file, threshold=70, maxFaces=15):

        response = self.client.search_faces_by_image(CollectionId=self.collection,
                                                Image={'S3Object': {'Bucket': bucket, 'Name': s3file}},
                                                FaceMatchThreshold=threshold,
                                                MaxFaces=maxFaces)

        faceMatches = response['FaceMatches']
        print('Matching faces')

        for match in faceMatches:
            print('FaceId:' + match['Face']['FaceId'])
            print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            print()

        return faceMatches

    def searchFaceById(self, id, threshold=50, maxFaces=2):
        response = self.client.search_faces(CollectionId=self.collection,
                                       FaceId=id,
                                       FaceMatchThreshold=threshold,
                                       MaxFaces=maxFaces)

        faceMatches = response['FaceMatches']
        print('Matching faces')

        for match in faceMatches:
            print('FaceId:' + match['Face']['FaceId'])
            print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            print()

        return faceMatches

    def getFaces(self, maxResults=10):
        tokens = True
        faceList = []
        response = self.client.list_faces(CollectionId=self.collection,
                                     MaxResults=maxResults)
        print('Faces in collection ' + self.collection)

        while tokens:
            faces = response['Faces']
            faceList = faceList + faces

            for face in faces:
                print(face)
            if 'NextToken' in response:
                nextToken = response['NextToken']
                response = self.client.list_faces(CollectionId=self.collection,
                                             NextToken=nextToken, MaxResults=maxResults)
            else:
                tokens = False

        return faceList

    def makeCollection(self, collection):
        print('Creating collection:' + collection)
        response = self.client.create_collection(CollectionId=collection)
        print('Collection ARN: ' + response['CollectionArn'])
        print('Status code: ' + str(response['StatusCode']))
        print('Done...')
        return response, response['CollectionArn'], str(response['StatusCode'])

    def getCollection(self):
        return self.collection

    def setCollection(self, collection):
        self.collection = collection

    def deleteCollection(self, collection=None):
        if collection == None:
            collection = self.collection
        print('Attempting to delete collection ' + collection)
        statusCode = ''
        try:
            response = self.client.deleteCollection(CollectionId=collection)
            statusCode = response['StatusCode']
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print('The collection ' + collection + ' was not found ')
            else:
                print('Error other than Not Found occurred: ' + e.response['Error']['Message'])
            statusCode = e.response['ResponseMetadata']['HTTPStatusCode']
        print('Operation returned Status Code: ' + str(statusCode))
        print('Done...')
        return False

    def getCollectionInfo(self, collection=None):
        if collection == None:
            collection = self.collection
        print('Attempting to describe collection ' + collection)

        try:
            response = self.client.describe_collection(CollectionId=collection)
            print("Collection Arn: " + response['CollectionARN'])
            print("Face Count: " + str(response['FaceCount']))
            print("Face Model Version: " + response['FaceModelVersion'])
            print("Timestamp: " + str(response['CreationTimestamp']))

            return response

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print('The collection ' + collection + ' was not found ')
            else:
                print('Error other than Not Found occurred: ' + e.response['Error']['Message'])
        print('Done...')

    def getCollectionList(self, maxResults=5):
        # Display all the collections
        print('Displaying collections...')
        response = self.client.list_collections(MaxResults=maxResults)
        results = []

        while True:
            collections = response['CollectionIds']
            results.append(collections)

            for collection in collections:
                print(collection)
            if 'NextToken' in response:
                nextToken = response['NextToken']
                response = self.client.list_collections(NextToken=nextToken, MaxResults=maxResults)

            else:
                break

        print('done...')
        return results


if __name__ == "__main__":
    am = AWSManager.getInstance()
    am.connect("ifind2", "IFCollection")
    s3m = am.getS3M()
    rekom = am.getRekoM()

    rekom.makeCollection("IFCollection")
    rekom.getCollectionInfo()
    # am.registerFaces('tkndata\\tkn_decode_0.jpg')
    # s3m.delete("tkn_decode_0.jpg")
    # response = rekom.getFaces()
    # am.searchFaces("tkndata\\tkn_decode_0.jpg")
    # result = am.deleteFaces("tkn_decode_0.jpg", "0c039c2e-55e5-4f1b-84d9-cf7ea84e3582")
    rekom.deleteFaces(['42c6b17d-893c-4a8f-b4ef-21adbd8887ff',
'0221af1c-26fa-47db-a2a9-72f0bebdd044',
'0817a0be-dd7c-4ca6-8918-bade349ca33e',
'55eb1859-6ffe-4bcc-a189-817d3221a6c1'])
    #'ExternalImageId' (2020683411696)
    response = rekom.getFaces()
    bucketName = "ifind2"
    collectionId = 'IFCollection'
    fileName = "source.jpg"
    s3fileName = "source1.jpg"
    #98675bfb-59df-4a95-a7a1-c2b5d68399d0


'''
References : 
    https://docs.aws.amazon.com/ko_kr/rekognition/latest/dg/describe-collection-procedure.html
'''