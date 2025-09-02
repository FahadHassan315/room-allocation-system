import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
import io
import random

# Page configuration
st.set_page_config(
    page_title="Hafali Smart Allocation System",
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
    """Check if course needs IT lab/room - only MIS, CSC, BDS, SEC"""
    if pd.isna(course_code):
        return False
    
    course_code = str(course_code).upper().strip()
    lab_prefixes = ['MIS', 'CSC', 'BDS', 'SEC']
    
    return any(course_code.startswith(prefix) for prefix in lab_prefixes)

def is_lab_room(room_name):
    """Check if room is an IT lab or IT room"""
    room_str = str(room_name).upper()
    return 'IT LAB' in room_str or 'ITROOM' in room_str or 'IT_LAB' in room_str or 'IT_ROOM' in room_str

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
    elif 'CREEK' in room_str or 'CRK' in room_str:
        return 5
    elif 'CHS' in room_str:
        return 6  # Lowest priority
    else:
        return 7  # Unknown rooms get lowest priority

def get_room_category(room_name):
    """Get room category for pie chart"""
    room_str = str(room_name).upper()
    
    if 'CBM' in room_str:
        return 'CBM Rooms'
    elif 'SSK' in room_str:
        return 'SSK Rooms'
    elif 'I.MGMT' in room_str or 'IMGMT' in room_str:
        return 'I.MGMT Rooms'
    elif 'LIB' in room_str:
        return 'Library Rooms'
    elif 'CREEK' in room_str or 'CRK' in room_str:
        return 'Creek Rooms'
    elif 'CHS' in room_str:
        return 'CHS Rooms'
    elif 'IT LAB' in room_str or 'ITROOM' in room_str or 'IT_LAB' in room_str or 'IT_ROOM' in room_str:
        return 'IT Labs'
    else:
        return 'Other Rooms'

def create_room_distribution_chart(rooms_list):
    """Create a chart showing room distribution by category using native Streamlit"""
    # Count rooms by category
    room_categories = {}
    for room in rooms_list:
        category = get_room_category(room)
        room_categories[category] = room_categories.get(category, 0) + 1
    
    # Create dataframe for chart
    chart_data = pd.DataFrame({
        'Category': list(room_categories.keys()),
        'Count': list(room_categories.values())
    })
    
    # Sort by count for better visualization
    chart_data = chart_data.sort_values('Count', ascending=False)
    
    return chart_data, room_categories

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
    """Main room allocation function with priority-based room distribution"""
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
    
    # Separate lab and regular rooms
    lab_rooms = [room for room in rooms_list if is_lab_room(room)]
    regular_rooms = [room for room in rooms_list if not is_lab_room(room)]
    
    # Track room assignments by time slot
    room_schedule = {room: [] for room in rooms_list}
    
    # Track which rooms have been recently allocated to encourage variety
    recently_allocated = set()
    allocation_counter = 0
    
    # Process courses in original order (no grouping)
    allocated_courses = []
    rooms_required_count = 0
    
    for index, course in df.iterrows():
        time_slot = course['parsed_time_slot']
        course_code = course.get('course_code', course.get('Course Code', ''))
        
        # Create course dictionary with new columns
        course_dict = {
            'program': course.get('program', course.get('Program', '')),
            'section': course.get('section', course.get('Section', '')),
            'course_code': course_code,
            'course_title': course.get('course_title', course.get('Course Title', '')),
            'faculty': course.get('name', course.get('Faculty', course.get('Name', ''))),
            'days': course.get('days', course.get('Days', '')),
            'times': course.get("time's", course.get('times', course.get('Time', ''))),
            'students': course.get('total student strength', course.get('Students', 0)),
            'semester': course.get('semester_selected', course.get('Semester', '')),
            'catalog_year': course.get('catalog_year', course.get('Catalog Year', '')),
            'allocated_room': None
        }
        
        # Skip courses with invalid time slots
        if not time_slot:
            course_dict['allocated_room'] = 'INVALID TIME SLOT'
            allocated_courses.append(course_dict)
            continue
        
        # Get prioritized room list with variety
        if needs_lab_room(course_code):
            # For lab courses: prioritized labs first, then prioritized regular rooms
            lab_rooms_prioritized = distribute_rooms_by_priority(lab_rooms, recently_allocated)
            regular_rooms_prioritized = distribute_rooms_by_priority(regular_rooms, recently_allocated)
            preferred_rooms = lab_rooms_prioritized + regular_rooms_prioritized
        else:
            # For regular courses: prioritized regular rooms first, then prioritized labs
            regular_rooms_prioritized = distribute_rooms_by_priority(regular_rooms, recently_allocated)
            lab_rooms_prioritized = distribute_rooms_by_priority(lab_rooms, recently_allocated)
            preferred_rooms = regular_rooms_prioritized + lab_rooms_prioritized
        
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
            course_dict['allocated_room'] = 'ROOM REQUIRED'
            rooms_required_count += 1
        
        allocated_courses.append(course_dict)
        
        # Clear recently allocated set every 8 courses to allow room reuse
        # but encourage variety within small batches
        if allocation_counter % 8 == 0:
            recently_allocated.clear()
    
    return pd.DataFrame(allocated_courses), rooms_required_count

def main():
    st.title("🏫 Hafali Smart Allocation System")
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
    
    # Show room categories with priority explanation and charts
    lab_rooms = [room for room in rooms_list if is_lab_room(room)]
    regular_rooms = [room for room in rooms_list if not is_lab_room(room)]
    
    # Create room distribution chart
    if rooms_list:
        st.markdown("### 📊 Room Distribution")
        
        chart_data, room_categories = create_room_distribution_chart(rooms_list)
        
        # Display bar chart
        st.bar_chart(chart_data.set_index('Category'))
        
        # Display statistics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🏛️ Room Categories:**")
            for category, count in room_categories.items():
                percentage = (count / len(rooms_list)) * 100
                st.write(f"• **{category}:** {count} rooms ({percentage:.1f}%)")
        
        with col2:
            st.info(f"🖥️ **IT Labs/Rooms:** {len(lab_rooms)}")
            if lab_rooms:
                with st.expander("View IT Labs/Rooms"):
                    for room in lab_rooms[:10]:  # Show first 10
                        st.write(f"• {room}")
                    if len(lab_rooms) > 10:
                        st.write(f"... and {len(lab_rooms) - 10} more")
        
        with col3:
            st.info(f"🏛️ **Regular Rooms:** {len(regular_rooms)}")
            if regular_rooms:
                with st.expander("View Regular Rooms (Priority Order)"):
                    st.markdown("**Priority 1 (Highest):** CBM rooms")
                    st.markdown("**Priority 2:** SSK rooms") 
                    st.markdown("**Priority 3:** I.MGMT rooms")
                    st.markdown("**Priority 4:** Library rooms (LIB)")
                    st.markdown("**Priority 5:** CREEK rooms")
                    st.markdown("**Priority 6 (Lowest):** CHS rooms")
                    st.write("---")
                    for room in regular_rooms[:15]:  # Show first 15
                        priority = get_room_priority_group(room)
                        st.write(f"• {room} (Priority {priority})")
                    if len(regular_rooms) > 15:
                        st.write(f"... and {len(regular_rooms) - 15} more")
    
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
                
                with col3:
                    catalogs = len(uploaded_files)
                    st.metric("Catalogs Combined", catalogs)
            
            if len(combined_df) > 0:
                st.success(f"✅ Successfully combined {len(uploaded_files)} files into {len(combined_df)} total courses!")
                
                # Show preview
                with st.expander("📋 Preview combined data"):
                    preview_columns = ['program', 'course_code', 'course_title', 'days', "time's"]
                    if 'semester_selected' in combined_df.columns:
                        preview_columns.insert(-2, 'semester_selected')
                    if 'catalog_year' in combined_df.columns:
                        preview_columns.insert(-2, 'catalog_year')
                    
                    preview_df = combined_df[preview_columns].head(10)
                    st.dataframe(preview_df)
                    if len(combined_df) > 10:
                        st.write(f"... and {len(combined_df) - 10} more courses from all catalogs")
                
                # Process allocation
                if st.button("🎯 Allocate Rooms for All Catalogs", type="primary"):
                    with st.spinner("Processing room allocation for combined catalogs..."):
                        result_df, rooms_needed = allocate_rooms(combined_df, rooms_list)
                    
                    # Display results
                    st.markdown("---")
                    st.subheader("📊 Allocation Results (All Catalogs Combined)")
                    
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
                            result_df['allocated_room'].apply(lambda x: is_lab_room(str(x)))
                        ])
                        st.metric("Lab Rooms Used", lab_allocated)
                    
                    # Show results table
                    st.markdown("### 📋 Detailed Allocation")
                    
                    # Create display dataframe (removed source_file column)
                    display_columns = ['program', 'section', 'course_code', 'course_title', 
                                     'faculty', 'days', 'times', 'students', 'semester', 
                                     'catalog_year', 'allocated_room']
                    
                    # Only include columns that exist in the dataframe
                    available_columns = []
                    for col in display_columns:
                        if col in result_df.columns:
                            available_columns.append(col)
                    
                    display_df = result_df[available_columns].copy()
                    
                    # Color code the rooms
                    def highlight_rooms(val):
                        if 'ROOM REQUIRED' in str(val):
                            return 'background-color: #ffebee; color: #c62828'
                        elif 'INVALID' in str(val):
                            return 'background-color: #fff3e0; color: #ef6c00'
                        elif is_lab_room(str(val)):
                            return 'background-color: #e8f5e8; color: #2e7d32'
                        else:
                            return 'background-color: #f3e5f5; color: #7b1fa2'
                    
                    # Apply styling and display
                    styled_df = display_df.style.map(highlight_rooms, subset=['allocated_room'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Download button
                    csv = result_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Combined Allocation Results (CSV)",
                        data=csv,
                        file_name=f"combined_room_allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # Show conflicts summary
                    if rooms_needed > 0:
                        st.warning(f"⚠️ {rooms_needed} additional rooms are needed across all catalogs. Consider:")
                        st.markdown("""
                        - Adding more time slots
                        - Using additional rooms  
                        - Splitting large classes
                        - Scheduling some courses online
                        - Staggering catalog schedules if possible
                        """)
            
            else:
                st.error("❌ No valid data found in uploaded files.")
        
        except Exception as e:
            st.error(f"❌ Error processing files: {str(e)}")

if __name__ == "__main__":
    main()
