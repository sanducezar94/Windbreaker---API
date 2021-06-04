from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship



base = declarative_base()

class User(base):
    __tablename__ = "user"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(48), unique=True)
    email = Column('email', String(128),  unique=True)
    password = Column('password', String(128))
    icon = Column('icon', String(60))
    rated_routes = relationship('UserRatedRoute', lazy='joined', back_populates='user_parent')
    rated_comments = relationship('UserRatedComment', lazy='joined', back_populates='user_parent')


class Route(base):
    __tablename__ = "route"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(80))
    rating = Column('rating', Float(3), default=0, nullable=False)
    one_star = Column('onestar', Integer, default=0, nullable=False)
    two_star = Column('twostar', Integer, default=0, nullable=False)
    three_star = Column('threestar', Integer, default=0, nullable=False)
    four_star = Column('fourstar', Integer, default=0, nullable=False)
    five_star = Column('fivestar', Integer, default=0, nullable=False)
    comments = relationship("Comment", back_populates="route_parent")

class UserRatedRoute(base):
    __tablename__ = "userratedroute"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"))
    route_id = Column('route_id', Integer, ForeignKey('route.id', ondelete="CASCADE"))
    user_parent = relationship('User', back_populates='rated_routes')

class UserRatedComment(base):
    __tablename__ = "userratedcomment"
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    rating = Column('rating', Integer)
    user_id = Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"))
    comment_id = Column('comment_id', Integer, ForeignKey('comment.id', ondelete="CASCADE"))
    user_parent = relationship('User', back_populates='rated_comments')

class Comment(base):
    __tablename__ = "comment"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    text = Column('text', String(128))
    user_id = Column('user', String(80), ForeignKey('user.name', ondelete="CASCADE"))
    route_id = Column('route_id', Integer, ForeignKey('route.id', ondelete="CASCADE"))
    rating = Column('rating', Integer)
    created_on = Column('created_on', DateTime)
    route_parent = relationship("Route", back_populates="comments")