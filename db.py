# db.py
import requests
from sqlalchemy import create_engine, Column, Integer, String, Boolean, JSON, DateTime, Table, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///site.db')
Session = sessionmaker(bind=engine)
session = Session()

user_like_association = Table('user_like_association', Base.metadata,
                Column('user_id', String, ForeignKey('user.id')),
                Column('post_id', Integer, ForeignKey('post.id'))
)

user_dislike_association = Table('user_dislike_association', Base.metadata,
                Column('user_id', String, ForeignKey('user.id')),
                Column('post_id', Integer, ForeignKey('post.id'))
)

class User(Base):
    __tablename__ = 'user'
    id = Column(String(120), primary_key=True)
    username = Column(String(80), nullable=False)
    likes = relationship('Post', secondary=user_like_association, back_populates='liked_by')
    dislikes = relationship('Post', secondary=user_dislike_association, back_populates='disliked_by')
    isAdmin = Column(Boolean, default=False)

class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(250), nullable=False)
    url = Column(String(100), nullable=False)
    date_posted = Column(DateTime, nullable=False, default=datetime.utcnow)
    likes = Column(Integer, default=0, nullable=False)
    dislikes = Column(Integer, default=0, nullable=False)
    liked_by = relationship('User', secondary=user_like_association, back_populates='likes')
    disliked_by = relationship('User', secondary=user_dislike_association, back_populates='dislikes')

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"
