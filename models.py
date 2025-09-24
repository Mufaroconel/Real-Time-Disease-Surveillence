from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class DiseaseRecord(db.Model):
    __tablename__ = 'DiseaseRecords'
    
    id = db.Column(db.Integer, primary_key=True)
    Patient_Age = db.Column('Patient_Age', db.Integer, nullable=False)
    Disease_Name = db.Column('Disease_Name', db.String(200), nullable=False)
    Occasion = db.Column('Occasion', db.String(50), nullable=False)
    Date = db.Column('Date', db.Date, nullable=False)
    Hospital_Name = db.Column('Hospital_Name', db.String(200), nullable=False)
    
    def __repr__(self):
        return f'<DiseaseRecord {self.Disease_Name} at {self.Hospital_Name}>'






