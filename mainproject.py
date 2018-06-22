from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Shoppingmall, Cloth, User
# Import Login session
from flask import session as login_session
import random
import string
# imports for gconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
# import login decorator
from functools import wraps
from flask import Flask, render_template
from flask import request, redirect, jsonify, url_for, flash
app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json',
                            'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog"

engine = create_engine('sqlite:///dresses.db')
Base.metadata.bind = engine


DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@app.route('/login')
def showlogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application-json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # upgrade the authorization code in credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade\
                                            the authorization code'), 401)
        response.headers['Content-Type'] = 'application-json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1].decode("utf-8"))
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response
    # Access token within the app
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user\
                                            is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.

    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    response = make_response(json.dumps('Succesfully connected'), 200)

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # See if user exists or if it doesn't make a new one
    print('User email is' + str(login_session['email']))
    user_id = getUserID(login_session['email'])
    if user_id:
        print('Existing user#' + str(user_id) + 'matches this email')
    else:
        user_id = createUser(login_session)
        print('New user_id#' + str(user_id) + 'created')
        login_session['user_id'] = user_id
        print('Login session is tied to :id#' + str(login_session['user_id']))

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius:100px;- \
      webkit-border-radius:100px;-moz-border-radius: 100px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print("done!")
    return output

# Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).first()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).first()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session.
@app.route('/gdisconnect')
def gdisconnect():
    # only disconnect a connected User
    access_token = login_session.get('access_token')
    print('In gdisconnect access token is %s', access_token)
    print('User name is: ')
    print(login_session['username'])
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.c\
           om/o/oauth2/revoke?token = %s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is')
    print(result)
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke\
                                            token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/logout')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            del login_session['user_id']
            del login_session['provider']
            flash("You have succesfully been logout")
            return redirect(url_for('showShoppingmalls'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showShoppingmalls'))


@app.route('/shoppingmall/<int:shoppingmall_id>/cloth/JSON')
def shoppingmallclothJSON(brand_id):
    shoppingmall = session.query(Shoppingmall).filter_by(
        id=shoppingmall_id).one()
    details = session.query(Cloth).filter_by(
        shoppingmall_id=shoppingmall_id).all()
    return jsonify(Cloth=[i.serialize for i in details])


@app.route('/shoppingmall/<int:shoppingmall_id>/details/<int:details_id>/JSON')
def clothesJSON(shoppingmall_id, details_id):
    Clothes_Details = session.query(Cloth).filter_by(id=details_id).one()
    return jsonify(Cloth_Details=Cloth_Details.serialize)


@app.route('/shoppingmall/JSON')
def shoppingmallsJSON():
    shoppingmalls = session.query(shoppingmall).all()
    return jsonify(shoppingmalls=[r.serialize for r in shoppingmalls])
# Show all shoppingmalls


@app.route('/')
@app.route('/shoppingmall/')
def showShoppingmalls():
    session = DBSession()
    shoppingmalls = session.query(Shoppingmall).all()
    # return "This page will show all my brands"
    session.close()
    return render_template('shoppingmalls.html', shoppingmalls=shoppingmalls)


# Create a new brand
@app.route('/shoppingmall/new/', methods=['GET', 'POST'])
def newShoppingmall():
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newShoppingmall = Shoppingmall(name=request.form['name'])
        session.add(newShoppingmall)
        session.commit()
        session.close()
        return redirect(url_for('showShoppingmalls'))
    else:
        session.close()
        return render_template('newShoppingmall.html')
    # return "This page will be for making a new brand"

# Edit a brand


@app.route('/shoppingmall/<int:shoppingmall_id>/edit/',
           methods=['GET', 'POST'])
def editShoppingmall(shoppingmall_id):
    session = DBSession()
    editShoppingmall = session.query(Shoppingmall).filter_by(
                        id=shoppingmall_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        if request.form['name']:
            print(editShoppingmall.name)
            editShoppingmall.name = request.form['name']
            session.add(editShoppingmall)
            session.commit()
            session.close()
            return redirect(url_for('showShoppingmalls',
                            shoppingmall_id=shoppingmall_id))
    else:
        session.close()
        return render_template('editShoppingmall.html',
                               shoppingmall_id=shoppingmall_id,
                               shoppingmall=editShoppingmall)

    # return 'This page will be for editing shoppingmall %s' % shoppingmall_id

# Delete a shoppingmall


@app.route('/shoppingmall/<int:shoppingmall_id>/delete/',
           methods=['GET', 'POST'])
def deleteShoppingmall(shoppingmall_id):
    session = DBSession()
    deleteShoppingmall = session.query(
        Shoppingmall).filter_by(id=shoppingmall_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        session.delete(deleteShoppingmall)
        session.commit()
        session.close()
        return redirect(
            url_for('showShoppingmalls', shoppingmall_id=shoppingmall_id))
    else:
        session.close()
        return render_template('deleteShoppingmall.html',
                               shoppingmall_id=shoppingmall_id,
                               shoppingmall=deleteShoppingmall)


# Show a brand product
@app.route('/shoppingmall/<int:shoppingmall_id>/')
@app.route('/shoppingmall/<int:shoppingmall_id>/cloth/')
def showCloth(shoppingmall_id):
    session = DBSession()
    shoppingmall = session.query(Shoppingmall).filter_by(
                   id=shoppingmall_id).one()
    details = session.query(Cloth).filter_by(
              shoppingmall_id=shoppingmall_id).all()
    session.close()
    return render_template('cloth.html', details=details,
                           shoppingmall=shoppingmall)
    # return 'This page is the product for brand %s' % brand_id

# Create a new product details


@app.route('/shoppingmall/<int:shoppingmall_id>/shoppingmall/new/',
           methods=['GET', 'POST'])
def newCloth(shoppingmall_id):
    session = DBSession()
    shoppingmall = session.query(Shoppingmall).filter_by(
                   id=shoppingmall_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newShoppingmall = Cloth(
            name=request.form['name'],
            description=request.form['description'],
            price=request.form['price'],
            type=request.form['type'],
            shoppingmall_id=shoppingmall_id,
            user_id=shoppingmall.user_id)

        session.add(newShoppingmall)
        session.commit()
        session.close()

        return redirect(url_for('showCloth', shoppingmall_id=shoppingmall_id))
    else:
        return render_template('newCloth.html',
                               shoppingmall_id=shoppingmall_id)

    return render_template('newCloth.html')
# return 'This page is for making a new product details for shoppingmall %s'

# Edit a cloth details


@app.route('/shoppingmall/<int:shoppingmall_id>/cloth/<int:cloth_id>/edit',
           methods=['GET', 'POST'])
def editCloth(shoppingmall_id, cloth_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    editCloth = session.query(Cloth).filter_by(id=cloth_id).one()
    shoppingmall = session.query(Shoppingmall).filter_by(
                   id=shoppingmall_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editCloth.name = request.form['name']
        if request.form['description']:
            editCloth.description = request.form['name']
        if request.form['price']:
            editCloth.price = request.form['price']
        if request.form['type']:
            editCloth.type = request.form['type']
        session.add(editCloth)
        session.commit()
        session.close()
        return redirect(url_for('showCloth', shoppingmall_id=shoppingmall_id))
    else:
        return render_template('editCloth.html',
                               shoppingmall_id=shoppingmall_id,
                               cloth_id=cloth_id, details=editCloth)

    # return 'This page is for editing product details %s' % product_id

# Delete a cloth details


@app.route('/shoppingmall/<int:shoppingmall_id>/cloth/<int:cloth_id>/delete',
           methods=['GET', 'POST'])
def deleteCloth(shoppingmall_id, cloth_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    shoppingmall = session.query(Shoppingmall).filter_by(
                   id=shoppingmall_id).one()
    deleteCloth = session.query(Cloth).filter_by(id=cloth_id).one()
    if request.method == 'POST':
        session.delete(deleteCloth)
        session.commit()
        session.close()
        return redirect(url_for('showCloth', shoppingmall_id=shoppingmall_id))
    else:
        return render_template('deleteCloth.html',
                               shoppingmall_id=shoppingmall_id,
                               cloth_id=cloth_id, details=deleteCloth)
    # return "This page is for deleting cloth details %s" % cloth_id


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=2000)
