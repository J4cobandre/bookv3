from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import case

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///par_log.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def get_pcp_change_form_link(insurance):
    """
    Retrieve PCP change form link based on insurance provider
    """
    pcp_form_links = {
    "Aetna": "https://drive.google.com/file/d/1E-t1kXgILxWG2lsrLJXUyXyo2eh_k7CX/view?usp=drive_link",
    "BC Empire": "https://drive.google.com/file/d/1YaI9ZJPTeLjJSnlB1sftb8RKN48kcUWb/view?usp=drive_link",
    "BCBS Empire": "https://drive.google.com/file/d/1YaI9ZJPTeLjJSnlB1sftb8RKN48kcUWb/view?usp=drive_link",
    "Elder Plan": "https://drive.google.com/file/d/1YYqHn22xvViGqsSPZteoRbnQEHoNhVel/view?usp=drive_link",
    "Fidelis": "https://drive.google.com/file/d/1-K2tLlgklynhSvj3bFra387_amNMYCBu/view?usp=drive_link",
    "Healthfirst Medicaid": "https://drive.google.com/file/d/1QaT8J6j0ZyGascS-NN8ADOJC419mnEi6/view?usp=drive_link",
    "Healthfirst Medicare": "https://drive.google.com/file/d/1QaT8J6j0ZyGascS-NN8ADOJC419mnEi6/view?usp=drive_link",
    "Healthfirst Other LOB": "https://drive.google.com/file/d/1QaT8J6j0ZyGascS-NN8ADOJC419mnEi6/view?usp=drive_link",
    "Humana": "https://drive.google.com/file/d/19oM7dToudm-J-MwZmWa6VOyEPIOlI4jW/view?usp=drive_link",
    "Medicare": "https://drive.google.com/file/d/1uVLcqNum148eJkyO35BfoyiJB46esxt9/view?usp=drive_link",
    "UHC Medicare": "https://drive.google.com/file/d/1RjmXRj2Bs0fJ_NSYeSNdWH8V6c8M0VNC/view?usp=drive_link",
    "UHC Medicaid NY": "https://drive.google.com/file/d/1RjmXRj2Bs0fJ_NSYeSNdWH8V6c8M0VNC/view?usp=drive_link",
    "UHC other LOB": "https://drive.google.com/file/d/1RjmXRj2Bs0fJ_NSYeSNdWH8V6c8M0VNC/view?usp=drive_link",
    "Wellcare": "https://drive.google.com/file/d/1Ue0-Sn21smGaens7RzavXowVIzq3SEak/view?usp=drive_link"
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
        "Priti Jain", "Sandeep Jain", "Dayakishan Chahal", "Mansoor Farooki", 
        "Abel Infante", "Fazle Showon", "Barbara Phillips-Cole", "Rakesh Koul"
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
    # Query the providers with order by priority
    if location.upper() in ["PSYCH", "NUTRITION", "TELEVISIT"]:
        providers = Provider.query.filter(
            db.func.upper(Provider.location) == location.upper(),
            db.func.upper(Provider.insurance) == insurance.upper()
        ).order_by(order_case).all()
    else:
        providers = Provider.query.filter(
            db.func.upper(Provider.location).in_([location.upper(), "ALL"]),
            db.func.upper(Provider.insurance) == insurance.upper()
        ).order_by(order_case).all()

    # Debugging information
    print(f"Location: {location}")
    print(f"Insurance: {insurance}")
    print(f"Providers found: {len(providers)}")
    for provider in providers:
        print(f"Provider: {provider.provider_name}, Location: {provider.location}, Insurance: {provider.insurance}")

    if not providers:
        return jsonify({"error": "No Providers Available. Please book this appointment with SCUC."})

    # Existing logic for constructing the response remains the same
    out_of_contract = not providers[0].hfmc_contract

    if is_under_18:
        facility_message = "Patients under 18 should be seen under SCUC (Urgent Care)."
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
            facility_message = "You can only visit SCUC."
            facilities = ["SCUC"]
        else:
            facility_message = "You can only visit SCUC."
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
            "<li>Preferably book the appointment under Hicksville Family Medical Care (HFMC), but the patient must understand and agree that their primary care provider (PCP) needs to be changed.</li>"
            "<li>If the patient disagrees, they can only visit Statcare Urgent Care (SCUC).</li>"
            "</ul>"
            "</div>"
        )
        facilities = ["HFMC"]
    else:
        facility_message = (
            "Schedule with Hicksville Family Medical Care (HFMC) (Statcare Urgent Care (SCUC) is available for same day appointments only.)"
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

        },
        "provider_options": [
            {"name": provider.provider_name, "npi": provider.npi}
            for provider in providers
        ],
        "feedback_link": "https://forms.gle/ME2mKmVALXh4iDKWA"
    }
    print("Final Response:", response) 
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
