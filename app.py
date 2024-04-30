from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus, urlencode
from flask import Flask, request, jsonify, redirect, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from db import Post, User, user_like_association, user_dislike_association
import secrets
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.secret_key = secrets.token_urlsafe(16)
"""
"""

Base = declarative_base()
engine = create_engine('sqlite:///site.db')
Session = sessionmaker(bind=engine)

db = SQLAlchemy(app)

Base.metadata.create_all(engine, checkfirst=True)

oauth = OAuth(app)

oauth.register(
        "auth0",
        client_id="kMehFewqaxeoWnmDEjdQRLQlQzpzzkCe",
        client_secret="1nQqMP5Cghh9BsjQIaMUUvhEeNuXkrx95MWap2y60rlj9VrDy6frD2uN5QkJ61lw",
        client_kwargs={"scope": "openid profile email",},
        server_metadata_url="https://dev-fkmst0p3l8ckzcn1.us.auth0.com/.well-known/openid-configuration"
)

@app.route('/')
def home():
    user_info = session.get("user")
    if user_info:
        user_id = user_info.get("sub")
        username = user_info.get("nickname")
    else:
        user_id = 0
        username = 'guest'
    db_session = Session()
    posts = db_session.query(Post).order_by(Post.date_posted.desc()).all()
    db_session.close()
    return render_template('home.html', posts=posts, user_id=user_id, username=username)

@app.route("/callback",methods=["GET","POST"])
def callback():
    """ Auth0 Callback route """
    token = oauth.auth0.authorize_access_token()
    nonce = session["nonce"]
    userinfo = oauth.auth0.parse_id_token(token, nonce)
    session["user"] = userinfo

    db_session = Session()
    user = db_session.query(User).filter_by(id=userinfo["sub"]).first()
    if user is None:
        username = userinfo["nickname"] if "nickname" in userinfo else "Unknown"
        user = User(id=userinfo["sub"], username=username)
        db_session.add(user)
        db_session.commit()

    return redirect(url_for('home'))

@app.route('/register')
def register():
    """ To register for the site, redirects to callback """
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback",
        _external=True), nonce=nonce)

@app.route('/login')
def login():
    """ To log into the site, redirects to callback """
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback",
        _external=True), nonce=nonce)

@app.route("/logout")
def logout():
    """ To log out of the site, redirects the user back to home after """
    session.clear()
    return redirect(
        "https://dev-fkmst0p3l8ckzcn1.us.auth0.com/v2/logout?" + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": kMehFewqaxeoWnmDEjdQRLQlQzpzzkCe,
            },
            quote_via=quote_plus,
        )
    )


@app.route('/profile')
def profile():
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for('home'))

    user_id = user_info.get("sub")
    username = user_info.get("nickname")

    return render_template('profile.html', user_id=user_id, username=username)

@app.route('/create_post', methods=['POST', 'GET'])
def create_post():
    if request.method == 'POST':
        db_session = Session()
        post_title = request.form['title']
        post_url = request.form['url']
        post_content = request.form['content']
        new_post = Post(title=post_title, content=post_content, url=post_url)
        db_session.add(new_post)
        db_session.commit()
        db_session.close()
        return redirect(url_for('home'))
    return render_template('create_post.html')

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    """ Route which disliked a specific post and returns user back to home """
    user_info = session.get("user")
    user_id = user_info.get("sub") if user_info else None

    if user_id and not (has_liked(post_id, user_id) or has_disliked(post_id, user_id)):
        save_like(post_id, user_id)

    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    """ Route which disliked a specific post and returns user back to home """
    user_info = session.get("user")
    user_id = user_info.get("sub") if user_info else None

    if user_id and not (has_disliked(post_id, user_id) or has_liked(post_id, user_id)):
        save_dislike(post_id, user_id)

    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    user_info = session.get("user")
    user_id = user_info.get("sub") if user_info else None
    db_session = Session()

    if not is_admin(user_id, db_session):
        abort(403)

    post = db_session.query(Post).get(post_id)

    if post:
        db_session.execute(user_like_association.delete().where(
            user_like_association.c.post_id == post_id))
        db_session.delete(post)
        db_session.commit()

    db_session.close()

    return redirect(url_for('home'))
    
@app.route('/post/<int:post_id>/edit', methods=['GET'])
def show_edit_post_form(post_id):
    db_session = Session()
    post = db_session.query(Post).get_or_404(post_id)
    db_session.close()
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    db_session = Session()
    post = db_session.query(Post).get_or_404(post_id)
    post.title = request.form['title']
    post.url = request.form['url']
    post.content = request.form['content']
    db_session.commit()
    db_session.close()
    return redirect(url_for('home'))

def save_like(post_id, user_id):
    """ Saves a like and reflects database changes when a user likes a post """
    db_session = Session()
    existing_like = has_liked(post_id, user_id)

    if not existing_like:
        like_association = user_like_association.insert().values(
                user_id=user_id, post_id=post_id)
        db_session.execute(like_association)
        db_session.commit()

        post = db_session.query(Post).get(post_id)

        if post:
            post.likes += 1
            db_session.commit()

    db_session.close()



def save_dislike(post_id, user_id):
    """ Updates the DB with new values if a user dislikes a post """
    db_session = Session()

    existing_dislike = has_disliked(post_id, user_id)
    if not existing_dislike:

        dislike_association = user_dislike_association.insert().values(
                user_id=user_id, post_id=post_id)
        db_session.execute(dislike_association)
        db_session.commit()

        post = db_session.query(Post).get(post_id)
        if post:
            post.dislikes += 1
            db_session.commit()

    db_session.close()

def has_liked(post_id, user_id):
    """ Checks if a user has already liked a specific post """
    db_session = Session()
    like_association = user_like_association.alias()

    result = db_session.query(like_association.c.post_id)\
        .filter(like_association.c.user_id == user_id,
                    like_association.c.post_id == post_id)\
        .first()

    db_session.close()
    return result is not None
    


def has_disliked(post_id, user_id):
    """ Checks if a user has already disliked a specific post """
    db_session = Session()
    
    dislike_association = user_dislike_association.alias()

    result = db_session.query(dislike_association.c.post_id)\
            .filter(dislike_association.c.user_id == user_id,
                    dislike_association.c.post_id == post_id)\
            .first()
    
    db_session.close()
    return result is not None

if __name__ ==  '__main__':
	app.run(debug=True)

