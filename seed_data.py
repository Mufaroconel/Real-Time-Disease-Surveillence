#!/usr/bin/env python3
"""
Seed Data Script for Disease Surveillance Dashboard

This script populates the SQLite database with realistic sample data
to demonstrate the full functionality of the disease surveillance system.
"""

import random
from datetime import datetime, timedelta, date
from flask import Flask
from models import db, DiseaseRecord

# Initialize Flask app for database context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///disease_surveillance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Sample data for realistic disease records
DISEASES = [
    "Malaria", "Tuberculosis", "Diarrhea", "COVID-19", 
    "Pneumonia", "Cholera", "Typhoid", "Dengue Fever",
    "Hepatitis B", "Influenza"
]

HOSPITALS = [
    "Harare Central Hospital",
    "Parirenyatwa Group of Hospitals", 
    "Chitungwiza Central Hospital",
    "Mpilo Central Hospital",
    "Mutare General Hospital",
    "Gweru Provincial Hospital",
    "Bulawayo Central Hospital"
]

OCCASIONS = ["Newly detected", "Review"]

# Disease prevalence weights (some diseases more common than others)
DISEASE_WEIGHTS = {
    "Malaria": 0.25,
    "Tuberculosis": 0.15,
    "Diarrhea": 0.15,
    "COVID-19": 0.12,
    "Pneumonia": 0.10,
    "Cholera": 0.08,
    "Typhoid": 0.06,
    "Dengue Fever": 0.04,
    "Hepatitis B": 0.03,
    "Influenza": 0.02
}

# Age distribution weights (more cases in certain age groups)
AGE_RANGES = [
    (1, 10, 0.15),    # Children
    (11, 20, 0.12),   # Teens
    (21, 40, 0.35),   # Young adults (highest)
    (41, 60, 0.25),   # Middle age
    (61, 80, 0.13)    # Elderly
]

def weighted_choice(choices, weights):
    """Select a random choice based on weights"""
    return random.choices(choices, weights=weights, k=1)[0]

def generate_weighted_age():
    """Generate age based on realistic age distribution"""
    age_range, weight = random.choices(
        [(r, w) for r, w in [(range_tuple[:2], range_tuple[2]) for range_tuple in AGE_RANGES]],
        weights=[w for _, _, w in AGE_RANGES],
        k=1
    )[0]
    return random.randint(age_range[0], age_range[1])

def generate_sample_data():
    """Generate realistic sample disease records"""
    print("🏥 Generating sample disease surveillance data...")
    
    # Calculate date range (last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    records = []
    total_records = random.randint(80, 120)
    
    # Ensure good distribution across days
    dates_pool = []
    for i in range(30):
        day = start_date + timedelta(days=i)
        # More recent days should have slightly more cases
        weight = 1.0 + (i / 30) * 0.5
        count = max(1, int(total_records * weight / 30 / 1.25))
        dates_pool.extend([day] * count)
    
    # Shuffle and trim to exact count needed
    random.shuffle(dates_pool)
    dates_pool = dates_pool[:total_records]
    
    for i in range(total_records):
        # Select disease based on prevalence
        disease = weighted_choice(
            list(DISEASE_WEIGHTS.keys()),
            list(DISEASE_WEIGHTS.values())
        )
        
        # Select hospital (roughly equal distribution)
        hospital = random.choice(HOSPITALS)
        
        # Select occasion (80% newly detected, 20% review)
        occasion = random.choices(OCCASIONS, weights=[0.8, 0.2], k=1)[0]
        
        # Generate realistic age
        age = generate_weighted_age()
        
        # Use pre-calculated date
        record_date = dates_pool[i] if i < len(dates_pool) else random.choice(dates_pool)
        
        record = DiseaseRecord(
            Patient_Age=age,
            Disease_Name=disease,
            Occasion=occasion,
            Date=record_date,
            Hospital_Name=hospital
        )
        
        records.append(record)
    
    return records

def seed_database():
    """Populate database with sample data"""
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Clear existing disease records (keep users)
            print("🗑️  Clearing existing disease records...")
            DiseaseRecord.query.delete()
            db.session.commit()
            
            # Generate and insert sample data
            records = generate_sample_data()
            
            print(f"📊 Inserting {len(records)} sample records...")
            for record in records:
                db.session.add(record)
            
            db.session.commit()
            
            # Print summary statistics
            print("\n✅ Database seeded successfully!")
            print("\n📈 Data Summary:")
            print(f"   • Total Records: {len(records)}")
            
            # Disease distribution
            disease_counts = {}
            for record in records:
                disease_counts[record.Disease_Name] = disease_counts.get(record.Disease_Name, 0) + 1
            
            print("\n🦠 Disease Distribution:")
            for disease, count in sorted(disease_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {disease}: {count} cases")
            
            # Hospital distribution
            hospital_counts = {}
            for record in records:
                hospital_counts[record.Hospital_Name] = hospital_counts.get(record.Hospital_Name, 0) + 1
            
            print("\n🏥 Hospital Distribution:")
            for hospital, count in sorted(hospital_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {hospital}: {count} cases")
            
            # Recent activity (last 7 days)
            recent_date = datetime.now().date() - timedelta(days=7)
            recent_records = [r for r in records if r.Date >= recent_date]
            newly_detected = [r for r in recent_records if r.Occasion == "Newly detected"]
            
            print(f"\n📅 Recent Activity (Last 7 days):")
            print(f"   • Total Cases: {len(recent_records)}")
            print(f"   • Newly Detected: {len(newly_detected)}")
            print(f"   • Review Cases: {len(recent_records) - len(newly_detected)}")
            
            print("\n🎯 Dashboard Ready!")
            print("   Run 'python app.py' to view the populated dashboard")
            
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    print("🌱 Disease Surveillance Database Seeder")
    print("=" * 50)
    seed_database()
