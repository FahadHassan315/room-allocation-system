def login_page():
    """Display login page with improved structure"""
    # Add custom CSS for better spacing and layout
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }
    .logo-title-section {
        text-align: center;
        margin-bottom: 2rem;
    }
    .logo-title-section img {
        margin-bottom: 0.5rem !important;
    }
    .main-title {
        color: #d32f2f;
        font-size: 2rem;
        font-weight: 600;
        margin: 0.5rem 0 0.3rem 0 !important;
        line-height: 1.2;
    }
    .sub-title {
        color: #666;
        font-size: 1.1rem;
        margin: 0.3rem 0 0.5rem 0 !important;
        font-weight: 400;
    }
    .description-text {
        color: #888;
        font-size: 0.9rem;
        margin: 0.5rem 0 1.5rem 0 !important;
    }
    .login-form {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .form-header {
        color: #333;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 1rem !important;
        text-align: center;
    }
    /* Reduce default streamlit spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create centered container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo and title section - tightly grouped
        st.markdown('<div class="logo-title-section">', unsafe_allow_html=True)
        
        # Display logo
        try:
            st.image("iobm.png", width=120)
        except:
            st.markdown('<div style="background: #f0f0f0; padding: 2rem; border-radius: 8px; text-align: center; margin-bottom: 0.5rem;"><h3>IOBM</h3></div>', unsafe_allow_html=True)
        
        # Title and subtitle with minimal spacing
        st.markdown('<h1 class="main-title">SSK ARMS</h1>', unsafe_allow_html=True)
        st.markdown('<h3 class="sub-title">Room Allocation System</h3>', unsafe_allow_html=True)
        st.markdown('<p class="description-text">Please login to access the room allocation system</p>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Login form with better styling
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown('<h4 class="form-header">Login Credentials</h4>', unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="Enter your username", label_visibility="visible")
            password = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="visible")
            
            # Submit button with full width
            submit_button = st.form_submit_button("🚪 Login", type="primary", use_container_width=True)
            
            if submit_button:
                if username.lower() in AUTHORIZED_USERS and AUTHORIZED_USERS[username.lower()] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username.lower()
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Compact footer information
    st.markdown("---")
    
    # Info and authorized users in a more compact layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("🎯 **Authorized Users Only**\nContact system administrator for access")
    
    with col2:
        with st.expander("👥 Authorized Users"):
            st.markdown("""
            **Contact for credentials:**
            • Fahad Hassan  
            • Ali Hasnain  
            • Habibullah  
            • Rabiya Sabri
            """)

def display_logo_login():
    """Display IOBM logo for login page - this function is now integrated into login_page()"""
    # This function is no longer needed as the logo display is now handled directly in login_page()
    pass
