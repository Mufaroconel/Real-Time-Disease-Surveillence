from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, ValidationError, Length, EqualTo
import re


from models import User 

    
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address")
    ])
    
    username = StringField('Username', validators=[
        DataRequired(message="Username is required"),
        Length(min=4, max=20, message="Username must be between 4-20 characters"),
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters"),
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    
    submit = SubmitField('Register')

    def validate_email(self, field):
        """Validate email format and check if already exists"""
        email = field.data
        # Enhanced email regex pattern
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Invalid email address format")
        
        # Check if email exists in database
        if User.query.filter_by(email=email).first():
            raise ValidationError("Email already registered")

    def validate_username(self, field):
        """Validate username format and check if already exists"""
        username = field.data
        # Only allow alphanumeric + underscore
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers and underscores")
        
        # Check if username exists in database
        if User.query.filter_by(username=username).first():
            raise ValidationError("Username already taken")

    def validate_password(self, field):
        """Validate password strength"""
        password = field.data
        # At least one uppercase, one lowercase, one digit
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$', password):
            raise ValidationError(
                "Password must contain at least: " +
                "8 characters, one uppercase, one lowercase, and one number"
            )