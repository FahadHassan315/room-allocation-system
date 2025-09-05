def login_page():
    """Display login page with improved structure"""
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo section - centered with minimal spacing
        st.markdown("<div style='text-align: center; margin-bottom: 1rem;'>", unsafe_allow_html=True)
        try:
            st.image("iobm.png", width=120)
        except:
            st.markdown("<div style='background: #f0f0f0; padding: 1rem; border-radius: 8px; margin: 0 auto; width: 120px;'><h3 style='margin: 0; text-align: center;'>IOBM</h3></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Title section - tightly spaced
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #d32f2f; margin: 0.5rem 0 0.2rem 0; font-size: 2rem;">SSK ARMS</h1>
            <h3 style="color: #666; margin: 0.2rem 0 0.3rem 0; font-weight: 400;">Room Allocation System</h3>
            <p style="color: #888; margin: 0.3rem 0 0; font-size: 0.9rem;">Please login to access the room allocation system</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        with st.container():
            st.markdown("#### Login Credentials")
            
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_button = st.form_submit_button("🚪 Login", type="primary", use_container_width=True)
                
                if submit_button:
                    if username.lower() in AUTHORIZED_USERS and AUTHORIZED_USERS[username.lower()] == password:
                        st.session_state.logged_in = True
                        st.session_state.username = username.lower()
                        st.success(f"✅ Welcome, {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Please try again.")
    
    # Footer information - more compact
    st.markdown("---")
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
