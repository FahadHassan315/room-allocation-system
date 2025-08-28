import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
import io

# Page configuration
st.set_page_config(
    page_title="Room Allocation System",
    page_icon="🏫",
    layout="wide"
)

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

def needs_lab_room(course_code):
    """Check if course needs IT lab/room"""
    if pd.isna(course_code):
        return False
    
    course_code = str(course_code).upper().strip()
    lab_prefixes = ['MIS', 'CSC', 'BDS', 'SEC']
    
    return any(course_code.startswith(prefix) for prefix in lab_prefixes)

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

def allocate_rooms(courses_df, rooms_list):
    """Main room allocation function"""
    # Create a copy of the dataframe
    df = courses_df.copy()
    
    # Parse time slots for all courses
    df['parsed_time_slot'] = df.apply(
        lambda row: parse_time_slot(row.get('days', ''), row.get('times', row.get('time', ''))), 
        axis=1
    )
    
    # Filter out courses with invalid time slots
    valid_courses = df[df['parsed_time_slot'].notna()].copy()
    invalid_courses = df[df['parsed_time_slot'].isna()].copy()
    
    # Separate lab and regular rooms
    lab_rooms = [room for room in rooms_list if 'ITLAB' in str(room).upper() or 'ITROOM' in str(room).upper()]
    regular_rooms = [room for room in rooms_list if room not in lab_rooms]
    
    # Track room assignments
    room_schedule = {room: [] for room in rooms_list}
    allocated_courses = []
    unallocated_courses = []
    
    # Sort courses: lab courses first, then by time
    def sort_key(row):
        needs_lab = needs_lab_room(row.get('course_code', ''))
        start_time = row['parsed_time_slot']['start_time'] if row['parsed_time_slot'] else 999999
        return (0 if needs_lab else 1, start_time)
    
    valid_courses = valid_courses.iloc[valid_courses.apply(sort_key, axis=1).argsort()]
    
    # Allocate rooms
    for _, course in valid_courses.iterrows():
        allocated = False
        time_slot = course['parsed_time_slot']
        course_code = course.get('course_code', '')
        
        # Determine which rooms to try first
        if needs_lab_room(course_code):
            preferred_rooms = lab_rooms + regular_rooms
        else:
            preferred_rooms = regular_rooms + lab_rooms
        
        # Try to allocate a room
        for room in preferred_rooms:
            # Check for conflicts with existing allocations
            has_conflict = False
            for existing_course in room_schedule[room]:
                if has_time_conflict(time_slot, existing_course['parsed_time_slot']):
                    has_conflict = True
                    break
            
            if not has_conflict:
                # Allocate this room
                course_dict = course.to_dict()
                course_dict['allocated_room'] = room
                room_schedule[room].append(course_dict)
                allocated_courses.append(course_dict)
                allocated = True
                break
        
        if not allocated:
            course_dict = course.to_dict()
            course_dict['allocated_room'] = 'ROOM REQUIRED'
            unallocated_courses.append(course_dict)
    
    # Handle invalid time slot courses
    for _, course in invalid_courses.iterrows():
        course_dict = course.to_dict()
        course_dict['allocated_room'] = 'INVALID TIME SLOT'
        unallocated_courses.append(course_dict)
    
    # Combine all results
    all_results = allocated_courses + unallocated_courses
    
    return pd.DataFrame(all_results), len(unallocated_courses)

def main():
    st.title("🏫 Room Allocation System")
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
    
    # Show room categories
    lab_rooms = [room for room in rooms_list if 'ITLAB' in str(room).upper() or 'ITROOM' in str(room).upper()]
    regular_rooms = [room for room in rooms_list if room not in lab_rooms]
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"🖥️ **IT Labs/Rooms:** {len(lab_rooms)}")
    with col2:
        st.info(f"🏛️ **Regular Rooms:** {len(regular_rooms)}")
    
    # File upload
    st.markdown("---")
    st.subheader("📁 Upload Course Schedule")
    
    uploaded_file = st.file_uploader(
        "Choose an Excel or CSV file",
        type=['xlsx', 'xls', 'csv'],
        help="Upload your course schedule file"
    )
    
    if uploaded_file is not None:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File uploaded successfully! Found {len(df)} courses.")
            
            # Show preview
            with st.expander("📋 Preview uploaded data"):
                st.dataframe(df.head())
            
            # Column mapping
            st.markdown("---")
            st.subheader("🗂️ Column Mapping")
            
            columns = df.columns.tolist()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                program_col = st.selectbox("Program Column", columns, 
                                         index=next((i for i, col in enumerate(columns) if 'program' in col.lower()), 0))
                course_code_col = st.selectbox("Course Code Column", columns,
                                             index=next((i for i, col in enumerate(columns) if 'course' in col.lower() and 'code' in col.lower()), 1))
                course_title_col = st.selectbox("Course Title Column", columns,
                                              index=next((i for i, col in enumerate(columns) if 'title' in col.lower()), 2))
            
            with col2:
                faculty_col = st.selectbox("Faculty Column", columns,
                                         index=next((i for i, col in enumerate(columns) if 'faculty' in col.lower() or 'name' in col.lower()), 3))
                days_col = st.selectbox("Days Column", columns,
                                      index=next((i for i, col in enumerate(columns) if 'day' in col.lower()), 4))
                time_col = st.selectbox("Time Column", columns,
                                      index=next((i for i, col in enumerate(columns) if 'time' in col.lower()), 5))
            
            with col3:
                section_col = st.selectbox("Section Column", columns,
                                         index=next((i for i, col in enumerate(columns) if 'section' in col.lower()), 0))
                students_col = st.selectbox("Students Column", columns,
                                          index=next((i for i, col in enumerate(columns) if 'student' in col.lower()), -1))
            
            # Rename columns for processing
            df_processed = df.rename(columns={
                program_col: 'program',
                course_code_col: 'course_code', 
                course_title_col: 'course_title',
                faculty_col: 'faculty',
                days_col: 'days',
                time_col: 'times',
                section_col: 'section',
                students_col: 'students'
            })
            
            # Process allocation
            if st.button("🎯 Allocate Rooms", type="primary"):
                with st.spinner("Processing room allocation..."):
                    result_df, rooms_needed = allocate_rooms(df_processed, rooms_list)
                
                # Display results
                st.markdown("---")
                st.subheader("📊 Allocation Results")
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Courses", len(result_df))
                
                with col2:
                    allocated_count = len(result_df[~result_df['allocated_room'].isin(['ROOM REQUIRED', 'INVALID TIME SLOT'])])
                    st.metric("Rooms Allocated", allocated_count)
                
                with col3:
                    st.metric("Rooms Required", rooms_needed, delta=f"{rooms_needed} additional" if rooms_needed > 0 else None)
                
                with col4:
                    lab_allocated = len(result_df[
                        result_df['allocated_room'].apply(lambda x: 'ITLAB' in str(x).upper() or 'ITROOM' in str(x).upper())
                    ])
                    st.metric("Lab Rooms Used", lab_allocated)
                
                # Show results table
                st.markdown("### 📋 Detailed Allocation")
                
                # Create display dataframe
                display_df = result_df[['program', 'section', 'course_code', 'course_title', 
                                      'faculty', 'days', 'times', 'students', 'allocated_room']].copy()
                
                # Color code the rooms
                def color_room(val):
                    if 'ROOM REQUIRED' in str(val):
                        return 'background-color: #ffebee; color: #c62828'
                    elif 'INVALID' in str(val):
                        return 'background-color: #fff3e0; color: #ef6c00'
                    elif 'ITLAB' in str(val).upper() or 'ITROOM' in str(val).upper():
                        return 'background-color: #e8f5e8; color: #2e7d32'
                    else:
                        return 'background-color: #f3e5f5; color: #7b1fa2'
                
                styled_df = display_df.style.applymap(color_room, subset=['allocated_room'])
                st.dataframe(styled_df, use_container_width=True)
                
                # Download button
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Allocation Results (CSV)",
                    data=csv,
                    file_name=f"room_allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Show conflicts summary
                if rooms_needed > 0:
                    st.warning(f"⚠️ {rooms_needed} additional rooms are needed. Consider:")
                    st.markdown("""
                    - Adding more time slots
                    - Using additional rooms
                    - Splitting large classes
                    - Scheduling some courses online
                    """)
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
    
    # Instructions
    with st.expander("📖 How to use this application"):
        st.markdown("""
        ### Step-by-step guide:
        
        1. **Ensure rooms.csv exists** in the repository with your room list
        2. **Upload your course schedule** (Excel or CSV format)
        3. **Map the columns** to match your data structure
        4. **Click 'Allocate Rooms'** to process the allocation
        5. **Download the results** as CSV
        
        ### Important notes:
        - Courses starting with **MIS, CSC, BDS, SEC** will be prioritized for IT labs/rooms
        - Time conflicts are automatically detected and prevented
        - Invalid time formats will be marked as "INVALID TIME SLOT"
        - When rooms are insufficient, courses will be marked as "ROOM REQUIRED"
        """)

if __name__ == "__main__":
    main()
