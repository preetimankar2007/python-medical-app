import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import os
import re
import random
import string
from datetime import datetime
from auth import (
    init_db, 
    register_user, 
    login_user, 
    verify_token, 
    create_discount_code,
    validate_discount_code,
    register_mr,
    get_mr_details,
    get_mr_statistics,
    record_doctor_visit,
    update_mr_profile
)
import sqlite3

# Initialize the database
init_db()

# Function to generate unique doctor discount code
def generate_doctor_code(doctor_id):
    """Generate a unique discount code for a doctor"""
    prefix = "DR"
    random_digits = ''.join(random.choices(string.digits, k=5))
    return f"{prefix}{random_digits}"

# Function to validate and apply discount
def apply_discount_code(code):
    """Validate and apply discount code using database"""
    if not code:
        return False, "Please enter a discount code"
    
    return validate_discount_code(code)

# Function to store discount code in session state
def save_discount_code(username):
    """Store generated discount code in database"""
    if 'discount_code' not in st.session_state:
        # Get doctor's ID from database
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        try:
            c.execute('SELECT id FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            if result:
                doctor_id = result[0]
                # Generate new code
                new_code = generate_doctor_code(doctor_id)
                success, message = create_discount_code(doctor_id, new_code)
                if success:
                    st.session_state.discount_code = new_code
                else:
                    st.error(message)
                    return None
            else:
                st.error("Doctor not found in database")
                return None
        finally:
            conn.close()
    
    return st.session_state.discount_code

# Set page config
st.set_page_config(
    page_title="Medical Prescription Recognition App",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
    <style>
    /* Main app styling */
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
        background-color: #f8f9fa;
    }
    
    .main {
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Header styling */
    .app-header {
        background: linear-gradient(135deg, #0047AB 0%, #00A3E0 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .app-header h1 {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .app-header p {
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Button styling */
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
        background: linear-gradient(135deg, #0047AB 0%, #00A3E0 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 5px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Form styling */
    .auth-form {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .auth-form h2 {
        color: #0047AB;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #ddd;
        padding: 0.5rem;
    }
    
    /* Prescription box styling */
    .prescription-box {
        border: 1px solid #e0e0e0;
        padding: 1.5rem;
        border-radius: 10px;
        background-color: white;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f1f3f4;
        padding: 2rem 1rem;
    }
    
    /* Section headers */
    .section-header {
        color: #0047AB;
        font-size: 1.5rem;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #0047AB;
    }
    
    /* Tips section styling */
    .tips-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 2rem;
    }
    
    .tips-section h3 {
        color: #0047AB;
        margin-bottom: 1rem;
    }
    
    .tips-section ul {
        list-style-type: none;
        padding-left: 0;
    }
    
    .tips-section li {
        margin-bottom: 0.5rem;
        padding-left: 1.5rem;
        position: relative;
    }
    
    .tips-section li:before {
        content: "•";
        color: #0047AB;
        position: absolute;
        left: 0;
    }
    
    /* Status messages */
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .stError {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Image display styling */
    .image-container {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* Navigation links */
    .nav-link {
        color: #0047AB;
        text-decoration: none;
        font-weight: 500;
    }
    
    .nav-link:hover {
        text-decoration: underline;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid #dee2e6;
    }
    </style>
""", unsafe_allow_html=True)

def login_page():
    st.markdown("""
        <div class="app-header">
            <h1>🏥 Medical Prescription Recognition</h1>
            <p>Secure login to access prescription processing</p>
        </div>
    """, unsafe_allow_html=True)
    
    # st.markdown('<div class="auth-form">', unsafe_allow_html=True)
    st.markdown('<h2>Login</h2>', unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("Login", key="login_button"):
            if username and password:
                success, result, user_id, user_type = login_user(username, password)
                if success:
                    st.session_state['authenticated'] = True
                    st.session_state['token'] = result
                    st.session_state['username'] = username
                    st.session_state['user_id'] = user_id
                    st.session_state['user_type'] = user_type
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error(result)
            else:
                st.warning("Please enter both username and password")
    
    st.markdown('<div style="text-align: center; margin-top: 1rem;">', unsafe_allow_html=True)
    st.markdown("""
        <div>New user?</div>
        <div style="margin-top: 0.5rem;">
            <a class="nav-link" href="#register" style="margin-right: 1rem;">Register as Doctor</a> | 
            <a class="nav-link" href="#mr_register" style="margin-left: 1rem;">Register as Medical Representative</a>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def register_page():
    st.markdown("""
        <div class="app-header">
            <h1>🏥 Medical Prescription Recognition</h1>
            <p>Create your account to get started</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-form">', unsafe_allow_html=True)
    st.markdown('<h2>Register</h2>', unsafe_allow_html=True)
    
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password",
                           help="Password must be at least 8 characters and contain uppercase, lowercase, numbers, and special characters")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("Register", key="register_button"):
            if username and email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(username, password, email)
                    if success:
                        st.success(message)
                        st.info("Please login with your credentials")
                        st.session_state['page'] = 'login'
                        st.experimental_rerun()
                    else:
                        st.error(message)
            else:
                st.warning("Please fill in all fields")
    
    st.markdown('<div style="text-align: center; margin-top: 1rem;">', unsafe_allow_html=True)
    st.markdown('Already have an account? <a class="nav-link" href="#login">Login here</a>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def logout():
    for key in ['authenticated', 'token', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

def enhance_prescription_image(image, denoise_strength, contrast_strength):
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive thresholding with reduced block size for better detail
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 21, 10
        )
        
        # Denoise with strength parameter
        denoised = cv2.fastNlMeansDenoising(binary, None, denoise_strength, 7, 21)
        
        # Apply dilation to connect broken text
        kernel = np.ones((2,2), np.uint8)
        dilated = cv2.dilate(denoised, kernel, iterations=1)
        
        # Enhance edges
        edges = cv2.Laplacian(dilated, cv2.CV_8U, ksize=3)
        sharpened = cv2.addWeighted(dilated, 1.5, edges, -0.5, 0)
        
        # Apply contrast enhancement
        enhanced = cv2.convertScaleAbs(sharpened, alpha=contrast_strength, beta=10)
        
        # Invert back to black text on white background
        enhanced = cv2.bitwise_not(enhanced)
        
        return enhanced
    except Exception as e:
        st.error(f"Error in image preprocessing: {str(e)}")
        return None

def extract_prescription_text(image, denoise_strength, contrast_strength):
    try:
        # Enhance the image
        processed_image = enhance_prescription_image(image, denoise_strength, contrast_strength)
        if processed_image is None:
            return "Error: Image preprocessing failed"
        
        # Configure pytesseract for medical text
        custom_config = '--oem 3 --psm 6'
        
        # Extract text
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        if not text.strip():
            return "No text was detected in the prescription. Please try adjusting the image processing parameters."
        
        # Process and structure the extracted text
        structured_text = process_prescription_text(text)
        
        return structured_text
    except Exception as e:
        return f"Error in text extraction: {str(e)}"

def process_prescription_text(text):
    """Process and structure the prescription text"""
    try:
        # Split text into lines
        lines = text.split('\n')
        
        # Initialize sections
        sections = {
            'Doctor Info': [],
            'Patient Info': [],
            'Medications': [],
            'Instructions': [],
            'Other Details': []
        }
        
        current_section = 'Other Details'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to categorize the line
            lower_line = line.lower()
            
            # Check for doctor-related information
            if any(word in lower_line for word in ['dr.', 'dr ', 'doctor', 'clinic', 'hospital']):
                current_section = 'Doctor Info'
                sections[current_section].append(line)
            
            # Check for patient-related information
            elif any(word in lower_line for word in ['name:', 'age:', 'patient', 'sex:', 'gender:']):
                current_section = 'Patient Info'
                sections[current_section].append(line)
            
            # Check for medication-related information
            elif any(word in lower_line for word in ['tab.', 'tablet', 'cap.', 'capsule', 'mg', 'ml', 'syrup', 'injection']):
                current_section = 'Medications'
                sections[current_section].append(line)
            
            # Check for instructions
            elif any(word in lower_line for word in ['take', 'times', 'daily', 'days', 'morning', 'night', 'afternoon']):
                current_section = 'Instructions'
                sections[current_section].append(line)
            
            else:
                sections[current_section].append(line)
        
        # Format the structured text
        formatted_text = ""
        for section, lines in sections.items():
            if lines:
                formatted_text += f"\n{section}:\n" + "-" * 40 + "\n"
                formatted_text += "\n".join(lines) + "\n"
        
        return formatted_text.strip()
    except Exception as e:
        return text  # Return original text if processing fails

def mr_registration_page():
    st.markdown("""
        <div class="app-header">
            <h1>🏥 Medical Representative Registration</h1>
            <p>Create your Medical Representative account</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-form">', unsafe_allow_html=True)
    st.markdown('<h2>MR Registration</h2>', unsafe_allow_html=True)
    
    # Basic Information
    username = st.text_input("Username*")
    email = st.text_input("Email*")
    password = st.text_input("Password*", type="password",
                           help="Password must be at least 8 characters and contain uppercase, lowercase, numbers, and special characters")
    confirm_password = st.text_input("Confirm Password*", type="password")
    
    # Professional Information
    st.markdown("<h3>Professional Details</h3>", unsafe_allow_html=True)
    full_name = st.text_input("Full Name*")
    phone = st.text_input("Phone Number*")
    territory = st.text_input("Territory/Region*")
    company = st.text_input("Pharmaceutical Company*")
    specialization = st.text_input("Specialization")
    
    if st.button("Register as MR", key="mr_register_button"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, message = register_mr(
                username, password, email, full_name,
                phone, territory, company, specialization
            )
            if success:
                st.success(message)
                st.info("Please login with your credentials")
                st.session_state['page'] = 'login'
                st.experimental_rerun()
            else:
                st.error(message)

def mr_dashboard():
    st.markdown("""
        <div class="app-header">
            <h1>🏥 Medical Representative Dashboard</h1>
            <p>Manage your doctor visits and track performance</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Get MR details
    mr_details = get_mr_details(st.session_state['user_id'])
    if not mr_details:
        st.error("Error loading MR profile")
        return
    
    # Display MR Statistics
    stats = get_mr_statistics(mr_details[0])
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Assigned Doctors", stats['total_doctors'])
    with col2:
        st.metric("Monthly Visits", stats['monthly_visits'])
    with col3:
        st.metric("Territory", mr_details[3])  # territory field
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Record Visit", "Visit History", "Profile"])
    
    with tab1:
        st.subheader("Record New Doctor Visit")
        doctor_id = st.selectbox("Select Doctor", ["Dr. Smith", "Dr. Johnson"])  # This should be populated from database
        visit_purpose = st.text_input("Visit Purpose")
        discussion_points = st.text_area("Discussion Points")
        feedback = st.text_area("Feedback/Notes")
        next_visit_date = st.date_input("Next Visit Date")
        
        if st.button("Record Visit"):
            success, message = record_doctor_visit(
                mr_details[0], doctor_id, visit_purpose,
                discussion_points, feedback, next_visit_date
            )
            if success:
                st.success(message)
            else:
                st.error(message)
    
    with tab2:
        st.subheader("Visit History")
        # Display visit history in a table
        st.dataframe({
            "Date": ["2024-01-01", "2024-01-15"],
            "Doctor": ["Dr. Smith", "Dr. Johnson"],
            "Purpose": ["Product Introduction", "Follow-up"],
            "Next Visit": ["2024-02-01", "2024-02-15"]
        })
    
    with tab3:
        st.subheader("Profile Information")
        with st.form("profile_update_form"):
            updated_name = st.text_input("Full Name", value=mr_details[2])  # full_name field
            updated_phone = st.text_input("Phone", value=mr_details[3])  # phone field
            updated_territory = st.text_input("Territory", value=mr_details[4])  # territory field
            updated_company = st.text_input("Company", value=mr_details[5])  # company field
            updated_specialization = st.text_input("Specialization", value=mr_details[6])  # specialization field
            
            if st.form_submit_button("Update Profile"):
                success, message = update_mr_profile(
                    st.session_state['user_id'],
                    updated_name, updated_phone, updated_territory,
                    updated_company, updated_specialization
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

def main_app():
    st.markdown("""
        <div class="app-header">
            <h1>🏥 Medical Prescription Recognition</h1>
            <p>Upload and process medical prescriptions with advanced recognition</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Add discount code section in sidebar for doctors
    st.sidebar.markdown('<div class="section-header">Doctor Discount Code</div>', unsafe_allow_html=True)
    
    # Generate unique doctor ID (in real app, this would come from the database)
    doctor_id = st.session_state.get('username', 'default_doctor')
    
    # Display or generate discount code
    discount_code = save_discount_code(doctor_id)
    if discount_code:
        st.sidebar.markdown(f"""
            <div style='background-color: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>
                <h4 style='margin: 0; color: #0047AB;'>Your Discount Code</h4>
                <p style='font-size: 24px; font-weight: bold; margin: 10px 0; color: #0047AB;'>{discount_code}</p>
                <p style='margin: 0; font-size: 12px;'>Share this code with your patients for a 20% discount</p>
                <p style='margin: 5px 0 0 0; font-size: 10px; color: #666;'>Valid for 30 days • Max 100 uses</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Add discount code input for patients
    st.sidebar.markdown('<div class="section-header">Patient Discount</div>', unsafe_allow_html=True)
    patient_code = st.sidebar.text_input("Enter Doctor's Discount Code")
    if st.sidebar.button("Apply Discount"):
        success, message = apply_discount_code(patient_code)
        if success:
            st.session_state.discount_applied = True
            st.session_state.discount_percentage = int(message.split('%')[0])
            st.sidebar.success(message)
        else:
            st.session_state.discount_applied = False
            st.sidebar.error(message)
    
    # Display active discount if applied
    if st.session_state.get('discount_applied', False):
        st.sidebar.markdown(f"""
            <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px;'>
                <p style='margin: 0; color: #155724;'>
                    <strong>{st.session_state.discount_percentage}% discount active</strong>
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    # Add image preprocessing options in sidebar
    st.sidebar.markdown('<div class="section-header">Image Settings</div>', unsafe_allow_html=True)
    denoise_strength = st.sidebar.slider("Denoise Strength", 5, 30, 15)
    contrast_strength = st.sidebar.slider("Contrast Enhancement", 1.0, 4.0, 2.0, 0.1)
    
    # Main content
    st.markdown('<div class="section-header">Upload Prescription</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a prescription image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="section-header">Original Image</div>', unsafe_allow_html=True)
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                image = Image.open(uploaded_file)
                st.image(image, use_column_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="section-header">Processed Image</div>', unsafe_allow_html=True)
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                processed_image = enhance_prescription_image(opencv_image, denoise_strength, contrast_strength)
                if processed_image is not None:
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(processed_image, use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("Extract Prescription Details", key="extract_button"):
                with st.spinner("Processing prescription..."):
                    extracted_text = extract_prescription_text(opencv_image, denoise_strength, contrast_strength)
                    
                    st.markdown('<div class="section-header">Extracted Details</div>', unsafe_allow_html=True)
                    st.markdown('<div class="prescription-box">', unsafe_allow_html=True)
                    st.text_area("", extracted_text, height=400)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if extracted_text and not extracted_text.startswith("Error"):
                        col1, col2, col3 = st.columns([1,2,1])
                        with col2:
                            st.download_button(
                                label="Download Prescription Text",
                                data=extracted_text,
                                file_name="prescription.txt",
                                mime="text/plain"
                            )
        
        except Exception as e:
            st.error(f"An error occurred while processing the prescription: {str(e)}")
            st.info("Please ensure the prescription image is clear and properly oriented.")
    
    # Tips section
    st.markdown("""
        <div class="tips-section">
            <h3>📋 Tips for Best Results</h3>
            <ul>
                <li>Ensure the prescription is well-lit and clearly visible</li>
                <li>Avoid shadows and glare on the prescription</li>
                <li>Keep the prescription straight when taking the photo</li>
                <li>Include all parts of the prescription in the image</li>
                <li>If text is unclear, try adjusting the Denoise and Contrast settings</li>
                <li>Make sure handwriting is reasonably legible</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="tips-section">
            <h3>🔍 Recognition Capabilities</h3>
            <ul>
                <li>Doctor and clinic information</li>
                <li>Patient details</li>
                <li>Prescribed medications</li>
                <li>Dosage instructions</li>
                <li>Additional notes and instructions</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="footer">
            <p>© 2024 Medical Prescription Recognition App. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)

def main():
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    
    # Show logout button if authenticated
    if st.session_state['authenticated']:
        st.sidebar.button("Logout", on_click=logout)
        st.sidebar.write(f"Logged in as: {st.session_state['username']}")
    
    # Navigation
    if not st.session_state['authenticated']:
        pages = {
            'login': login_page,
            'register': register_page,
            'mr_register': mr_registration_page
        }
        
        # Navigation links
        st.markdown(
            '<div style="text-align: center">'
            '<h1>🏥 Medical Prescription Recognition App</h1>'
            '</div>',
            unsafe_allow_html=True
        )
        
        # Show current page
        pages[st.session_state['page']]()
        
        # Handle navigation
        if st.session_state['page'] == 'login':
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Register as Doctor"):
                    st.session_state['page'] = 'register'
                    st.experimental_rerun()
            with col2:
                if st.button("Register as MR"):
                    st.session_state['page'] = 'mr_register'
                    st.experimental_rerun()
        else:
            if st.button("Back to Login"):
                st.session_state['page'] = 'login'
                st.experimental_rerun()
    else:
        # Show appropriate dashboard based on user type
        if st.session_state.get('user_type') == 'mr':
            mr_dashboard()
        else:
            main_app()

if __name__ == "__main__":
    main()