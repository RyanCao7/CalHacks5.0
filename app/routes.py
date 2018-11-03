from __future__ import print_function
from flask import render_template, flash, redirect, jsonify, request, make_response
from app import app
from app.forms import LoginForm, CreateAccForm
import hashlib
import os
import MySQLdb
import webapp2
import json

# These environment variables are configured in app.yaml.
CLOUDSQL_CONNECTION_NAME = os.environ.get('CLOUDSQL_CONNECTION_NAME')
CLOUDSQL_USER = os.environ.get('CLOUDSQL_USER')
CLOUDSQL_PASSWORD = os.environ.get('CLOUDSQL_PASSWORD')

def default_param_factory():
    params = {}

    params['user_id'] = 'not logged in'
    params['username'] = None
    params['passhash'] = None

    params['response'] = None

    return params

params = default_param_factory()

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
    global params
    print(request.cookies)
    logged_in = False

    # This signifies logged in
    assert(request.cookies['username'] is not None)
    if request.cookies['username'] != 'not logged in':
        params['username'] = request.cookies['username']
        logged_in = True

    # This signifies just created account
    if params['response'] is not None:
        resp = params['response']
        params['response'] = None
        return resp

    return render_template('base.html', title = 'test_title', username = params['username'], logged_in = logged_in)

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

@app.route('/api/v1/<user_id>/<category>')
def category_questions(user_id, category):
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute('SELECT * FROM Question q WHERE q.category="{}" AND NOT (q.id = ANY(SELECT question_id FROM Solves WHERE user_id={}))'.format(category, user_id))
    stuff = cursor.fetchall()

    return jsonify(mapping_question(stuff))

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    params['user_id'] = 'not logged in'
    resp = make_response(render_template('logout.html'))
    resp.set_cookie('userID', 'not logged in')
    resp.set_cookie('username', 'not logged in')
    return resp


@app.route('/create', methods = ['GET', 'POST'])
def create_account():
    global params

    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')

    fail = False

    # Doesn't activate unless we sent a post
    if len(request.args) > 1:
        new_username = request.args['name']
        new_hashpass = hashlib.sha256(request.args['pass']).hexdigest()
        # Check if username exists in database
        cursor.execute('SELECT * FROM User WHERE User.name = "{}"'.format(new_username))
        query_result = cursor.fetchall()
        cursor.close()
        cursor = db.cursor()

        # If the given username doesn't exist, go ahead and create the account!
        if len(query_result) == 0:
            # First insert, then grab ID
            cursor.execute('INSERT INTO User(name, hashpass) VALUES ("{}", "{}")'.format(new_username, new_hashpass))
            cursor.close()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM User')
            db.commit()

            # Grab the ID from the database
            cursor.execute('SELECT * FROM User WHERE User.name = "{}" AND User.hashpass = "{}"'.format(new_username, new_hashpass))
            new_id = cursor.fetchall()[0][0]

            # Set cookies accordingly
            resp = make_response(render_template('base.html', username = new_username, logged_in = True))
            resp.set_cookie('userID', str(new_id), max_age = 10000)
            resp.set_cookie('username', str(new_username), max_age = 10000)
            params['response'] = resp
            return redirect('/home')
        else:
            fail = True

    return render_template('create.html', title='Sign In', fail = fail)


@app.route('/login', methods = ['GET', 'POST'])
def login():
    global params

    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')

    fail = False
    # Doesn't activate unless we sent a post
    if len(request.args) > 1:
        username = request.args['name']
        password = hashlib.sha256(request.args['pass']).hexdigest()
        # Check if username/password exist in database
        cursor.execute('SELECT * FROM User WHERE User.name = "{}" AND User.hashpass = "{}"'.format(username, password))
        query_result = cursor.fetchall()

        if len(query_result) == 1:
            user_data = query_result[0]
            # Makes the cookie expire after a day
            resp = make_response(render_template('base.html', username = user_data[1], logged_in = True))
            resp.set_cookie('userID', str(user_data[0]), max_age = 10000)
            resp.set_cookie('username', user_data[1], max_age = 10000)
            params['response'] = resp
            return redirect('/home')
        else:
            fail = True

    return render_template('login.html', title='Sign In', fail = fail)
