# -*- coding: utf-8 -*-
"""
Created on November 10, 2017 09:40:51 2017

@author: Jamie
"""
import pandas as pd
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, Markup, send_from_directory
from werkzeug.utils import secure_filename
import json
from Optimizer import optimize
from Predictor import ownershipPredict

UPLOAD_FOLDER = os.path.dirname(os.path.realpath(__file__)) + '/temp'
ALLOWED_EXTENSIONS = set(['csv', 'txt'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def main():
    return render_template('index.html')

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

class Marker:
    def __init__(self, lon, lat, rid, address):
        self.lon = lon
        self.lat = lat
        self.rid = rid
        self.address = address

#UPLOAD DAILY PLAYERS
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/uploadCSV", methods=['GET', 'POST'])
def uploadCSV():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return render_template('upload_csv.html')

#upload button
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

#Add twitter counts and pre-process for prediction
@app.route("/initializeFanDuels")
def initializeFanDuels():
    predict = ownershipPredict()
    twitter = predict.load_fanduel()

    twitter.loc[twitter['D'] == 1, 'Position'] = 'D'
    twitter.loc[twitter['QB'] == 1, 'Position'] = 'QB'
    twitter.loc[twitter['K'] == 1, 'Position'] = 'K'
    twitter.loc[twitter['RB'] == 1, 'Position'] = 'RB'
    twitter.loc[twitter['TE'] == 1, 'Position'] = 'TE'
    twitter.loc[twitter['WR'] == 1, 'Position'] = 'WR'

    twitter.loc[twitter['home'] == 1, 'Home/Away'] = 'Home'
    twitter.loc[twitter['home'] == 0, 'Home/Away'] = 'Away'

    twitter.loc[twitter['doubtful'] == 0, 'Injury Status'] = 'Healthy'
    twitter.loc[twitter['pup'] == 0, 'Injury Status'] = 'Healthy'
    twitter.loc[twitter['out'] == 0, 'Injury Status'] = 'Healthy'
    twitter.loc[twitter['questionable'] == 0, 'Injury Status'] = 'Healthy'

    twitter.loc[twitter['doubtful'] == 1, 'Injury Status'] = 'Doubtful'
    twitter.loc[twitter['pup'] == 1, 'Injury Status'] = 'PUP'
    twitter.loc[twitter['out'] == 1, 'Injury Status'] = 'Out'
    twitter.loc[twitter['questionable'] == 1, 'Injury Status'] = 'Questionable'

    twitter = twitter[['play', 'salary', 'proj_points', 'Position', 'Injury Status', 'Home/Away', 'd_points', 'minTweetCounts', 'sentimentCounts']].copy()
    twitter.columns = ['Player','Salary', 'Projected Points', 'Position', 'Injury Status', 'Home/Away', 'Opponent Score', 'Tweet Counts', 'Sentiment Counts']
    return render_template('twittercounts.html', tables=[twitter.to_html(classes='twitter')],
    titles=['twitter_count'])

#Go Back to main menu
@app.route("/goBack")
def goBack():
    return render_template('index.html')

#OWNERSHIP PROJECTIONS
@app.route("/ownershipPredictions", methods=['GET', 'POST'])
def ownershipPredictions():
    make_predict = ownershipPredict()
    data = make_predict.return_project()[['play','Position', 'salary','proj_points', 'Predicted Ownership']].copy()
    data.columns = ['Player', 'Position', 'Salary', 'Projected Points', 'Projected Ownership']
    return render_template('own_predict.html', tables=[data.to_html(classes='data')],
    titles=['ownership_projections'])

#OPTIMIZE LINEUP
@app.route("/preOPT")
def preOPT():
    return render_template('pre_opt.html')

#after inputing weights, returns optimal lineup
@app.route('/preOPT', methods=['POST'])
def my_form_post():
    text = request.form['text']
    text2 = request.form['text2']
    points = text.upper()
    ownership = text2.upper()
    make_optimal = optimize()
    data = make_optimal.solve_lineup([float(points),float(ownership)])
    return render_template('opt_lineup.html', tables=[data.to_html(classes='data')],
    titles=['optimal_lineup'])

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return

if __name__ == "__main__":
    app.run()