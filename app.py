import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Security Config
app.secret_key = "law_firm_secure_key_2026"
ADMIN_PASSWORD = "@Loginlocal2452"  # Firm's secret password

# Initialize Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# --- CLIENT ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: 
        return redirect('/')
    # Fetch cases specifically for the logged-in user
    user_cases = supabase.table("cases").select("*").eq("user_email", session['user']).order("created_at", desc=True).execute()
    return render_template('dashboard.html', cases=user_cases.data)

@app.route('/create-case', methods=['POST'])
def create_case():
    # Normalize email: strip spaces and make lowercase to prevent duplicates
    raw_email = request.form.get('email')
    if not raw_email:
        return redirect('/')
    
    email = raw_email.strip().lower()
    session['user'] = email
    
    # FEATURE: Smart Case Check
    # Check if a case already exists for this email
    check_existing = supabase.table("cases").select("*").eq("user_email", email).execute()
    
    if check_existing.data:
        # If client exists, don't create a new case, just take them to their dashboard
        return redirect(url_for('dashboard'))
    
    # If brand new client, initialize their first legal file
    title = request.form.get('title') or "New Litigation Inquiry"
    
    supabase.table("cases").insert({
        "user_email": email, 
        "title": title, 
        "status": "Reviewing"
    }).execute()
    
    return redirect(url_for('dashboard'))

@app.route('/case/<case_id>')
def view_case(case_id):
    # Retrieve specific case details and message history
    case_data = supabase.table("cases").select("*").eq("id", case_id).single().execute()
    msgs = supabase.table("messages").select("*").eq("case_id", case_id).order("created_at").execute()
    return render_template('case_room.html', case=case_data.data, messages=msgs.data)

# --- CHAT & COMMUNICATION LOGIC ---

@app.route('/send-message', methods=['POST'])
def send_message():
    data = request.json
    supabase.table("messages").insert({
        "case_id": data.get('case_id'),
        "sender": data.get('sender'), # 'client' or 'lawyer'
        "content": data.get('content')
    }).execute()
    return jsonify({"status": "sent"})

# --- LAWYER ADMIN ROUTES (PROTECTED) ---

@app.route('/lawyer-admin', methods=['GET', 'POST'])
def lawyer_admin():
    # Handle Login Attempt
    if request.method == 'POST':
        password_attempt = request.form.get('password')
        if password_attempt == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('lawyer_admin'))
        else:
            return "Unauthorized: Incorrect Password", 401

    # Check for Active Admin Session
    if not session.get('is_admin'):
        # Professional Inline Login Form
        return '''
            <body style="background:#020617; color:white; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; margin:0;">
                <form method="post" style="background:#0f172a; padding:3rem; border-radius:1.5rem; border:1px solid #f59e0b; box-shadow: 0 0 30px rgba(245, 158, 11, 0.1); width: 350px;">
                    <div style="text-align:center; margin-bottom:2rem;">
                        <h2 style="color:#f59e0b; font-family:serif; letter-spacing:2px;">ADMIN ACCESS</h2>
                        <p style="color:#64748b; font-size:12px; text-transform:uppercase;">Secure Lawyer Portal</p>
                    </div>
                    <input type="password" name="password" placeholder="Enter Firm Password" required 
                           style="padding:1rem; width:100%; margin-bottom:1.5rem; border-radius:0.75rem; border:1px solid #334155; background:#1e293b; color:white; outline:none; box-sizing:border-box;">
                    <button type="submit" style="background:#f59e0b; color:#000; width:100%; padding:1rem; border:none; border-radius:0.75rem; font-weight:bold; cursor:pointer; text-transform:uppercase; letter-spacing:1px;">Verify Credentials</button>
                </form>
            </body>
        '''

    # If Authenticated, show all cases
    all_cases = supabase.table("cases").select("*").order("created_at", desc=True).execute()
    return render_template('admin_portal.html', cases=all_cases.data)

@app.route('/admin/reply', methods=['POST'])
def admin_reply():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    supabase.table("messages").insert({
        "case_id": data.get('case_id'),
        "sender": "lawyer",
        "content": data.get('content')
    }).execute()
    return jsonify({"status": "sent"})

@app.route('/admin/update-status', methods=['POST'])
def update_status():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    supabase.table("cases").update({"status": data.get('status')}).eq("id", data.get('case_id')).execute()
    return jsonify({"status": "updated"})

@app.route('/lawyer-logout')
def lawyer_logout():
    session.pop('is_admin', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)