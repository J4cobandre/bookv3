from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import case
import requests
import json
import time
from sqlalchemy.exc import OperationalError, SQLAlchemyError

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_ynj3laFAPM7Y@ep-shy-heart-a562hdfj-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def get_pcp_change_form_link(insurance):
    """
    Retrieve PCP change form link based on insurance provider
    """
    pcp_form_links = {
    "Aetna": "https://drive.google.com/file/d/1h-VkDlIw8tljeHP3djHuoz-mYz5JbTmP/view?usp=drive_link",
    "BC Empire": "https://drive.google.com/file/d/1M8HhUOm5rXpOdkzns_ZVKN9TzDuOnI-c/view?usp=drive_link",
    "BCBS Empire": "https://drive.google.com/file/d/1M8HhUOm5rXpOdkzns_ZVKN9TzDuOnI-c/view?usp=drive_link",
    "Elder Plan": "https://drive.google.com/file/d/1YYqHn22xvViGqsSPZteoRbnQEHoNhVel/view?usp=drive_link",
    "Fidelis": "https://drive.google.com/file/d/1-K2tLlgklynhSvj3bFra387_amNMYCBu/view?usp=drive_link",
    "Healthfirst Medicaid": "https://drive.google.com/file/d/1anV3flfC1-fPXTHK-YwYIM0FRAnTGdCo/view?usp=sharing",
    "Healthfirst Medicare": "https://drive.google.com/file/d/1anV3flfC1-fPXTHK-YwYIM0FRAnTGdCo/view?usp=sharing",
    "Healthfirst Other LOB": "https://drive.google.com/file/d/1anV3flfC1-fPXTHK-YwYIM0FRAnTGdCo/view?usp=sharing",
    "Humana": "https://drive.google.com/file/d/1kykVPXr0GCVPDFRmdN7g9DsO7fqn1H6b/view?usp=drive_link",
    "Medicare": "https://drive.google.com/file/d/1uVLcqNum148eJkyO35BfoyiJB46esxt9/view?usp=drive_link",
    "Oxford":"https://drive.google.com/file/d/123sT5gr6wGg0xCTAnEFbKzWW5FAFe461/view?usp=drive_link",
    "UHC Medicare": "https://drive.google.com/file/d/123sT5gr6wGg0xCTAnEFbKzWW5FAFe461/view?usp=drive_link",
    "UHC Medicaid NY": "https://drive.google.com/file/d/123sT5gr6wGg0xCTAnEFbKzWW5FAFe461/view?usp=drive_link",
    "UHC other LOB": "https://drive.google.com/file/d/123sT5gr6wGg0xCTAnEFbKzWW5FAFe461/view?usp=drive_link",
    "Wellcare": "https://drive.google.com/file/d/1arW5qNXjRAZJ7kBcPCXYOAZFXbHCnywk/view?usp=drive_link"
    }
    
    # Normalize insurance name and get link, with fallback
    return pcp_form_links.get(insurance, "https://drive.google.com/drive/folders/1b6f6xpUJVAdRU6wXuqQJqGXWiPuWIWtZ?usp=drive_link")

def normalize_location(location):
    """Normalize location names for consistent matching."""
    if not location:
        return location
    
    location = location.upper().strip()
    location_mapping = {
        'NEW YORK': 'Manhattan',
        'BRONX': 'BX174',
        'BROOKLYN': 'Crown Heights',
        'LIC': 'Long Island City',
        'CH': 'Crown Heights',
        'JH': 'Jackson Heights',
        'CROWNHEIGHTS': 'Crown Heights'
    }
    return location_mapping.get(location, location)

# Provider model remains the same
class Provider(db.Model):
    __tablename__ = 'providers'
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(128), nullable=False)
    npi = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(64), nullable=False)
    insurance = db.Column(db.String(64), nullable=False)
    pcp_change_requirement = db.Column(db.String(256), nullable=True)
    hfmc_contract = db.Column(db.Boolean, nullable=False)
    status = db.Column(db.String(256), nullable=False)

# Add a function to handle database retries
def query_with_retry(query_func, max_retries=3, retry_delay=1):
    """
    Execute a database query with retry logic for handling connection issues.
    
    Args:
        query_func: Function that performs the actual database query
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        The result of the query function or raises the last exception
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return query_func()
        except (OperationalError, SQLAlchemyError) as e:
            last_error = e
            print(f"Database error on attempt {attempt+1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for next attempt
                retry_delay *= 2
    
    # If we get here, all retries failed
    raise last_error

# Route to serve the HTML form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle the logic for location and insurance
@app.route('/test', methods=['GET'])
def get_provider_options():
    # Normalize the input location
    location = normalize_location(request.args.get('location', ''))
    insurance = request.args.get('insurance', '')
    is_under_18 = request.args.get('isUnder18', 'false').lower() == 'true'  # Convert to boolean
    is_follow_up = request.args.get('isFollowUp', 'false').lower() == 'true'  # Convert to boolean

    if not location or not insurance:
        return jsonify({"error": "Both location and insurance are required!"})
    print(f"Querying with location: {location}, insurance: {insurance}")

    providers = None
    # Define the priority order for providers
    priority_1 = [
        "Priti Jain", "Sandeep Jain", "Dayakishan Chahal", "Michael Ihemaguba","Mansoor Farooki", 
        "Abel Infante", "Fazle Showon", "Barbara Phillips-Cole", "Rakesh Koul", 
    ]
    priority_2 = [
        "Rosetta Romero-Williams", "Shelly Twito", "Suraiya Chowdhury", 
        "Nickecha Redway", "Rainier Chirinos", "Mark Basaritmand", "Suresh Sagar"
    ]

    # Create a case statement for ordering
    order_case = case(
        *[
            (Provider.provider_name == name, i) for i, name in enumerate(priority_1, start=1)
        ] + [
            (Provider.provider_name == name, i + len(priority_1)) for i, name in enumerate(priority_2, start=1)
        ],
        else_=len(priority_1) + len(priority_2) + 1
    )
    
    # Wrap the database query in the retry function
    try:
        if location.upper() in ["PSYCH", "NUTRITION", "TELEVISIT"]:
            def query_func():
                return Provider.query.filter(
                    db.func.upper(Provider.location) == location.upper(),
                    db.func.upper(Provider.insurance) == insurance.upper()
                ).order_by(order_case).all()
            
            providers = query_with_retry(query_func)
        else:
            def query_func():
                return Provider.query.filter(
                    db.func.upper(Provider.location).in_([location.upper(), "ALL"]),
                    db.func.upper(Provider.insurance) == insurance.upper()
                ).order_by(order_case).all()
            
            providers = query_with_retry(query_func)
    except Exception as e:
        print(f"Failed to query database after retries: {str(e)}")
        return jsonify({"error": "Database connection error. Please try again in a moment."})

    # Debugging information
    print(f"Location: {location}")
    print(f"Insurance: {insurance}")
    print(f"Providers found: {len(providers) if providers else 0}")
    if providers:
        for provider in providers:
            print(f"Provider: {provider.provider_name}, Location: {provider.location}, Insurance: {provider.insurance}")

    if not providers:
        return jsonify({"error": "No Providers Available. Please book this appointment with Statcare Urgent Care."})

    # Existing logic for constructing the response remains the same
    out_of_contract = not providers[0].hfmc_contract

    if is_under_18:
        facility_message = "Patients under 18 should be seen under Statcare Urgent Care."
        facilities = ["SCUC"]
        response = {
            "facility_options": {
                "facilities": facilities,
                "message": facility_message
            },
            "provider_options": [
                {"name": provider.provider_name, "npi": provider.npi}
                for provider in providers
            ]
        }
        print("Returning response for under 18:", response)
        return jsonify(response)  # Do not include PCP Change Requirement or Form
        
    if out_of_contract:
        # Check if it's a follow-up with out-of-contract insurance
        if is_follow_up:
            facility_message = "You can only visit Statcare Urgent Care."
            facilities = ["SCUC"]
        else:
            facility_message = "You can only visit Statcare Urgent Care."
            facilities = ["SCUC"]
        
        # Build response without PCP Change Requirement
        response = {
            "facility_options": {
                "facilities": facilities,
                "message": facility_message
            },
            "provider_options": [
                {"name": provider.provider_name, "npi": provider.npi}
                for provider in providers
            ],
            "feedback_link": "https://forms.gle/ME2mKmVALXh4iDKWA"
        }
        print("Final Response for out-of-contract insurance:", response)
        return jsonify(response)
    elif is_follow_up:
        facility_message = (
            "<div>"
            "<p>For follow-up appointments:</p>"
            "<ul>"
            "<li>Preferably book the appointment under Hicksville Family Medical Care, but the patient must understand and agree that their primary care provider (PCP) needs to be changed.</li>"
            "<li>If the patient disagrees, they can only visit Statcare Urgent Care.</li>"
            "</ul>"
            "</div>"
        )
        facilities = ["HFMC"]
    else:
        facility_message = (
            "Schedule with Hicksville Family Medical Care, (Statcare Urgent Care is available for same day appointments only)."
        )
        facilities = ["HFMC", "SCUC"]

    response = {
        "facility_options": {
            "facilities": facilities,
            "message": facility_message
        },
        "pcp_change_requirement": {
            "details": providers[0].pcp_change_requirement or "No PCP change requirement.",
            "required": bool(providers[0].pcp_change_requirement),
            "additional_info": "Ensure you submit the PCP Change Form before visiting.",
            "form_link": get_pcp_change_form_link(insurance) if providers[0].pcp_change_requirement.strip() in [
                "Insurance has PCP Change Form",
                "Insurance has PCP Change Form.",
                "Medicare requires submission of Voluntary Alignment and SDoH Forms.",
            ] else None,
            "requires_phone": providers[0].pcp_change_requirement.strip() in [
                "Insurance has PCP Change Form",
                "Insurance has PCP Change Form.",
            ]
        },
        "provider_options": [
            {"name": provider.provider_name, "npi": provider.npi}
            for provider in providers
        ],
        "feedback_link": "https://forms.gle/ME2mKmVALXh4iDKWA"
    }
    print("Final Response:", response) 
    return jsonify(response)

@app.route('/submit-phone', methods=['POST'])
def submit_phone():
    phone = request.json.get('phone')
    insurance = request.json.get('insurance')
    
    if not phone or not insurance:
        return jsonify({"error": "Phone number and insurance are required"}), 400

    def send_sms(phone_number):
        url = "https://us-central1-care-plan-beta.cloudfunctions.net/nao-communications/send-message"
        
        payload = {
            "phoneNum": phone_number,
            "smsText": "Hi, this is Nao Medical.\n\nTo ensure that your visit with our Primary Care Provider (PCP) is properly covered by your insurance, we kindly ask that you elect Nao Medical as your PCP, which you can easily do at the link below. If you do not complete this process, we will not be able to complete your visit.\n\nPCP Change Portal: https://checkin.naomedical.com"
        }
        
        try:
            response = requests.request("POST", url, headers={}, data=json.dumps(payload, default=str))
            return {
                'status_code': response.status_code,
                'message': response.text,
                'success': response.status_code == 200
            }
        except Exception as e:
            return {
                'status_code': 500,
                'message': str(e),
                'success': False
            }

    # Send the SMS
    result = send_sms(phone)
    
    if result['success']:
        return jsonify({
            "message": "Text message sent successfully",
            "phone": phone,
            "insurance": insurance
        })
    else:
        return jsonify({
            "error": f"Failed to send text message: {result['message']}"
        }), result['status_code']

if __name__ == '__main__':
    app.run(debug=True)
