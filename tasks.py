from celery import Celery
from sklearn.neural_network import MLPClassifier
import numpy as np
import pickle
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn import linear_model
import pandas as pd
import os



BROKER_URL = 'amqp://guest:guest@localhost:5672//'#Default RabbitMQ Broker
app = Celery('tasks', broker=BROKER_URL)


# train_function====================================
@app.task
def train_function(fileID):
    '''
    This function finds out the chosen model for training and its parameters by user.
    After training is done, this function saves it on disk and change the status in
    "status_manager.csv" to be used for prediction of test data

    Input(s):
    fileID: The unique random ID which is created after the file is uploaded

    Output(s):
     -
    '''
    df_status_manager = pd.read_csv('status_manager.csv',header=[0], #loads status_manager.csv
                                    index_col=[0]).fillna(value = '')
    parameters = eval(df_status_manager['parameters'].loc[fileID])# convert model parameters from string to dict
    model_name = parameters['model_name']
    trainX, trainY = load_dataset(fileID) #Loads uploaded dataset and seperates as input values(trainX) and labels(trainY)


    if model_name=='model1_NN':#If "1.Simple Neural Network" is chosen as classifier
        print('======',' Loading Parameters ','======')
        #Reading parameters that were entered by user
        solver = 'adam' if parameters['algorithm_name']=='' else parameters['algorithm_name']
        alpha = 1e-5 if parameters['alpha_val']=='' else np.float(parameters['alpha_val'])
        hidden_layer_sizes = (20,30,15, 5) if parameters['hidden_layers_val']=='' else tuple([int(x.strip()) for x in parameters['hidden_layers_val'].split(',')])
        print('======',' Defineing Classifier ','======')
        #Creates a Classifier
        clf = MLPClassifier(solver=solver, alpha=alpha,
                            hidden_layer_sizes=hidden_layer_sizes, random_state=1)
        print('======',' Training Classifier ','======')
        #Trains Classifier for trainX data with respect to trainY labels
        clf.fit(trainX, trainY)
        pickle_code = '%s_%s'%(fileID,model_name)
        print('======',' Saveing Model ','======')
        #Saves trained model using Pickle library
        with open(os.path.join('files','results',pickle_code), 'wb') as handle:
            pickle.dump(clf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        #Changing status of the file in status_manager.csv
        df_status_manager.at[fileID, 'pickle_address'] = pickle_code
        df_status_manager.at[fileID, 'status'] = 'Predict'
        df_status_manager.to_csv('status_manager.csv', index=[0], header=df_status_manager.columns) #save the new Process_list.csv
        print('======',' Done! ','======')

    elif model_name=='model2_SVM':#If "2.Support Vector Machine (SVM)" is chosen as classifier
        print('======',' Loading Parameters ','======')
        #Reading parameters that were entered by user
        C_val = 1.0 if parameters['c_val']=='' else float(parameters['c_val'])
        kernel_name = 'rbf' if parameters['kernel_name']=='' else parameters['kernel_name']
        gamma_val = 'scale' if parameters['gamma_val']=='' else parameters['gamma_val']
        print('======',' Defineing Classifier ','======')
        #Creates a Classifier
        clf = make_pipeline(StandardScaler(), SVC(C=C_val,kernel=kernel_name,
                                                  gamma=gamma_val))
        print('======',' Training Classifier ','======')
        #Trains Classifier for trainX data with respect to trainY labels
        clf.fit(trainX, trainY)
        pickle_code = '%s_%s'%(fileID,model_name)
        print('======',' Saveing Model ','======')
        #Changing status of the file in status_manager.csv
        with open(os.path.join('files','results',pickle_code), 'wb') as handle:
            pickle.dump(clf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        df_status_manager.at[fileID, 'pickle_address'] = pickle_code
        df_status_manager.at[fileID, 'status'] = 'Predict'
        df_status_manager.to_csv('status_manager.csv', index=[0], header=df_status_manager.columns) #save the new Process_list.csv
        print('======',' Done! ','======')

    elif model_name=='model3_LASSO':#If "3.Lasso (Linear Model)" is chosen as classifier
        print('======',' Loading Parameters ','======')
        #Reading parameters that were entered by user
        alpha_val = 0.1 if parameters['alpha_val']=='' else np.float(parameters['alpha_val'])
        print('======',' Defineing Classifier ','======')
        #Creates a Classifier
        clf = linear_model.Lasso(alpha=alpha_val)
        print('======',' Training Classifier ','======')
        #Trains Classifier for trainX data with respect to trainY labels
        clf.fit(trainX, trainY)
        pickle_code = '%s_%s'%(fileID,model_name)
        print('======',' Saveing Model ','======')
        #Changing status of the file in status_manager.csv
        with open(os.path.join('files','results',pickle_code), 'wb') as handle:
            pickle.dump(clf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        df_status_manager.at[fileID, 'pickle_address'] = pickle_code
        df_status_manager.at[fileID, 'status'] = 'Predict'
        df_status_manager.to_csv('status_manager.csv', index=[0], header=df_status_manager.columns) #save the new Process_list.csv
        print('======',' Done! ','======')
#end train_function=================================



# load_dataset====================================
def load_dataset(fileID):
    '''
    Loads uploaded dataset and for each row of data, selects the last column value
    as LABEL and other values as input data (as a Vector)

    Input(s):
    fileID: The unique random ID which is created after the file is uploaded

    Output(s):
    trainX : Input values(Vectors) that needs to be trained on
    trainY : Labels for each row of data in trainX
    '''
    df_dataset = pd.read_csv(os.path.join('files','uploads','%s'%(fileID)),header=[0])#load Dataset
    np_dataset = df_dataset.to_numpy()
    trainX = np_dataset[:,:-1]#keep all but last column
    trainY = np_dataset[:,-1]#keep the last column
    return np.asarray(trainX), np.asarray(trainY)
#end load_dataset=================================
