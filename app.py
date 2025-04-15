from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin
import pickle
import pandas as pd
import numpy as np
import requests
import pyodbc

app = Flask(__name__)
cors = CORS(app)

# Load the model and data
model = pickle.load(open('LinearRegressionModel.pkl', 'rb'))
car = pd.read_csv('Cleaned_Car_data.csv')

# Azure Function URL to increment page visit count
AZURE_FUNCTION_URL = 'https://counter1645.azurewebsites.net/api/counting?'  # Replace with your Azure Function URL

# Azure SQL Database connection details
DB_SERVER = 'shanky1645.database.windows.net'  # Replace with your server name
DB_DATABASE = 'carPredDb'  # Replace with your database name
DB_USERNAME = 'shankySql'  # Replace with your username
DB_PASSWORD = '2004@NSUT'  # Replace with your password
DB_DRIVER = '{ODBC Driver 17 for SQL Server}'

# Connect to Azure SQL Database
def get_db_connection():
    conn = pyodbc.connect(
        f'DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD}'
    )
    return conn

@app.route('/', methods=['GET', 'POST'])
def index():
    # Call the Azure Function to count page visits
    try:
        response = requests.get(AZURE_FUNCTION_URL)
        visit_count = response.json().get('count', 'Unknown')
    except Exception as e:
        visit_count = 'Error fetching visit count'

    companies = sorted(car['company'].unique())
    car_models = sorted(car['name'].unique())
    year = sorted(car['year'].unique(), reverse=True)
    fuel_type = car['fuel_type'].unique()

    companies.insert(0, 'Select Company')
    return render_template('index.html', companies=companies, car_models=car_models, years=year, fuel_types=fuel_type, visit_count=visit_count)

@app.route('/predict', methods=['POST'])
@cross_origin()
def predict():
    company = request.form.get('company')
    car_model = request.form.get('car_models')
    year = request.form.get('year')
    fuel_type = request.form.get('fuel_type')
    driven = request.form.get('kilo_driven')

    # Make prediction
    prediction = model.predict(pd.DataFrame(columns=['name', 'company', 'year', 'kms_driven', 'fuel_type'],
                                            data=np.array([car_model, company, year, driven, fuel_type]).reshape(1, 5)))
    predicted_price = np.round(prediction[0], 2)

    # Store the query and prediction in Azure SQL Database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO Predictions (company, car_model, year, fuel_type, kms_driven, predicted_price) VALUES (?, ?, ?, ?, ?, ?)"
        cursor.execute(query, company, car_model, year, fuel_type, driven, predicted_price)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error inserting data into Azure SQL Database: {e}")

    return str(predicted_price)

if __name__ == '__main__':
    app.run()
