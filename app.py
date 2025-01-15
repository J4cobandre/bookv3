from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///par_logic.db'
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

    if not location or not insurance:
        return jsonify({"error": "Both location and insurance are required!"})

    # Use case-insensitive matching with normalized location
    providers = Provider.query.filter(
        db.func.upper(Provider.location).in_([location.upper(), "ALL"]),
        db.func.upper(Provider.insurance) == insurance.upper()
    ).all()

    if not providers:
        return jsonify({"error": "No providers found for the given location and insurance."})

    out_of_contract = not providers[0].hfmc_contract

    if out_of_contract:
        facility_message = "You can only visit SCUC."
        facilities = ["SCUC"]
    else:
        facility_message = "Schedule with HFMC (SCUC is available for same day appointments only)."
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
            "form_link": get_pcp_change_form_link(insurance) if providers[0].pcp_change_requirement.strip() == "Insurance has PCP Change Form" else None
        },
        "provider_options": [
            {"name": provider.provider_name, "npi": provider.npi}
            for provider in providers
        ]
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)