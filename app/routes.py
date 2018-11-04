from __future__ import print_function
from flask import render_template, flash, redirect, jsonify, request, make_response
from app import app
from app.forms import LoginForm, CreateAccForm
import random
import hashlib
import os
import MySQLdb
import webapp2
import json

# These environment variables are configured in app.yaml.
CLOUDSQL_CONNECTION_NAME = os.environ.get('CLOUDSQL_CONNECTION_NAME')
CLOUDSQL_USER = os.environ.get('CLOUDSQL_USER')
CLOUDSQL_PASSWORD = os.environ.get('CLOUDSQL_PASSWORD')

escape_dict={'\a':r'\a',
           '\b':r'\b',
           '\c':r'\c',
           '\f':r'\f',
           '\n':r'\n',
           '\r':r'\r',
           '\t':r'\t',
           '\v':r'\v',
           '\'':r'\'',
           '\"':r'\"',
           '\0':r'\0',
           '\1':r'\1',
           '\2':r'\2',
           '\3':r'\3',
           '\4':r'\4',
           '\5':r'\5',
           '\6':r'\6',
           '\7':r'\7',
           '\8':r'\8',
           '\9':r'\9'}

def raw_text(text):
    """Returns a raw string representation of text"""
    new_string=''
    for char in text:
        try: new_string+=escape_dict[char]
        except KeyError: new_string+=char
    return new_string


def make_api_response(message, code):
    return make_response((json.dumps({'status': message}, indent = 4), code))

def default_param_factory():
    params = {}

    params['user_id'] = 'not logged in'
    params['username'] = 'not logged in'
    params['passhash'] = None

    params['response'] = None

    return params

params = default_param_factory()

def mapping_leaderboard(info_tuple):
    json_dicts = []
    for bundle in info_tuple:
        dict_bundle = {}
        dict_bundle['name'] = bundle[0]
        dict_bundle['time'] = bundle[1]
        json_dicts.append(dict_bundle)
    return json_dicts

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

# Simply performs the query and returns the appropriate string
def get_data_from_database(query):
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')
    cursor.execute(query)
    stuff = cursor.fetchall()
    cursor.close()
    db.commit()
    return stuff

def connect_to_cloudsql():
    # Attempts to connect using UNIX socket
    if True: # os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
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

@app.route('/results', methods = ['GET', 'POST'])
def results():
    print(request.args)
    print(request.form)
    category = request.form['category']
    question_id = request.form['question_id']
    user_answer = request.form['response']
    print(category, question_id, user_answer)
    username = request.cookies['username']
    user_id = request.cookies['user_id']
    raw = get_data_from_database('SELECT * FROM Question q WHERE q.id="{}"'.format(question_id))[0]
    answer = raw[4]

    correct = abs(float(user_answer) - float(answer)) < 0.01
    time = random.randint(1, 300)
    if correct:
        get_data_from_database('INSERT INTO Solves (user_id, question_id, time) VALUES ("{}", "{}", "{}")'.format(user_id, question_id, time))

    unsolved = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}" AND NOT (q.id = ANY(SELECT question_id FROM Solves WHERE user_id="{}"))'.format(category, user_id))[0][0]
    total = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}"'.format(category))[0][0]

    return render_template('results.html', category = category, total = total, unsolved = unsolved, correct = correct)

@app.route('/question', methods = ['GET', 'POST'])
def question():
    category = request.args['category']
    username = request.cookies['username']
    user_id = request.cookies['user_id']
    raw = get_data_from_database('SELECT * FROM Question q WHERE q.category="{}" AND NOT(q.id = ANY(SELECT question_id FROM Solves WHERE user_id="{}"))'.format(category, user_id))
    random_raw = random.choice(raw)
    question_id = random_raw[0]
    category = random_raw[1]
    text = random_raw[2]
    question = random_raw[3]
    answer = random_raw[4]

    return render_template('question.html', question_text = raw_text(question.strip('$')).replace('\\', '\\\\'), category = category, answer = answer, question_id = question_id, question = text)

@app.route('/category', methods = ['GET', 'POST'])
def category():
    category = request.args['category']
    print(request.cookies)
    username = request.cookies['username']
    user_id = request.cookies['user_id']

    unsolved = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}" AND NOT (q.id = ANY(SELECT question_id FROM Solves WHERE user_id="{}"))'.format(category, user_id))[0][0]
    total = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}"'.format(category))[0][0]

    return render_template('math.html', unsolved = unsolved, total = total, category = category)


@app.route('/home', methods = ['GET', 'POST'])
def home():
    global params
    print(request.cookies)
    logged_in = False

    categories = list(thing[0] for thing in get_data_from_database('SELECT DISTINCT Category FROM Question'))

    if 'username' not in request.cookies:
        params['user_id'] = 'not logged in'
        resp = make_response(render_template('base.html', title = 'test_title', logged_in = False))
        resp.set_cookie('user_id', 'not logged in')
        resp.set_cookie('username', 'not logged in')
        return resp

    # This signifies logged in
    if request.cookies['username'] != 'not logged in':
        params['username'] = request.cookies['username']
        logged_in = True

    # This signifies just created account
    if params['response'] is not None:
        resp = params['response']
        params['response'] = None
        return resp

    return render_template('base.html', title = 'test_title', username = params['username'], logged_in = logged_in,
    categories = categories)

# Grabs single user data
@app.route('/api/v1/user', methods = ['GET', 'POST'])
def v1_user():
    if 'username' in request.args:
        username = request.args['username']
        raw = get_data_from_database('SELECT * FROM User WHERE name = "{}"'.format(username))
        return jsonify(mapping_users(raw))

# Pass the player id, question id, and time taken to add that problem to the player's solves.
@app.route('/api/v1/solve', methods = ['GET', 'POST'])
def v1_solve():
    if 'user_id' and 'question_id' and 'time' in request.args:
        user_id = request.args['user_id']
        question_id = request.args['question_id']
        time = request.args['time']
        raw = get_data_from_database('INSERT INTO Solves (user_id, question_id, time) VALUES ("{}", "{}", "{}")'.format(user_id, question_id, time))
        return make_response((json.dumps({'status': 'success'}, indent = 4), 201))

# Gets all data back for solves of that question
@app.route('/api/v1/leaderboard', methods = ['GET', 'POST'])
def scoreboard():
    if 'question_id' in request.args:
        # TODO: Grab correct SQL query
        raw = get_data_from_database('SELECT u.name, s.time FROM Solves s JOIN User u ON s.user_id = u.id WHERE s.question_id = "{}" ORDER BY s.time LIMIT 10'.format(request.args['question_id']))
        print(raw)
        # TODO: Probably user mapping?
        return jsonify(mapping_leaderboard(raw))
    return make_api_response('fail', 400)

# Queries on solves
@app.route('/api/v1/solves', methods = ['GET', 'POST'])
def v1_solves():
    # TODO: Proper queries
    raw = None
    if 'user_id' in request.args and 'category' in request.args:
        raw = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}" AND NOT (q.id = ANY(SELECT question_id FROM Solves WHERE user_id="{}"))'.format(request.args['category'], request.args['user_id']))[0][0]
        raw2 = get_data_from_database('SELECT COUNT(*) FROM Question q WHERE q.category="{}"'.format(request.args['category']))[0][0]
        return jsonify({'unsolved': raw, 'total': raw2})
    elif 'user_id' in request.args: # All solves that this player made
        raw = get_data_from_database('SELECT * FROM Solves WHERE user_id="{}"'.format(request.args['user_id']))
    elif 'question_id' in request.args: # All solves on the specified question
        raw = get_data_from_database('SELECT * FROM Solves WHERE question_id="{}"'.format(request.args['question_id']))
    elif 'category' in request.args: # All solves of this particular category. This is sorta hacky.
        raw = get_data_from_database('SELECT * FROM Solves JOIN Question ON Solves.question_id = Question.id WHERE Category = "{}"'.format(request.args['category']))
    else: # All solves in general
        raw = get_data_from_database('SELECT * FROM Solves')
    return jsonify(mapping_solves(raw))

# Grabs a random unanswered (by the specified player) question in the specified category
@app.route('/api/v1/question')
def v1_category():
    # TODO: Correct SQL Query
    raw = None
    if 'user_id' in request.args and 'category' in request.args:
        raw = get_data_from_database('SELECT * FROM Question q WHERE q.category="{}" AND NOT(q.id = ANY(SELECT question_id FROM Solves WHERE user_id="{}"))'.format(request.args['category'], request.args['user_id']))
        random_raw = random.choice(raw)
        random_unsolved = {}
        random_unsolved['id'] = random_raw[0]
        random_unsolved['category'] = random_raw[1]
        random_unsolved['text'] = random_raw[2]
        random_unsolved['question'] = random_raw[3]
        random_unsolved['answer'] = random_raw[4]
        print(random_unsolved)
        return jsonify(random_unsolved)

    return make_api_response('fail', 400)

# Pass back all users
@app.route('/api/v1/users')
def v1_users():
    raw = get_data_from_database('SELECT * FROM User')
    return jsonify(mapping_users(raw))

@app.route('/api/v1/questions')
def v1_questions():
    raw = get_data_from_database('SELECT * FROM Question')
    return jsonify(mapping_question(raw))

# All the problems in <category> which the user hasn't solved
@app.route('/api/v1/<user_id>/<category>')
def category_questions(user_id, category):
    raw = get_data_from_database('SELECT * FROM Question q WHERE q.category="{}" AND NOT (q.id = ANY(SELECT question_id FROM Solves WHERE user_id={}))'.format(category, user_id))
    return jsonify(mapping_question(raw))

@app.route('/api/v1/solves/<user_id>')
def solves_by_user(user_id):
    raw = get_data_from_database('SELECT * FROM Solves WHERE user_id="{}"')
    return jsonify(mapping_solves(raw))

@app.route('/api/v1/login', methods = ['GET', 'POST'])
def api_login():
    global params

    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')

    print(request.args)

    if len(request.args) > 1:
        username = request.args['name']
        password = hashlib.sha256(request.args['pass']).hexdigest()
        # Check if username/password exist in database
        cursor.execute('SELECT * FROM User WHERE User.name = "{}" AND User.hashpass = "{}"'.format(username, password))
        query_result = cursor.fetchall()

        if len(query_result) == 1:
            user_data = query_result[0]
            user_id, username, _ = user_data
            return make_response((json.dumps({'status': 'success', 'user_id': user_id, 'username': username}, indent = 4), 201))
        else:
            return make_response((json.dumps({'status': 'fail', 'user_id': None, 'username': None}, indent = 4), 200))

    return make_response((json.dumps({'status': 'fail', 'user_id': None, 'username': None}, indent = 4), 400))

@app.route('/api/v1/create', methods = ['GET', 'POST'])
def create_api():
    db = connect_to_cloudsql()
    cursor = db.cursor()
    cursor.execute('USE calhacktable')

    # Doesn't activate unless we sent a post
    if len(request.args) > 1:
        new_username = request.args['name']
        new_hashpass = hashlib.sha256(request.args['pass']).hexdigest()
        # Check if username exists in database
        cursor.execute('SELECT * FROM User WHERE name = "{}"'.format(new_username))
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
            user_id = cursor.fetchall()[0][0]
            return make_response((json.dumps({'status': 'success', 'user_id': user_id, 'username': new_username}, indent = 4), 201))
        else:
            return make_response((json.dumps({'status': 'fail', 'user_id': None, 'username': None}, indent = 4), 200))

    return make_response((json.dumps({'status': 'fail', 'user_id': None, 'username': None}, indent = 4), 400))

@app.route('/api/v1/')

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    params['user_id'] = 'not logged in'
    resp = make_response(render_template('logout.html'))
    resp.set_cookie('user_id', 'not logged in')
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
        cursor.execute('SELECT * FROM User WHERE name = "{}"'.format(new_username))
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
            resp.set_cookie('user_id', str(new_id), max_age = 10000)
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
            categories = list(thing[0] for thing in get_data_from_database('SELECT DISTINCT Category FROM Question'))
            # Makes the cookie expire after a day
            resp = make_response(render_template('base.html', username = user_data[1], logged_in = True, categories = categories))
            resp.set_cookie('user_id', str(user_data[0]), max_age = 10000)
            resp.set_cookie('username', user_data[1], max_age = 10000)
            params['response'] = resp
            return redirect('/home')
        else:
            fail = True

    return render_template('login.html', title='Sign In', fail = fail)
