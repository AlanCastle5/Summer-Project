from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from db import db, Post

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)

"""
"""

@app.route('/')
def home():
	posts = Post.query.order_by(Post.date_posted.desc()).all()
	return render_template('home.html', posts=posts)

@app.route('/profile')
def profile():
	return render_template('profile.html')

@app.route('/create_post', methods=['POST', 'GET'])
def create_post():
	if request.method == 'POST':
		post_title = request.form['title']
		post_content = request.form['content']
		new_post = Post(title=post_title, content=post_content)
		db.session.add(new_post)
		db.session.commit()
		return redirect(url_for('home'))
	return render_template('create_post.html')

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.dislikes += 1
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('home'))
    
@app.route('/post/<int:post_id>/edit', methods=['GET'])
def show_edit_post_form(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.title = request.form['title']
    post.content = request.form['content']
    db.session.commit()
    return redirect(url_for('home'))
    
if __name__ ==  '__main__':
	with app.app_context():
		db.create_all()
	app.run(debug=True)

