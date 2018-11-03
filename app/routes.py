from flask import render_template, flash, redirect
from app import app
from app.forms import LoginForm

@app.route('/')

@app.route('/home', methods = ['GET', 'POST'])
def home():
    users = {'username': 'test_user'}
    return render_template('base.html', title = 'test_title', user = users)

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
