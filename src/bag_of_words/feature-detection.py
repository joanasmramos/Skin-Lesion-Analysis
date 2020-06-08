import sys
import csv
import random
import argparse
from shared import *
from sklearn.metrics import confusion_matrix, f1_score, recall_score, precision_score
sys.path.append('..')


parser = argparse.ArgumentParser(description='VCOM - Bag of Words Tumor classification')
parser.add_argument('-desc', action='store_true', help='Compute image descriptors')
parser.add_argument('-bow', action='store_true', help='Compute Bag of Words')
parser.add_argument('-train', action='store_true', help='Train classifier')
parser.add_argument('-test', action='store_true', help='Test classifier')
parser.add_argument('-testone', action='store_true', help='Test classifier for one image independently')
args = parser.parse_args()
DESC = args.desc
BOW = args.bow
TRAIN = args.train
TEST = args.test
TESTONE = args.testone

#-----------------------------------------------------------------------------------------------------------
DESC = 'desc'
BOW = 'bow'
TRAIN = 'train'
TEST = 'test'
TESTONE = 'testone'

#-----------------------------------------------------------------------------------------------------------
IMG_PATH_TRAIN = 'images/train'
IMG_PATH_TEST = 'images/test'


ANNOT_PATH_TRAIN = 'annotations/train'
ANNOT_PATH_TEST = 'annotations/test'

DESC_PATH_TRAIN = 'descriptors_train.pkl'

BOW_PATH = 'bow.pkl'
SVM_TRAIN_PATH = 'model.pkl'
VARS_TRAIN_PATH = 'train.pkl'

db_train = Database(IMG_PATH_TRAIN, ANNOT_PATH_TRAIN)
db_test = Database(IMG_PATH_TEST, ANNOT_PATH_TEST)


labels_train = {
    'lower_bound': 0,
    'upper_bound': 11402, #11402
}

labels_test = {
    'lower_bound': 0,
    'upper_bound': 11392, #11392
}

keys = {
    'ISIC_0': 0,
    'ISIC_1': 1,
}

def main():
    global db_train
    global db_test

    with open("ISBI2016_ISIC_Part3_Training_GroundTruth.csv") as f:
        keys = {line.split(',')[0]: line.split(',')[1].partition("\n")[0] for line in f}

    with open("TEGT.csv") as f:
        keys.update({line.split(',')[0]: line.split(',')[1].partition("\n")[0] for line in f})

    descriptors_train = []
    features_train = []
    features_test = []
    if not DESC:
        try:
            print('Loading descriptors file from path: ', BOW_PATH)
            descriptors_train = load_object(DESC_PATH_TRAIN)
            print('Finished loading descriptors')
        except Exception:
            print('Unable to load descriptors file')
            quit()

    print('Starting computing descriptors')
    file_it = labels_train['lower_bound']
    i = 0
    while file_it < labels_train['upper_bound'] :
        try:
            label = 'ISIC_'
            name = label + str(file_it).zfill(7)
            img = db_train.read_img(name)
            img = gray(img)
            img = resize_img(img)
            feature = get_key_points(img)
            features_train.append((name, img, feature))
            if DESC:
                descriptors_train.extend(feature[1])
            print('Computing descriptors for ' + str(label) + str(file_it).zfill(7))
            i = i + 1
        except:
            continue
        finally: 
            file_it = file_it + 1

    file_it = labels_test['lower_bound']
    while file_it < labels_test['upper_bound'] :
        try:
            label = 'ISIC_'
            name = label + str(file_it).zfill(7)
            img = db_test.read_img(name)
            img = gray(img)
            img = resize_img(img)
            feature = get_key_points(img)
            i = i + 1
            features_test.append((name, img, feature))
            print('Computing descriptors for ' + str(label) + str(file_it).zfill(7))
        except:
            continue
        finally: 
            file_it = file_it + 1


    print('Finished computing descriptors')
    print('Storing descriptors')
    store_object(descriptors_train, DESC_PATH_TRAIN)
    print('Finished storing descriptors')
    
    descriptors_train = array_to_np(descriptors_train)
    dictionary = None

    if not BOW:
        try:
            print('Loading dictionary file from path: ', BOW_PATH)
            dictionary = load_object(BOW_PATH)
            print('Finished loading dictionary')
        except:
            print('Unable load dictionary file')
            quit()
    else:
        print('Computing bag of words')
        bow = bow_trainer(100)
        dictionary = bow_cluster(bow, descriptors_train)
        print('Finished computing bag of words')
        print('Storing bag of words')
        store_object(dictionary, BOW_PATH)
        print('Finished storing bag of words')

    print('Computing target variables')
    X_train = []
    y_train = []
    X_test = []
    y_test = []
    extractor = bow_extractor(dictionary)
    for name, img, feature in features_train:
        try:
            X_train.append(bow_extract(extractor, img, feature[0])[0])
            y_train.append(1 if keys[name] == 'malignant' or keys[name] == '0.0' else 0)
        except:
            print('aqui')

    for name, img, feature in features_test:
        try:
            X_test.append(bow_extract(extractor, img, feature[0])[0])
            y_test.append(1 if keys[name] == 'malignant' or keys[name] == '0.0' else 0)
        except:
            print('aqui')
    print('Finish computing target variables')

    svm = None
    if not TRAIN:
        try:
            print('Loading model file from path: ', SVM_TRAIN_PATH)
            svm = load_svm(SVM_TRAIN_PATH)
            print('Finished loading model')
        except:
            print('Cant load model file')
            quit()
    else:
        print('Training model')
        svm = create_svm()
        train_svm(svm, X_train, y_train)
        print('Finished training model')

        print('Saving model')
        store_object([X_train,y_train], VARS_TRAIN_PATH)
        store_svm(svm, SVM_TRAIN_PATH)
        print('Finished saving model')


    if TEST:
        print('Testing model')
        pred = np.squeeze(test_svm(svm, X_test)[1].astype(int))
        print('Finished testing model')

        cm = confusion_matrix(y_test,pred)
        print('Confusion Matrix: \n' + str(cm))
        correct = 0
        for i in range(len(y_test)):
            if y_test[i] == pred[i]:
                correct += 1

        accuracy = correct/len(y_test)*100
        precision = cm[0][0]/(cm[0][0] + cm[1][0])*100
        recall = cm[0][0]/(cm[0][0] + cm[0][1])*100
        f1 = 2 * precision * recall / (precision + recall)

        print('Accuracy : ', round(accuracy, 2), '%')
        print('Precision: ', round(precision, 2), '%')
        print('Recall   : ', round(recall, 2), '%')
        print('F1       : ', round(f1, 2))

if __name__ == "__main__":
    main()
