import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
import io
import random
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="SSK ARMS - Room Allocation System",
    page_icon="🏫",
    layout="wide"
)

# Define authorized users
AUTHORIZED_USERS = {
    "fahadhassan": "iobm1",
    "alihasnain": "iobm2", 
    "habibullah": "iobm3",
    "rabiyasabri": "iobm4"
}

def display_logo_login():
    """Display IOBM logo for login page - centered and smaller"""
    try:
        # Centered logo for login page
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image("iobm.png", width=150)
    except:
        # Fallback to centered text if logo is not found
        st.markdown("<div style='text-align: center;'><h2>IOBM</h2></div>", unsafe_allow_html=True)

def display_logo_main():
    """Display IOBM logo for main app - larger size for header"""
    try:
        # Larger logo for main app header
        st.image("iobm.png", width=200)
    except:
        # Fallback text if logo is not found
        st.markdown("<h2>IOBM</h2>", unsafe_allow_html=True)

def login_page():
    """Display login page"""
    # Center the logo and login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Display centered logo for login page
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        display_logo_login()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <h1>SSK ARMS</h1>
            <h3>Room Allocation System</h3>
            <p>Please login to access the room allocation system</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create login form
        with st.form("login_form"):
            st.markdown("#### Login Credentials")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("🚪 Login", type="primary")
            
            if submit_button:
                if username.lower() in AUTHORIZED_USERS and AUTHORIZED_USERS[username.lower()] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username.lower()
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")
    
    # Add some helpful information
    st.markdown("---")
    st.info("🎯 **Authorized Users Only** - Contact system administrator for access")
    
    # Display authorized users (without passwords for security)
    with st.expander("👥 Authorized Users"):
        st.markdown("Contact one of these users for login credentials:")
        st.markdown("• Fahad Hassan")
        st.markdown("• Ali Hasnain") 
        st.markdown("• Habibullah")
        st.markdown("• Rabiya Sabri")

def logout():
    """Handle logout"""
    for key in ['logged_in', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

@st.cache_data
def load_rooms():
    """Load rooms from the CSV file in the repository"""
    try:
        # Try different encodings to handle various file formats
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                rooms_df = pd.read_csv('rooms.csv', encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            # If all encodings fail, try with error handling
            rooms_df = pd.read_csv('rooms.csv', encoding='utf-8', errors='ignore')
        
        # Clean the dataframe
        rooms_df = rooms_df.dropna()  # Remove empty rows
        
        # Find the room column
        if 'room_name' in rooms_df.columns:
            rooms = rooms_df['room_name'].tolist()
        elif 'Room' in rooms_df.columns:
            rooms = rooms_df['Room'].tolist()
        elif 'room' in rooms_df.columns:
            rooms = rooms_df['room'].tolist()
        else:
            # If no specific column name, take the first column
            rooms = rooms_df.iloc[:, 0].tolist()
        
        # Clean room names - remove any non-printable characters
        cleaned_rooms = []
        for room in rooms:
            if pd.notna(room):
                # Convert to string and clean
                clean_room = str(room).strip()
                # Remove any non-ASCII characters that might cause issues
                clean_room = ''.join(char for char in clean_room if ord(char) < 128)
                if clean_room:  # Only add non-empty room names
                    cleaned_rooms.append(clean_room)
        
        return cleaned_rooms
        
    except Exception as e:
        st.error(f"Error loading rooms.csv: {str(e)}")
        st.info("💡 Try these solutions:")
        st.markdown("""
        1. **Re-save your CSV file**:
           - Open rooms.csv in Excel
           - Go to File → Save As
           - Choose "CSV UTF-8 (Comma delimited) (*.csv)"
           
        2. **Check file format**:
           - Ensure first row has header (like 'room_name')
           - Remove any special characters
           - Save with simple text editor if needed
           
        3. **Upload a new rooms file using the uploader below**
        """)
        return []

def parse_time_slot(days_str, time_str):
    """Parse days and time into a standardized format"""
    if pd.isna(days_str) or pd.isna(time_str):
        return None
    
    # Clean and standardize days
    days_str = str(days_str).strip()
    time_str = str(time_str).strip()
    
    # Parse days - handle various formats
    day_mapping = {
        'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed', 
        'thursday': 'Thu', 'friday': 'Fri', 'saturday': 'Sat', 'sunday': 'Sun',
        'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 
        'thu': 'Thu', 'fri': 'Fri', 'sat': 'Sat', 'sun': 'Sun'
    }
    
    # Split days by common separators
    days_list = re.split(r'[/,&\s]+', days_str.lower())
    standardized_days = []
    
    for day in days_list:
        day = day.strip()
        if day in day_mapping:
            standardized_days.append(day_mapping[day])
        elif len(day) >= 3:
            # Try to match partial day names
            for full_day, short_day in day_mapping.items():
                if day.startswith(full_day[:3]):
                    standardized_days.append(short_day)
                    break
    
    if not standardized_days:
        return None
    
    # Parse time - handle various formats
    time_pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)'
    match = re.search(time_pattern, time_str, re.IGNORECASE)
    
    if not match:
        return None
    
    start_hour, start_min, start_period, end_hour, end_min, end_period = match.groups()
    
    # Convert to 24-hour format (minutes from midnight)
    def to_minutes(hour, minute, period):
        h = int(hour)
        m = int(minute)
        if period.upper() == 'PM' and h != 12:
            h += 12
        elif period.upper() == 'AM' and h == 12:
            h = 0
        return h * 60 + m
    
    start_time = to_minutes(start_hour, start_min, start_period)
    end_time = to_minutes(end_hour, end_min, end_period)
    
    return {
        'days': standardized_days,
        'start_time': start_time,
        'end_time': end_time,
        'original_days': days_str,
        'original_time': time_str
    }

def needs_lab_room(course_code, program):
    """Check if course needs specific lab room types"""
    if pd.isna(course_code):
        return 'none'
    
    course_code = str(course_code).upper().strip()
    program = str(program).upper().strip() if pd.notna(program) else ""
    
    # Special courses that need IT labs
    special_it_courses = ['SCM400', 'STA302']
    if course_code in special_it_courses:
        return 'it_lab'
    
    # Course prefixes that need IT labs
    it_lab_prefixes = ['MIS', 'CSC', 'BDS', 'SEC', 'CSP', 'BTM']
    if any(course_code.startswith(prefix) for prefix in it_lab_prefixes):
        return 'it_lab'
    
    # Physics courses need SSKLAB402
    if course_code.startswith('PHY'):
        return 'physics_lab'
    
    # Engineering courses need science labs
    science_lab_prefixes = ['GSC', 'CME', 'EPE', 'ELE', 'ENG', 'MEM']
    if any(course_code.startswith(prefix) for prefix in science_lab_prefixes):
        return 'science_lab'
    
    return 'none'

def needs_faculty_room(program):
    """Check if program is Research or Thesis"""
    if pd.isna(program):
        return False
    
    program = str(program).upper().strip()
    return 'RESEARCH' in program or 'THESIS' in program

def has_friday_class(days_str):
    """Check if class has Friday in its schedule"""
    if pd.isna(days_str):
        return False
    
    days_str = str(days_str).upper()
    return 'FRIDAY' in days_str or 'FRI' in days_str

def is_lab_room(room_name):
    """Check if room is an IT lab"""
    room_str = str(room_name).upper()
    return 'IT LAB' in room_str or 'ITROOM' in room_str or 'IT_LAB' in room_str or 'IT_ROOM' in room_str

def is_science_lab(room_name):
    """Check if room is a science lab (SSKLAB402, SSKLAB403)"""
    room_str = str(room_name).upper()
    return 'SSKLAB' in room_str

def is_physics_lab(room_name):
    """Check if room is SSKLAB402 specifically for Physics"""
    room_str = str(room_name).upper()
    return room_str == 'SSKLAB402'

def has_time_conflict(slot1, slot2):
    """Check if two time slots conflict"""
    if not slot1 or not slot2:
        return False
    
    # Check if they share any common days
    common_days = set(slot1['days']) & set(slot2['days'])
    if not common_days:
        return False
    
    # Check time overlap
    return not (slot1['end_time'] <= slot2['start_time'] or 
                slot2['end_time'] <= slot1['start_time'])

def get_room_priority_group(room_name):
    """Determine room priority group based on room name"""
    room_str = str(room_name).upper()
    
    if 'CBM' in room_str:
        return 1  # Highest priority
    elif 'SSK' in room_str:
        return 2
    elif 'I.MGMT' in room_str or 'IMGMT' in room_str:
        return 3
    elif 'LIB' in room_str:
        return 4  # Library rooms - after I.MGMT
    elif 'CREKCLG' in room_str or 'CHS' in room_str or 'CREEK' in room_str or 'CRK' in room_str:
        return 5  # Combined Creek rooms
    else:
        return 6  # Unknown rooms get lowest priority

def get_room_category(room_name):
    """Get room category for pie chart"""
    room_str = str(room_name).upper()
    
    if 'CBM' in room_str:
        return 'CBM Rooms'
    elif 'SSK' in room_str and 'SSKLAB' not in room_str:
        return 'SSK Rooms'
    elif 'SSKLAB' in room_str:
        return 'Science Labs'
    elif 'I.MGMT' in room_str or 'IMGMT' in room_str:
        return 'I.MGMT Rooms'
    elif 'LIB' in room_str:
        return 'Library Rooms'
    elif 'CREKCLG' in room_str or 'CHS' in room_str or 'CREEK' in room_str or 'CRK' in room_str:
        return 'Creek Rooms'  # Combined Creek College and Creek High School
    elif 'IT LAB' in room_str or 'ITROOM' in room_str or 'IT_LAB' in room_str or 'IT_ROOM' in room_str:
        return 'IT Labs'
    else:
        return 'Other Rooms'

def create_room_distribution_pie_chart(rooms_list):
    """Create a Plotly pie chart showing room distribution by category"""
    # Count rooms by category
    room_categories = {}
    for room in rooms_list:
        category = get_room_category(room)
        room_categories[category] = room_categories.get(category, 0) + 1
    
    # Create DataFrame for pie chart
    df = pd.DataFrame(list(room_categories.items()), columns=['Category', 'Count'])
    
    # Create Plotly pie chart
    fig = px.pie(
        df, 
        values='Count', 
        names='Category',
        title='Room Distribution by Category',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Update traces for better text visibility
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        textfont=dict(size=12, color='black', family='Arial Black'),  # Bold black text
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        pull=[0.03] * len(df)  # Slightly separate slices for better visibility
    )
    
    # Update layout for moderate size and better appearance
    fig.update_layout(
        showlegend=True,
        height=450,  # Reduced from 600 to 450
        width=600,   # Reduced from 800 to 600
        font=dict(size=12),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.01,
            font=dict(size=11)
        ),
        margin=dict(l=20, r=120, t=20, b=20)  # Reduced top margin since no title
    )
    
    return fig, room_categories

def distribute_rooms_by_priority(rooms_list, exclude_allocated=None):
    """Distribute rooms by priority groups with randomization within each group"""
    if exclude_allocated is None:
        exclude_allocated = set()
    
    # Group rooms by priority
    priority_groups = {}
    for room in rooms_list:
        if room not in exclude_allocated:
            priority = get_room_priority_group(room)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(room)
    
    # Randomize within each priority group and combine
    final_room_order = []
    for priority in sorted(priority_groups.keys()):
        group_rooms = priority_groups[priority].copy()
        random.shuffle(group_rooms)  # Randomize within the priority group
        final_room_order.extend(group_rooms)
    
    return final_room_order

def allocate_rooms(courses_df, rooms_list):
    """Main room allocation function with enhanced logic for special requirements"""
    # Create a copy of the dataframe to preserve original order
    df = courses_df.copy().reset_index(drop=True)
    
    # Parse time slots for all courses
    df['parsed_time_slot'] = df.apply(
        lambda row: parse_time_slot(
            row.get('days', row.get('Days', '')), 
            row.get("time's", row.get('times', row.get('time', '')))
        ), 
        axis=1
    )
    
    # Separate different types of rooms
    it_lab_rooms = [room for room in rooms_list if is_lab_room(room)]
    science_lab_rooms = [room for room in rooms_list if is_science_lab(room)]
    physics_lab_room = [room for room in rooms_list if is_physics_lab(room)]  # SSKLAB402
    regular_rooms = [room for room in rooms_list if not (is_lab_room(room) or is_science_lab(room))]
    
    # Track room assignments by time slot
    room_schedule = {room: [] for room in rooms_list}
    
    # Track which rooms have been recently allocated to encourage variety
    recently_allocated = set()
    allocation_counter = 0
    
    # Track shortfalls
    it_lab_shortfall = 0
    regular_room_shortfall = 0
    
    # Process courses in original order
    allocated_courses = []
    
    for index, course in df.iterrows():
        time_slot = course['parsed_time_slot']
        course_code = course.get('course_code', course.get('Course Code', ''))
        program = course.get('program', course.get('Program', ''))
        days = course.get('days', course.get('Days', ''))
        
        # Create course dictionary with new columns
        course_dict = {
            'program': program,
            'section': course.get('section', course.get('Section', '')),
            'course_code': course_code,
            'course_title': course.get('course_title', course.get('Course Title', '')),
            'faculty': course.get('name', course.get('Faculty', course.get('Name', ''))),
            'days': days,
            'times': course.get("time's", course.get('times', course.get('Time', ''))),
            'students': course.get('total student strength', course.get('Students', 0)),
            'semester': course.get('semester_selected', course.get('Semester', '')),
            'catalog_year': course.get('catalog_year', course.get('Catalog Year', '')),
            'allocated_room': None
        }
        
        # Check for special cases first
        
        # 1. Research/Thesis programs
        if needs_faculty_room(program):
            course_dict['allocated_room'] = 'Facroom'
            allocated_courses.append(course_dict)
            continue
        
        # 2. Friday classes
        if has_friday_class(days):
            course_dict['allocated_room'] = 'No Room'
            allocated_courses.append(course_dict)
            continue
        
        # 3. Invalid time slots
        if not time_slot:
            course_dict['allocated_room'] = 'INVALID TIME SLOT'
            allocated_courses.append(course_dict)
            continue
        
        # 4. Determine room requirement type
        lab_requirement = needs_lab_room(course_code, program)
        
        # Get appropriate room list based on requirement
        if lab_requirement == 'physics_lab':
            # Physics courses need SSKLAB402 specifically
            preferred_rooms = physics_lab_room + science_lab_rooms + distribute_rooms_by_priority(regular_rooms, recently_allocated)
        elif lab_requirement == 'science_lab':
            # Engineering courses need science labs but not SSKLAB402 (exclude physics lab)
            available_science_labs = [room for room in science_lab_rooms if not is_physics_lab(room)]
            preferred_rooms = available_science_labs + distribute_rooms_by_priority(regular_rooms, recently_allocated)
        elif lab_requirement == 'it_lab':
            # IT courses need IT labs first, then regular rooms
            it_rooms_prioritized = distribute_rooms_by_priority(it_lab_rooms, recently_allocated)
            regular_rooms_prioritized = distribute_rooms_by_priority(regular_rooms, recently_allocated)
            preferred_rooms = it_rooms_prioritized + regular_rooms_prioritized
        else:
            # Regular courses get regular rooms first, then labs if needed
            regular_rooms_prioritized = distribute_rooms_by_priority(regular_rooms, recently_allocated)
            it_rooms_prioritized = distribute_rooms_by_priority(it_lab_rooms, recently_allocated)
            preferred_rooms = regular_rooms_prioritized + it_rooms_prioritized + science_lab_rooms
        
        # Try to allocate a room
        room_allocated = False
        
        for room in preferred_rooms:
            # Check for time conflicts
            has_conflict = False
            for existing_slot in room_schedule[room]:
                if has_time_conflict(time_slot, existing_slot):
                    has_conflict = True
                    break
            
            if not has_conflict:
                # Allocate this room
                course_dict['allocated_room'] = room
                room_schedule[room].append(time_slot)
                recently_allocated.add(room)
                room_allocated = True
                allocation_counter += 1
                break
        
        if not room_allocated:
            # Track shortfall type
            if lab_requirement == 'it_lab':
                course_dict['allocated_room'] = 'IT LAB REQUIRED'
                it_lab_shortfall += 1
            else:
                course_dict['allocated_room'] = 'ROOM REQUIRED'
                regular_room_shortfall += 1
        
        allocated_courses.append(course_dict)
        
        # Clear recently allocated set every 8 courses to allow room reuse
        # but encourage variety within small batches
        if allocation_counter % 8 == 0:
            recently_allocated.clear()
    
    return pd.DataFrame(allocated_courses), it_lab_shortfall, regular_room_shortfall

def main_app():
    """Main application after login"""
    # Header with logo and logout - Left aligned logo with title
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        # Logo and title together on the left
        display_logo_main()
    
    with col2:
        st.markdown("""
        <div style="padding-top: 40px;">
            <h1>SSK ARMS</h1>
            <h3>Room Allocation System</h3>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"**Welcome, {st.session_state.username.title()}!**")
        if st.button("🚪 Logout", type="secondary"):
            logout()
    
    st.markdown("Upload your course schedule and automatically allocate rooms")
    
    # Load rooms
    rooms_list = load_rooms()
    
    # Add manual room upload option if automatic loading fails
    if not rooms_list:
        st.warning("⚠️ Could not load rooms from rooms.csv automatically.")
        st.markdown("**Upload your rooms file manually:**")
        
        rooms_file = st.file_uploader(
            "Upload rooms.csv file",
            type=['csv'],
            help="Upload a CSV file with room names"
        )
        
        if rooms_file is not None:
            try:
                # Try different encodings
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
                
                for encoding in encodings:
                    try:
                        rooms_df = pd.read_csv(rooms_file, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    rooms_df = pd.read_csv(rooms_file, encoding='utf-8', errors='ignore')
                
                # Get room names from first column
                rooms_list = rooms_df.iloc[:, 0].dropna().tolist()
                rooms_list = [str(room).strip() for room in rooms_list if str(room).strip()]
                
                st.success(f"✅ Loaded {len(rooms_list)} rooms from uploaded file")
                
            except Exception as e:
                st.error(f"Error reading rooms file: {str(e)}")
                st.stop()
        else:
            st.stop()
    else:
        st.success(f"✅ Loaded {len(rooms_list)} rooms from rooms.csv")
    
    # Show room distribution with enhanced categorization
    if rooms_list:
        st.markdown("### Room Distribution Analysis")
        
        # Create and display pie chart
        fig, room_categories = create_room_distribution_pie_chart(rooms_list)
        st.plotly_chart(fig, use_container_width=True)
        
        # Enhanced summary statistics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            it_lab_rooms = [room for room in rooms_list if is_lab_room(room)]
            st.metric("Total Rooms", len(rooms_list))
            st.metric("IT Labs", len(it_lab_rooms))
        
        with col2:
            science_lab_rooms = [room for room in rooms_list if is_science_lab(room)]
            regular_rooms = [room for room in rooms_list if not (is_lab_room(room) or is_science_lab(room))]
            st.metric("Science Labs", len(science_lab_rooms))
            st.metric("Regular Rooms", len(regular_rooms))
        
        with col3:
            physics_lab_count = len([room for room in rooms_list if is_physics_lab(room)])
            st.metric("Physics Lab (SSKLAB402)", physics_lab_count)
            top_category = max(room_categories, key=room_categories.get)
            st.metric("Largest Category", f"{top_category}")
        
        with col4:
            st.metric("Categories", len(room_categories))
            avg_per_category = round(len(rooms_list) / len(room_categories), 1)
            st.metric("Avg per Category", avg_per_category)
        
        # Detailed breakdown in expandable section
        with st.expander("🏛️ Detailed Room Breakdown"):
            # Create summary table
            summary_data = []
            for category, count in sorted(room_categories.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(rooms_list)) * 100
                priority_ranges = {
                    'CBM Rooms': 'Priority 1 (Highest)',
                    'SSK Rooms': 'Priority 2',
                    'I.MGMT Rooms': 'Priority 3', 
                    'Library Rooms': 'Priority 4',
                    'Creek Rooms': 'Priority 5',
                    'IT Labs': 'Special (IT Courses)',
                    'Science Labs': 'Special (Science/Engineering)',
                    'Other Rooms': 'Priority 6 (Lowest)'
                }
                summary_data.append({
                    'Category': category,
                    'Count': count,
                    'Percentage': f"{percentage:.1f}%",
                    'Priority': priority_ranges.get(category, 'Unknown')
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
    
    # File upload - Multiple files support
    st.markdown("---")
    st.subheader("📁 Upload Course Schedules")
    st.markdown("**Upload multiple catalog files (they will be combined automatically)**")
    
    uploaded_files = st.file_uploader(
        "Choose Excel or CSV files",
        type=['xlsx', 'xls', 'csv'],
        accept_multiple_files=True,
        help="Upload multiple catalog files - they will be combined into one schedule"
    )
    
    if uploaded_files:
        try:
            combined_df = pd.DataFrame()
            file_info = []
            
            # Process each uploaded file
            for i, uploaded_file in enumerate(uploaded_files, 1):
                try:
                    # Read the file
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    # Combine with previous data
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                    
                    file_info.append({
                        'file': uploaded_file.name,
                        'courses': len(df),
                        'status': '✅ Success'
                    })
                    
                except Exception as e:
                    file_info.append({
                        'file': uploaded_file.name,
                        'courses': 0,
                        'status': f'❌ Error: {str(e)}'
                    })
                    st.error(f"Error reading {uploaded_file.name}: {str(e)}")
            
            # Show file processing summary
            if file_info:
                st.markdown("### 📊 File Processing Summary")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    successful_files = len([f for f in file_info if '✅' in f['status']])
                    st.metric("Files Processed", f"{successful_files}/{len(uploaded_files)}")
                
                with col2:
                    total_courses = sum([f['courses'] for f in file_info])
                    st.metric("Total Courses", total_courses)
