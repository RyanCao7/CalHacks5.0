from __future__ import print_function
from flask import render_template, flash, redirect, jsonify
from app import app
from app.forms import LoginForm
import os
import MySQLdb
import webapp2
import json

# These environment variables are configured in app.yaml.
CLOUDSQL_CONNECTION_NAME = os.environ.get('CLOUDSQL_CONNECTION_NAME')
CLOUDSQL_USER = os.environ.get('CLOUDSQL_USER')
CLOUDSQL_PASSWORD = os.environ.get('CLOUDSQL_PASSWORD')

# Assume data comes in the form
def mapping_question(info_tuple):
    json_dicts = []
    for bundle in info_tuple:
        dict_bundle = {}
        dict_bundle['id'] = bundle[0]
        dict_bundle['text'] = bundle[1]
        dict_bundle['category'] = bundle[2]
        dict_bundle['question'] = bundle[3]
        dict_bundle['answer'] = bundle[4]
        json_dicts.append(dict_bundle)
    return json_dicts

def mapping_solves(info_tuple):
    json_dicts = []
    for bundle in info_tuple:
        dict_bundle = {}
        dict_bundle['id'] = bundle[0]
        dict_bundle['user_id'] = bundle[1]
        dict_bundle['question_id'] = bundle[2]
        dict_bundle['time'] = bundle[3]
        json_dicts.append(dict_bundle)
    return json_dicts

def mapping_users(info_tuple):
    json_dicts = []
    for bundle in info_tuple:
        dict_bundle = {}
        dict_bundle['id'] = bundle[0]
        dict_bundle['name'] = bundle[1]
        json_dicts.append(dict_bundle)
    return json_dicts

def connect_to_cloudsql():
    # Attempts to connect using UNIX socket
    if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
        cloudsql_unix_socket = os.path.join('/cloudsql', CLOUDSQL_CONNECTION_NAME)
        db = MySQLdb.connect(
                unix_socket=cloudsql_unix_socket,
                user=CLOUDSQL_USER,
                passwd=CLOUDSQL_PASSWORD)
    # Attempts to connect using TCP socket
    else:
        db = MySQLdb.connect(
            host='127.0.0.1', user=CLOUDSQL_USER, passwd=CLOUDSQL_PASSWORD)

    return db

@app.route('/')

@app.route('/home', methods = ['GET', 'POST'])
def home():
    users = {'username': 'test_user'}
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute('SELECT * FROM Question')
    stuff = cursor.fetchall()

    cursor.close()
    return jsonify(mapping_question(stuff))
    # return render_template('base.html', title = 'test_title', user = users)

@app.route('/api/v1/users')
def v1_users():
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute('SELECT * FROM User')
    stuff = cursor.fetchall()

    cursor.close()
    return jsonify(mapping_users(stuff))

@app.route('/api/v1/solves')
def v1_solves():
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute('SELECT * FROM Solves')
    stuff = cursor.fetchall()

    cursor.close()
    return jsonify(mapping_solves(stuff))

@app.route('/api/v1/questions')
def v1_questions():
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute('SELECT * FROM Question')
    stuff = cursor.fetchall()

    cursor.close()
    return jsonify(mapping_question(stuff))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    # Doesn't activate unless we sent a post
    if form.validate_on_submit():
        print(form.username.data)
        print(form.remember_me.data)
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('home'))
    return render_template('login.html', title='Sign In', form = form)
