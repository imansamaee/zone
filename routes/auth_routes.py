import os
from dotenv import load_dotenv
from flask import Blueprint, render_template, request, redirect, url_for, session

auth_blueprint = Blueprint('auth', __name__)
load_dotenv()  # Load environment variables from .env file

USERNAME = os.getenv('TAGTRADE_USERNAME')
PASSWORD = os.getenv('TAGTRADE_PASSWORD')


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['username'] = username
            return "ok"
        else:
            print(USERNAME,PASSWORD)
            return "failed"
    return render_template('login.html')

@auth_blueprint.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))  # Redirect to the login page