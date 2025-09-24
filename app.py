from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import json
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
import re
import folium
import matplotlib.pyplot as plt
import seaborn as sns
from flask import send_from_directory
from models import db
from io import BytesIO
from werkzeug.utils import secure_filename
import time
import threading
import webbrowser
from datetime import datetime, timedelta
from models import db, User, DiseaseRecord
from forms import  RegistrationForm 
import time
from flask import make_response
from openpyxl import Workbook, load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import io
from sqlalchemy import func




app = Flask(__name__)
app.secret_key = 'your_secret_key'  # secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///disease_surveillance.db'  # Database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create the database tables
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

@app.route('/')
def index():
    return render_template('index.html')

def open_browser():
    # Wait for the server to start
    time.sleep(1)  # Adjust sleep time if necessary
    webbrowser.open_new('http://127.0.0.1:5000/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Checking if user exists and password matches
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Use hashed passwords in production
            session['username'] = username
            return redirect(url_for('home'))  # Redirect to home
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        
        new_user = User(
            email=form.email.data,
            username=form.username.data,
            password=form.password.data  # Hash this in production!
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    
    return render_template('register.html', form=form)


# Getting available hospitals and occasions
def get_hospitals_and_occurrences():
    hospitals = [
        "Harare Central Hospital",
        "Parirenyatwa Group of Hospitals", 
        "Chitungwiza Central Hospital",
        "Mpilo Central Hospital",
        "Mutare General Hospital",
        "Gweru Provincial Hospital",
        "Bulawayo Central Hospital"
    ]
    occasions = ['Newly detected', 'Review']
    return hospitals, occasions

@app.route('/home')
def home():
    # Calculating the date range for the last seven days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    # Loading data for the last seven days for most frequent diseases (limit 5)
    most_frequent_diseases_query = db.session.query(
        DiseaseRecord.Disease_Name,
        func.count(DiseaseRecord.id).label('Case_Count')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date)
    ).group_by(DiseaseRecord.Disease_Name).order_by(
        func.count(DiseaseRecord.id).desc()
    ).limit(5)
    
    most_frequent_diseases = pd.read_sql(most_frequent_diseases_query.statement, db.engine)

    # Loading hospital admission trends (newly detected diseases) for the last seven days  
    admission_trends_query = db.session.query(
        DiseaseRecord.Date,
        func.count(DiseaseRecord.id).label('New_Cases')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date),
        DiseaseRecord.Occasion == 'Newly detected'
    ).group_by(DiseaseRecord.Date).order_by(DiseaseRecord.Date)
    
    admission_trends = pd.read_sql(admission_trends_query.statement, db.engine)

    # Loading analysis of newly detected and review cases
    new_cases_query = db.session.query(
        DiseaseRecord.Occasion,
        func.count(DiseaseRecord.id).label('Case_Count')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date)
    ).group_by(DiseaseRecord.Occasion)
    
    new_cases_analysis = pd.read_sql(new_cases_query.statement, db.engine)

    
    new_cases_count = new_cases_analysis.loc[new_cases_analysis['Occasion'] == 'Newly detected', 'Case_Count'].sum() if not new_cases_analysis.empty else 0
    review_cases_count = new_cases_analysis.loc[new_cases_analysis['Occasion'] == 'Review', 'Case_Count'].sum() if not new_cases_analysis.empty else 0

    return render_template('home.html',
                       most_frequent_diseases=most_frequent_diseases,
                       admission_trends=admission_trends,
                       new_cases_analysis=new_cases_analysis,
                       new_cases_count=new_cases_count,
                       review_cases_count=review_cases_count,
                       start_date=start_date.strftime('%Y-%m-%d'),
                       end_date=end_date.strftime('%Y-%m-%d'))

@app.route('/surveillance-map', methods=['GET', 'POST'])
def surveillance_map():
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3)

    disease_query = db.session.query(
        DiseaseRecord.Hospital_Name,
        DiseaseRecord.Disease_Name,
        func.count(DiseaseRecord.id).label('Case_Count')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date)
    ).group_by(DiseaseRecord.Hospital_Name, DiseaseRecord.Disease_Name)
    
    df = pd.read_sql(disease_query.statement, db.engine)

    
    total_cases_by_hospital = df.groupby('Hospital_Name')['Case_Count'].sum().reset_index()

    risk_levels = {}
    for _, row in total_cases_by_hospital.iterrows():
        if row['Case_Count'] <= 5:
            risk_levels[row['Hospital_Name']] = 'Low'
        elif 5 < row['Case_Count'] <= 10:
            risk_levels[row['Hospital_Name']] = 'Medium'
        else:
            risk_levels[row['Hospital_Name']] = 'High'

    # coordinates for Zimbabwe center (roughly between major cities)
    zimbabwe_center = (-19.0154, 29.1549)

    
    disease_map = folium.Map(location=zimbabwe_center, zoom_start=7)

    
    relevant_hospitals = {
        "Harare Central Hospital": {"latitude": -17.8216, "longitude": 31.0492},
        "Parirenyatwa Group of Hospitals": {"latitude": -17.7840, "longitude": 31.0456}, 
        "Chitungwiza Central Hospital": {"latitude": -18.0130, "longitude": 31.0776},
        "Mpilo Central Hospital": {"latitude": -20.1619, "longitude": 28.5906},
        "Mutare General Hospital": {"latitude": -18.9707, "longitude": 32.6731},
        "Gweru Provincial Hospital": {"latitude": -19.4620, "longitude": 29.8301},
        "Bulawayo Central Hospital": {"latitude": -20.1505, "longitude": 28.5665}
    }

   
    for hospital_name, location in relevant_hospitals.items():
        total_cases = total_cases_by_hospital.loc[total_cases_by_hospital['Hospital_Name'] == hospital_name, 'Case_Count']
        total_cases = total_cases.iloc[0] if not total_cases.empty else 0
        risk = risk_levels.get(hospital_name, 'Low')

        folium.Marker(
            location=[location['latitude'], location['longitude']],
            popup=f"{hospital_name}: {total_cases} cases (Risk: {risk})",
            icon=folium.Icon(color='blue' if risk == 'Low' else 'orange' if risk == 'Medium' else 'red')
        ).add_to(disease_map)

    map_html = disease_map._repr_html_()

    return render_template('map.html', map_html=map_html)

@app.route('/disease-database', methods=['GET', 'POST'])
def disease_database():
    hospitals, occasions = get_hospitals_and_occurrences()
    
    if request.method == 'POST':
        patient_age = request.form['patient_age']
        disease_name = request.form['disease_name']
        occasion = request.form['occasion']
        date = request.form['date']
        hospital_name = request.form['hospital_name']
        
        # Inserting data into the database
        try:
            # Convert date string to date object if needed
            from datetime import datetime
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            
            new_record = DiseaseRecord(
                Patient_Age=int(patient_age),
                Disease_Name=disease_name,
                Occasion=occasion,
                Date=date,
                Hospital_Name=hospital_name
            )
            db.session.add(new_record)
            db.session.commit()
            flash('Record added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error occurred: {e}', 'danger')
        
        return redirect(url_for('disease_database'))

    return render_template('disease_database.html', hospitals=hospitals, occasions=occasions)


@app.route('/prediction-trends', methods=['GET', 'POST'])
def prediction_trends():
    prediction_query = db.session.query(
        DiseaseRecord.Patient_Age,
        DiseaseRecord.Disease_Name,
        DiseaseRecord.Occasion
    )
    df = pd.read_sql(prediction_query.statement, db.engine)

    # Check if we have enough data for predictions
    if df.empty or len(df) < 5:
        # Return empty results if not enough data
        results_df = pd.DataFrame(columns=['Disease_Name', 'Count', 'Risk_Status'])
        results_list = []
    else:
        le_disease = LabelEncoder()
        le_occasion = LabelEncoder()
        
        df['Disease_Name'] = le_disease.fit_transform(df['Disease_Name'])
        df['Occasion'] = le_occasion.fit_transform(df['Occasion'])

        # Preparing features and target
        X = df[['Patient_Age', 'Occasion']]
        y = df['Disease_Name']

        # Use smaller test_size for small datasets or skip train_test_split
        if len(df) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            # Use all data for training and testing with small datasets
            X_train = X_test = X
            y_train = y_test = y

        # Train a Decision Tree model
        model = DecisionTreeClassifier()
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        predictions_decoded = le_disease.inverse_transform(predictions)

        disease_counts = pd.Series(predictions_decoded).value_counts()
        
        results_df = pd.DataFrame({
            'Disease_Name': disease_counts.index,
            'Count': disease_counts.values
        })

        # Applying risk status threshold
        def risk_status(count):
            if count <= 5:
                return 'Low'
            elif 6 <= count <= 10:
                return 'Medium'
            else:
                return 'High'

        results_df['Risk_Status'] = results_df['Count'].apply(risk_status)

        # Converting results to a list of dictionaries for rendering
        results_list = results_df.to_dict(orient='records')

    if request.method == 'POST':
        format_type = request.form.get('format')
        if format_type == 'excel':
            return generate_excel_response(results_df, 'prediction_results.xlsx')
        elif format_type == 'pdf':
            return generate_pdf_response(results_df, 'prediction_results.pdf')

    return render_template('predictions.html', results=results_list)

def generate_excel_response(dataframe, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Predictions')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

def generate_pdf_response(dataframe, filename):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []

    data = [dataframe.columns.tolist()] + dataframe.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=filename)
    


hospitals = {
    "Harare Central Hospital": {"latitude": -17.8216, "longitude": 31.0492},
    "Parirenyatwa Group of Hospitals": {"latitude": -17.7840, "longitude": 31.0456}, 
    "Chitungwiza Central Hospital": {"latitude": -18.0130, "longitude": 31.0776},
    "Mpilo Central Hospital": {"latitude": -20.1619, "longitude": 28.5906},
    "Mutare General Hospital": {"latitude": -18.9707, "longitude": 32.6731},
    "Gweru Provincial Hospital": {"latitude": -19.4620, "longitude": 29.8301},
    "Bulawayo Central Hospital": {"latitude": -20.1505, "longitude": 28.5665}
}

@app.route('/disease-surveillance', methods=['GET', 'POST'])
def disease_surveillance():
    # Calculating the date range for the last three days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3)

    # Loading data for the last three days, grouped by hospital
    surveillance_query = db.session.query(
        DiseaseRecord.Hospital_Name,
        DiseaseRecord.Disease_Name,
        func.count(DiseaseRecord.id).label('Case_Count')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date)
    ).group_by(DiseaseRecord.Hospital_Name, DiseaseRecord.Disease_Name)
    
    df = pd.read_sql(surveillance_query.statement, db.engine)

  
    selected_hospital = request.form.get('hospital')

    
    if selected_hospital:
        df = df[df['Hospital_Name'] == selected_hospital]

    
    total_cases_by_hospital = df.groupby('Hospital_Name')['Case_Count'].sum().reset_index()

    
    risk_levels = {}
    for _, row in total_cases_by_hospital.iterrows():
        if row['Case_Count'] <= 5:
            risk_levels[row['Hospital_Name']] = 'Low'
        elif 5 < row['Case_Count'] <= 10:
            risk_levels[row['Hospital_Name']] = 'Medium'
        else:
            risk_levels[row['Hospital_Name']] = 'High'

    
    top_diseases = df.loc[df.groupby('Hospital_Name')['Case_Count'].idxmax()].set_index('Hospital_Name')['Disease_Name'].to_dict()

    
    disease_counts = df.pivot(index='Disease_Name', columns='Hospital_Name', values='Case_Count').fillna(0)

   
    for hospital in hospitals.keys():
        if hospital not in disease_counts.columns:
            disease_counts[hospital] = 0

    
    disease_counts = disease_counts.reindex(columns=hospitals.keys(), fill_value=0)

    
    if selected_hospital:
        location = hospitals[selected_hospital]
        disease_map = folium.Map(location=[location['latitude'], location['longitude']], zoom_start=12)
        
        # Get case count for selected hospital safely
        hospital_cases = total_cases_by_hospital.loc[total_cases_by_hospital['Hospital_Name'] == selected_hospital, 'Case_Count']
        case_count = hospital_cases.iloc[0] if not hospital_cases.empty else 0
        hospital_risk = risk_levels.get(selected_hospital, 'Low')
        
        folium.Marker(
            location=[location['latitude'], location['longitude']],
            popup=f"{selected_hospital}: {case_count} cases (Risk: {hospital_risk})",
            icon=folium.Icon(color='blue' if hospital_risk == 'Low' else 'orange' if hospital_risk == 'Medium' else 'red')
        ).add_to(disease_map)
    else:
        initial_hospital = list(hospitals.values())[0]
        disease_map = folium.Map(location=[initial_hospital['latitude'], initial_hospital['longitude']], zoom_start=12)
        
        for hospital_name, location in hospitals.items():
            total_cases = total_cases_by_hospital.loc[total_cases_by_hospital['Hospital_Name'] == hospital_name, 'Case_Count']
            total_cases = total_cases.iloc[0] if not total_cases.empty else 0
            risk = risk_levels.get(hospital_name, 'Low')
            folium.Marker(
                location=[location['latitude'], location['longitude']],
                popup=f"{hospital_name}: {total_cases} cases (Risk: {risk})",
                icon=folium.Icon(color='blue' if risk == 'Low' else 'orange' if risk == 'Medium' else 'red')
            ).add_to(disease_map)

    
    map_html = disease_map._repr_html_()

    return render_template('disease_surveillance.html',
                           disease_counts=disease_counts,
                           total_cases_by_hospital=total_cases_by_hospital,
                           risk_levels=risk_levels,
                           top_diseases=top_diseases,
                           map_html=map_html,
                           hospitals=hospitals.keys(),
                           selected_hospital=selected_hospital)



@app.route('/outbreak-progression', methods=['GET', 'POST'])
def outbreak_progression():
    
    current_date = datetime.now().date()
    last_three_days = current_date - timedelta(days=3)
    
    # Query database using SQLAlchemy
    outbreak_query = db.session.query(
        DiseaseRecord.Disease_Name,
        DiseaseRecord.Patient_Age,
        DiseaseRecord.Date
    ).filter(
        DiseaseRecord.Date.between(last_three_days, current_date)
    )
    
    df = pd.read_sql(outbreak_query.statement, db.engine)
    
    # Calculating most frequent diseases for last 3 days
    most_frequent_diseases = df['Disease_Name'].value_counts()
    
    warnings = []
    seasonal_patterns = None
    age_risk_analysis = None
    
    if request.method == 'POST':
        
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Loading data from the database within the specified date range
        extended_query = db.session.query(
            DiseaseRecord.Disease_Name,
            DiseaseRecord.Patient_Age,
            DiseaseRecord.Date
        ).filter(
            DiseaseRecord.Date.between(start_date, end_date)
        )
        df = pd.read_sql(extended_query.statement, db.engine)        
        disease_counts = df['Disease_Name'].value_counts()
        
        for disease in disease_counts.index:
            daily_counts = df[df['Disease_Name'] == disease]['Date'].value_counts().sort_index()
            if len(daily_counts) > 1:  
                for i in range(1, len(daily_counts)):
                    if daily_counts.iloc[i] >= 1.2 * daily_counts.iloc[i - 1]:
                        warnings.append(f"Warning: 5% increase in {disease} cases on {daily_counts.index[i]}")

        # Seasonal disease patterns analysis
        df['Month'] = pd.to_datetime(df['Date']).dt.month.astype(int)
        seasonal_patterns = df.groupby(['Month', 'Disease_Name']).size().unstack(fill_value=0)

        # Age-based risk analysis
        df['Age_Group'] = pd.cut(df['Patient_Age'], bins=[0, 18, 35, 50, 65, 100], 
                               labels=['0-18', '19-35', '36-50', '51-65', '66+'], right=False)
        age_risk_analysis = df.groupby(['Age_Group', 'Disease_Name']).size().unstack(fill_value=0)
    
    return render_template('outbreak_progression.html', 
                         most_frequent_diseases=most_frequent_diseases,
                         warnings=warnings,
                         seasonal_patterns=seasonal_patterns,
                         age_risk_analysis=age_risk_analysis,
                         current_date=current_date,
                         last_three_days=last_three_days)
    
@app.route('/download-frequent-diseases', methods=['POST'])
def download_frequent_diseases():
    # Get data from last 3 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3)
    
    frequent_diseases_query = db.session.query(
        DiseaseRecord.Disease_Name,
        func.count(DiseaseRecord.id).label('Case_Count')
    ).filter(
        DiseaseRecord.Date.between(start_date, end_date)
    ).group_by(DiseaseRecord.Disease_Name)
    
    df = pd.read_sql(frequent_diseases_query.statement, db.engine)

    format_type = request.form.get('format')
    if format_type == 'excel':
        return generate_excel_response(df, 'most_frequent_diseases.xlsx')
    elif format_type == 'pdf':
        return generate_pdf_response(df, 'most_frequent_diseases.pdf')

@app.route('/download-age-risk-analysis', methods=['POST'])
def download_age_risk_analysis():
    # Fetching age-based risk analysis data
    age_risk_query = db.session.query(
        DiseaseRecord.Patient_Age,
        DiseaseRecord.Disease_Name
    )
    
    df = pd.read_sql(age_risk_query.statement, db.engine)

    # Age-based risk analysis
    df['Age_Group'] = pd.cut(df['Patient_Age'], bins=[0, 18, 35, 50, 65, 100], 
                             labels=['0-18', '19-35', '36-50', '51-65', '66+'], right=False)
    age_risk_analysis = df.groupby(['Age_Group', 'Disease_Name']).size().unstack(fill_value=0)

    format_type = request.form.get('format')
    if format_type == 'excel':
        return generate_excel_response(age_risk_analysis, 'age_risk_analysis.xlsx')
    elif format_type == 'pdf':
        return generate_pdf_response(age_risk_analysis, 'age_risk_analysis.pdf')

def generate_excel_response(dataframe, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=True, sheet_name='Report')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

def generate_pdf_response(dataframe, filename):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []

    data = [dataframe.index.tolist()] + dataframe.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=filename)
    


@app.route('/reports-analytics', methods=['GET', 'POST'])
def reports_analytics():
    if request.method == 'POST':
        occasion = request.form.get('occasion')
        format_type = request.form.get('format')

        if occasion and format_type:
            if occasion == 'all':
                return download_all_diseases_report(format_type)
            else:
                return download_disease_report(occasion, format_type)

    return render_template('reports_analytics.html')

def download_disease_report(occasion, format_type):
    report_query = db.session.query(DiseaseRecord).filter(
        DiseaseRecord.Occasion == occasion
    )
    
    report_data = pd.read_sql(report_query.statement, db.engine)

    if format_type == 'excel':
        return generate_excel_response(report_data, f'disease_report_{occasion}.xlsx')
    elif format_type == 'pdf':
        return generate_pdf_response(report_data, f'disease_report_{occasion}.pdf')

def download_all_diseases_report(format_type):
    all_diseases_query = db.session.query(DiseaseRecord)
    
    report_data = pd.read_sql(all_diseases_query.statement, db.engine)

    if format_type == 'excel':
        return generate_excel_response(report_data, 'all_diseases_report.xlsx')
    elif format_type == 'pdf':
        return generate_pdf_response(report_data, 'all_diseases_report.pdf')

def generate_excel_response(dataframe, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

def generate_pdf_response(dataframe, filename):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []

    data = [dataframe.columns.tolist()] + dataframe.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=filename)

    
@app.route('/recommendations')
def recommendations():
    recommendations = [
        "Encourage individuals to undergo regular health screenings to detect potential health issues early.",
        "Promote awareness about how diseases are transmitted and the importance of safe practices to prevent infections.",
        "Facilitate support groups and mental health resources to help individuals cope with health-related challenges.",
        "Advocate for good hygiene practices, such as frequent handwashing with soap and the use of sanitizers.",
        "Ensure communities have access to clean drinking water and advocate for proper sanitation facilities.",
        "Highlight the importance of vaccinations and encourage individuals to stay up to date with their immunizations.",
        "Educate the public on common symptoms of illnesses and the importance of seeking medical attention promptly.",
        "Organize community events to eliminate breeding sites for diseases, such as standing water and waste accumulation.",
        "Promote healthy lifestyle choices, including a balanced diet, regular exercise, and avoiding harmful substances.",
        "Develop community plans for responding to outbreaks, including communication strategies and resource allocation."
    ]

    return render_template('recommendations.html', recommendations=recommendations)
   

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Start the browser in a separate thread
    threading.Thread(target=open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)