from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

db = SQLAlchemy()

class Namespace(db.Model):
    __tablename__='namespace'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50),unique=True)
    create_time = db.Column(db.DateTime,nullable=False,default=datetime.now)
    labels = db.Column(db.Text)
    cluster_name = db.Column(db.String(50))
    
class Env(db.Model):
    __tablename__ = 'env'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50),unique=True)
    create_time = db.Column(db.DateTime,nullable=False,default=datetime.now)
    create_user = db.Column(db.String(50))

class Cluster(db.Model):
    __tablename__ = 'cluster'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50),unique=True)
    create_time = db.Column(db.DateTime,nullable=False,default=datetime.now)
    config = db.Column(db.Text)
    # create_user = db.Column(db.String(50))
    
    
