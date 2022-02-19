from flask import Flask, render_template, flash,  url_for, session, request,redirect
import pandas as pd
import datetime as dt
import time
import uuid
from werkzeug.utils import secure_filename
import os
from tasks import train_function
import pickle
import numpy as np


# Configurations **********************************************************
app = Flask(__name__)
app.config['SECRET_KEY'] = 'DontTellAnyOne'
status_manager_address = 'status_manager.csv' # A CSV file to store critial information such as file_id, trained model type, ...
UPLOAD_FOLDER = os.path.join('files','uploads') # location of the Upload Folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'csv'} # type of file to accept while uploading
# end Configurations *******************************************************




# Web Pages **********************************************************
#upload_csv page==========================
#Using upload_dataset, a new CSV dataset uploads in serever and its information stores in "status_manager.csv" file.
@app.route('/upload_dataset', methods=['GET', 'POST'])
def upload_dataset():
    #Using upload_dataset a new job adds to status_manager
    if request.method == 'POST':
        # checks if the post request has the file part
        if 'file' not in request.files:
            flash('No file part','danger') # show a warning MSG
            return redirect(url_for('home')) # Go to Homepage
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file','danger') # show a warning MSG
            return redirect(url_for('home')) # Go to Homepage
        if file and allowed_file(file.filename):
            #If every thing is OK with file, uploading process begins
            filename = str(uuid.uuid4().hex[:12]) # Create unique random ID for file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) #Save the file in UPLOAD_FOLDER
            append_file_id(filename) #to add File_id into status_manager.csv
            flash('Upload is done!','success')
            return redirect(url_for('home'))
    return render_template('upload_dataset.html') #for GET requests it just shows an upload page
#end submit_job page==========================

#train_dataset page=====================================
#This page handles training and parameter selection for each algorithm
@app.route("/train_dataset/<string:file_id>/",methods=['GET', 'POST'])
def train_dataset(file_id):
    if request.method == 'POST': # When you POST, it means you have chosen your prefered
                                 # classification algorithm and its parametes
        data = request.form #Classifier type and its parameters
        if data:
            #loads the status_manager to store training parametes
            df_status_manager = pd.read_csv('status_manager.csv',header=[0], index_col=[0]).fillna(value = '')
            df_status_manager.at[file_id,'method'] = str(data['model_name']) #selected classifier algorithm
            df_status_manager.at[file_id,'status'] = str('Training')
            df_status_manager.at[file_id,'parameters'] = {x:data[x] for x in list(data.keys())} #stores parameters as a dict
            df_status_manager.to_csv('status_manager.csv', index=[0], header=df_status_manager.columns) #saves the status_manager.csv whit new changes

            # Call for training in using Celery and RabbitMQ
            train_function.delay(file_id)

            # After training starts inside Celery, webpage redirects
            # to Homepage and shows a "Training..." badge in front of
            # specified File. You can predict your test values after
            # training process is over
            return redirect(url_for('home'))
    return render_template('train_dataset.html',file_id=file_id) #When method is GET
#end train_dataset page=================================

#predict_dataset page=====================================
#This page handles predicting the lablel for an input data after model training is over
@app.route("/predict_dataset/<string:file_id>/",methods=['GET', 'POST'])
def predict_dataset(file_id):
    #loads the status_manager to store training parametes
    df_status_manager = pd.read_csv('status_manager.csv',header=[0], index_col=[0]).fillna(value = '')
    parameters = eval(df_status_manager['parameters'].loc[file_id]) #convert stored model parametes as string to dict
    model_name = parameters['model_name'] # name of the trained model

    if request.method == 'POST': # When you POST, it means you have entered a test data
        if not request.form['input_value']=='':#checks if input data is not empty
            input_value = request.form['input_value'] #entered test data
            predict_result = prediction_function(file_id , input_value=input_value) #predicting the label for a new data
            return render_template('predict_dataset.html',file_id=file_id,model_name=model_name,predict_result=predict_result) #showing the result
        else:
            flash('No input value entered','danger')#No test data is entered
    return render_template('predict_dataset.html',file_id=file_id,model_name=model_name,predict_result='')#When method is GET, it shows a textbox and submit bottun to enter new test data
#end predict_dataset page=================================

#Home page=====================================
#Dashboard or Homepage
@app.route("/")
def home():
    # Load status_manager to show on the table
    status_manager = pd.read_csv(status_manager_address ,header=0,  low_memory=False, sep=',')#Load all process
    status_manager_records = status_manager.to_records()#Convert dataframe to records for easier use with render_template
    return render_template('home.html',process_list=status_manager_records)
#end Home page=================================

#end Web Pages **********************************************************






# Functions *************************************************************
# allowed_file====================================
def allowed_file(filename):
    '''
    Checks if the uploaded file has aد appropriate extension

    Input(s):
    filename: The file name when it is uploading

    Output(s):
     -  -  - :(Boolean) Basically it says Yes or NO
    '''
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
#end allowed_file=================================

# append_file_id====================================
def append_file_id(fileID):
    '''
    Append information of newly uploaded file in "status_manager.csv"

    Input(s):
    fileID: The unique random ID which is created after the file is uploaded

    Output(s):
    -
    '''
    data_new_row = {
    'file_id': fileID,
    'upload_date': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'method': '',
    'parameters': '',
    'pickle_address': '',
    'status': 'Upload', #set status to "Upload" to specify this file hasn't trained yet
    'details': ''
    }
    df_new_row = pd.DataFrame(data_new_row, index=[0])
    df_new_row.to_csv('status_manager.csv', mode='a', index=False, header=False) #saves status_manager.csv
#end append_file_id=================================



# prediction_function====================================
def prediction_function(fileID, input_value):
    '''
    A function to predict new input values or test data for a trained model.
    Based on "fileID" the trained model loads and label for "input_value" predicts.

    Input(s):
    fileID: The unique random ID which is created after the file is uploaded
    input_value: Test data to be predicted

    Output(s):
    -  -  - : Predicted label. (Only NUMERICAL Labels Are Acceptable!)
    '''
    df_status_manager = pd.read_csv('status_manager.csv',header=[0], index_col=[0]).fillna(value = '')#loads status_manager.csv to find trained model address and other parametrs
    pickle_code = df_status_manager['pickle_address'].loc[fileID] #trained model name
    pickle_address = os.path.join('files','results',pickle_code)
    with open(pickle_address, 'rb') as handle:#loads the trained model
        clf = pickle.load(handle)

    testX =np.expand_dims([float(x.strip()) for x in input_value.split(',')],axis=0) #preparing test data
    testY = clf.predict(testX)#predicting label for test data

    return int(testY[0])
#end prediction_function=================================

#end Functions **********************************************************





if __name__ == '__main__':
    app.run(debug=True)
