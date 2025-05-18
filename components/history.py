import streamlit as st
from datetime import datetime, timedelta
import os

# Import the report generation function
from scripts.rapport_results import generate_genevision_report
# Import functions from database.py
from scripts.database import (
    get_user_sequences,
    get_sequence,
    get_sequence_results,
    get_sequence_reports,
    delete_sequence,
    get_activity_statistics,
    create_report
)

def display_history_page():
    """Main function for displaying the history page"""
    
    st.title("Sequence Analysis History")
    
    # Check if user is logged in
    if 'user_id' not in st.session_state or not st.session_state['user_id']:
        st.error("You must be logged in to access this page.")
        return
    
    user_id = st.session_state['user_id']
    
    # Display Usage Summary at the top
    display_usage_summary(user_id)
    
    # Display Sequences section
    display_sequences_section(user_id)


def display_usage_summary(user_id):
    """Display usage summary section with metrics"""
    
    st.subheader("Usage Summary")
    
    # Get statistics and sequences for metrics
    stats = get_activity_statistics(user_id)
    sequences = get_user_sequences(user_id, limit=100)
    
    # Process stats data
    stats_data = {}
    if stats:
        for item in stats:
            action_type = item.get("_id")
            count = item.get("count", 0)
            stats_data[action_type] = count
    
    # Calculate metrics
    total_sequences = len(sequences) if sequences else 0
    completed = sum(1 for s in sequences if s.get("status") == "completed") if sequences else 0
    total_activities = sum(stats_data.values()) if stats_data else 0
    completion_rate = round((completed / total_sequences) * 100, 1) if total_sequences > 0 else 0
    
    # Apply CSS for the cards
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px 10px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-title {
        color: #6c757d;
        font-size: 14px;
        margin-bottom: 10px;
    }
    .metric-value-container {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .metric-icon {
        font-size: 22px;
        margin-right: 8px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display metrics in 4 columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        col1.markdown(f"""
        <div class="metric-card">
            <p class="metric-title">Total Sequences</p>
            <div class="metric-value-container">
                <span class="metric-icon">🧬</span>
                <span class="metric-value">{total_sequences}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        col2.markdown(f"""
        <div class="metric-card">
            <p class="metric-title">Completed Analyses</p>
            <div class="metric-value-container">
                <span class="metric-icon">✅</span>
                <span class="metric-value">{completed}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        col3.markdown(f"""
        <div class="metric-card">
            <p class="metric-title">Total Activities</p>
            <div class="metric-value-container">
                <span class="metric-icon">📊</span>
                <span class="metric-value">{total_activities}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        col4.markdown(f"""
        <div class="metric-card">
            <p class="metric-title">Completion Rate</p>
            <div class="metric-value-container">
                <span class="metric-icon">📈</span>
                <span class="metric-value">{completion_rate}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")


#afficher les sequences de user avec option de filtrage
def display_sequences_section(user_id):
    
    
    st.subheader("My Analyzed Sequences")
    
    # Filter options in rows
    col1, col2,col3 = st.columns(3)
    
    with col1:
        limit_value = st.text_input(
            "Maximum sequences to display",
            placeholder="10",
            key="limit_value"
        )

    with col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Most recent", "Oldest"],
            key="sort_option"
        )
    
    
    with col3:
        time_filter = st.selectbox(
            "Time period",
            ["All", "Custom period"],
            key="time_filter"
        )
    
    # Time filter row
    col1, col2= st.columns(2)

    # Show date selectors only if Custom period is selected
    start_date = None
    end_date = None
    
    if time_filter == "Custom period":
        with col1:
            start_date = st.date_input(
                "Start date",
                value=datetime.now() - timedelta(days=30),
                key="start_date"
            )
        
        with col2:
            end_date = st.date_input(
                "End date",
                value=datetime.now(),
                key="end_date"
            )
  
    # Convert limit to integer with validation
    try:
        limit = int(limit_value) if limit_value.strip() else 10
        if limit <= 0:
            st.warning("Please enter a positive number")
            limit = 10
    except ValueError:
        st.warning("Please enter a valid number")
        limit = 10
    
    # Retrieve sequences
    all_sequences = get_user_sequences(user_id, limit=limit)
    
    # Filter by status "analyzed"
    analyzed_sequences = [seq for seq in all_sequences if seq.get("status", "").lower() == "analyzed"]
    
    # Apply time filter
    if time_filter == "Custom period" and start_date and end_date:
        # Convert date objects to datetime for proper comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        # Add one day to end_date to include the entire end date (until 23:59:59)
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Check if end date is before start date
        if end_date < start_date:
            st.warning("End date cannot be before start date")
            filtered_sequences = analyzed_sequences
        else:
            filtered_sequences = [
                seq for seq in analyzed_sequences 
                if start_datetime <= seq.get("created_at", datetime.min) <= end_datetime
            ]
    else:
        filtered_sequences = analyzed_sequences
    
    # Apply sorting
    if sort_option == "Most recent":
        filtered_sequences = sorted(filtered_sequences, key=lambda x: x.get("created_at", datetime.min), reverse=True)
    elif sort_option == "Oldest":
        filtered_sequences = sorted(filtered_sequences, key=lambda x: x.get("created_at", datetime.min))

    
    # Display sequences
    if not filtered_sequences:
        if time_filter == "Custom period":
            st.info(f"No analyzed sequences found between {start_date} and {end_date}.")
        else:
            st.info("No analyzed sequences found.")
    else:
        # Display number of sequences
        date_range_msg = f" between {start_date} and {end_date}" if time_filter == "Custom period" else ""
        st.write(f"**{len(filtered_sequences)}** analyzed sequences found{date_range_msg}")
        
        # Display sequences as cards
        for i, seq in enumerate(filtered_sequences):
            display_sequence_card(seq, i, user_id)


#card de chaque sequence qui contient les options et les détails
def display_sequence_card(seq, index, user_id):
    
    # Basic information
    seq_id = seq.get("_id")
    status = seq.get("status", "unknown")
    created_at = seq.get("created_at", datetime.utcnow()).strftime("%m/%d/%Y %H:%M")
    
    # Create the card
    with st.expander(f"Sequence #{index+1} - {created_at}", expanded=(index == 0)):
        # Top section with basic info and download button
        info_cols = st.columns([2, 1])
        
        with info_cols[0]:
            # Basic sequence information in left column
            st.markdown(f"**ID:** <span style='color:#4CAF50; font-family:monospace;'>{seq_id}</span>", unsafe_allow_html=True)
            st.markdown(f"**Date:** {created_at}")
            st.markdown(f"**Status:** {status.capitalize()}")
        
        with info_cols[1]:
            # Download button in right column
            if status.lower() == "analyzed" or status.lower() == "completed":
                reports = get_sequence_reports(seq_id)
                
                if reports:
                    # Find the report with standard_pdf type
                    pdf_report = None
                    for report in reports:
                        if report.get("type") in ["standard_pdf", "standard_pdf₂"]:
                            pdf_report = report
                            break
                    
                    if pdf_report:
                        content = pdf_report.get("content", {})
                        report_path = None
                        
                        if isinstance(content, dict):
                            report_path = content.get("report_path")
                        
                        if report_path and os.path.exists(os.path.normpath(report_path)):
                            try:
                                with open(os.path.normpath(report_path), "rb") as file:
                                    pdf_data = file.read()
                                
                                st.download_button(
                                    label="📄 **Download Report**",
                                    data=pdf_data,
                                    file_name=f"sequence_report_{seq_id}.pdf",
                                    mime="application/pdf",
                                    help="Download the analysis report for this sequence",
                                    key=f"download_report_{seq_id}",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Error reading report file: {str(e)}")
        
        # Add horizontal separator
        st.markdown("<hr style='margin-top: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        
        # Middle section - Sequence preview (full width)
        st.markdown("### Sequence Preview")
        content = seq.get("content", "")
        if content:
            # Format as a bioinformatics sequence
            content = content[:180] + "..." if len(content) > 180 else content
            
            st.code(content)
        
        # Add horizontal separator
        st.markdown("<hr style='margin-top: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        
        # Bottom section - Delete sequence (full width)
        st.markdown("### Delete Sequence")
        
        # Custom layout for the confirmation input and delete button
        delete_cols = st.columns([2, 1])
        
        with delete_cols[0]:
            # Input field without label (since we added the label manually above)
            confirmation_text = st.text_input("", 
                                            key=f"confirm_delete_{seq_id}", placeholder="Type 'DELETE' to confirm and remove this sequence",
                                            label_visibility="collapsed")
        
        with delete_cols[1]:
            # Use a container to adjust vertical alignment
            delete_container = st.container()
            delete_disabled = confirmation_text != "DELETE"
            
            # The delete button
            if delete_container.button("🗑️ **Delete**", 
                                     key=f"delete_{seq_id}", 
                                     disabled=delete_disabled,
                                     use_container_width=True):
                if delete_sequence(seq_id, user_id):
                    st.success("Sequence deleted successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Failed to delete sequence.")

#genérer rapport pdf du sequence
def generate_sequence_report_for_download(seq_id, user_id):
    
    # Get sequence data
    sequence = get_sequence(seq_id)
    if not sequence:
        st.error("Sequence not found")
        return None
    
    # Get analysis results
    results = get_sequence_results(seq_id)
    if not results:
        st.error("No analysis results available for this sequence")
        return None
    
    # Use the first result
    analysis_data = results[0].get("data", {})
    
    # Generate a filename using OS-independent path joining
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("reports")
    os.makedirs(output_dir, exist_ok=True)  # Ensure directory exists
    output_filename = f"genevision_report_{seq_id}_{timestamp}.pdf"
    output_path = os.path.join(output_dir, output_filename)
    
    # Generate the report
    try:
        report_path = generate_genevision_report(analysis_data, output_path)
        
        # Save report information to database with normalized path
        report_content = {"report_path": os.path.normpath(report_path)}
        create_report(seq_id, report_content)
        
        # Read the file for download
        with open(report_path, "rb") as file:
            pdf_data = file.read()
        
        # Return the data for download
        return pdf_data
        
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None
