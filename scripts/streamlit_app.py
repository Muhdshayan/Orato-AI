import streamlit as st
import os
import sys
import subprocess
import uuid
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the video preprocessing function
from python_modules.Preprocessor.video_preprocessing import process_video, get_pg_conn
import psycopg2
from psycopg2.extras import RealDictCursor

def create_user(name: str, email: str) -> str:
    """Create a new user and return the user_id"""
    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING user_id
                """,
                (name, email, "temp_hash")  # You might want to implement proper password hashing
            )
            row = cur.fetchone()
            conn.commit()
            return row["user_id"]
    finally:
        conn.close()

def user_exists(user_id: str) -> bool:
    """Check if a user exists"""
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone() is not None
    finally:
        conn.close()

# Page configuration
st.set_page_config(
    page_title="OratoAI - Video Preprocessing",
    page_icon="🎥",
    layout="wide"
)

# Title and description
st.title("🎥 OratoAI Video Preprocessing")
st.markdown("Upload your video for analysis and feedback generation")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Database connection test
    st.subheader("Database Status")
    try:
        conn = get_pg_conn()
        conn.close()
        st.success("✅ Database Connected")
    except Exception as e:
        st.error(f"❌ Database Error: {str(e)}")
    
    # MinIO connection test
    st.subheader("MinIO Status")
    try:
        from python_modules.Preprocessor.video_preprocessing import get_minio_client, ensure_bucket
        minio_client = get_minio_client()
        bucket = os.getenv("MINIO_MEDIA_BUCKET", "orato-media")
        ensure_bucket(minio_client, bucket)
        st.success("✅ MinIO Connected")
    except Exception as e:
        st.error(f"❌ MinIO Error: {str(e)}")

# Main form
st.header("📁 Video Upload")

col1, col2 = st.columns(2)

with col1:
    # Video file path input
    video_path = st.text_input(
        "Video File Path",
        placeholder="C:\\path\\to\\your\\video.mp4",
        help="Enter the full path to your MP4 video file"
    )
    
    # File validation
    if video_path:
        if not os.path.exists(video_path):
            st.error("❌ File not found. Please check the path.")
        elif not video_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            st.warning("⚠️ File should be a video format (MP4, AVI, MOV, MKV)")
        else:
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            st.info(f"📊 File size: {file_size:.2f} MB")

with col2:
    # Declared topic input
    declared_topic = st.text_input(
        "Presentation Topic",
        placeholder="e.g., Climate Change Solutions",
        help="What is your presentation about?"
    )
    
    # User ID input with options
    st.subheader("User Identification")
    user_option = st.radio(
        "Choose user option:",
        ["Use existing User ID", "Create new user"]
    )
    
    if user_option == "Use existing User ID":
        user_id = st.text_input(
            "User ID (UUID)",
            placeholder="12345678-1234-1234-1234-123456789012",
            help="Enter an existing user UUID"
        )
        if user_id and not user_exists(user_id):
            st.error("❌ User ID not found in database")
    else:
        # Create new user form
        st.write("**Create New User**")
        user_name = st.text_input(
            "Full Name",
            placeholder="John Doe",
            help="Enter your full name"
        )
        user_email = st.text_input(
            "Email Address",
            placeholder="john.doe@example.com",
            help="Enter your email address"
        )
        
        if st.button("Create User"):
            if user_name and user_email:
                try:
                    new_user_id = create_user(user_name, user_email)
                    st.session_state.new_user_id = new_user_id
                    st.success(f"✅ User created successfully! ID: {new_user_id}")
                except Exception as e:
                    st.error(f"❌ Error creating user: {str(e)}")
            else:
                st.error("❌ Please fill in both name and email")
        
        user_id = st.text_input(
            "User ID",
            value=st.session_state.get('new_user_id', ''),
            help="User ID will appear here after creation"
        )

# Processing options
st.subheader("⚙️ Processing Options")
col3, col4 = st.columns(2)

with col3:
    max_duration = st.number_input(
        "Max Duration (seconds)",
        min_value=60,
        max_value=600,
        value=300,
        help="Maximum allowed video duration"
    )

with col4:
    language = st.selectbox(
        "Expected Language",
        ["en", "es", "fr", "de", "it"],
        help="Language for speech recognition"
    )

# Submit button
submitted = st.button("🚀 Process Video", use_container_width=True)

# Process video when form is submitted
if submitted:
    if not all([video_path, declared_topic, user_id]):
        st.error("❌ Please fill in all required fields")
    elif not os.path.exists(video_path):
        st.error("❌ Video file not found. Please check the path.")
    else:
        # Set environment variables for this session
        os.environ["MAX_DURATION_SECONDS"] = str(max_duration)
        os.environ["SUPPORTED_LANGUAGE"] = language
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Validation
            status_text.text("🔍 Validating video file...")
            progress_bar.progress(20)
            
            # Step 2: Processing
            status_text.text("⚙️ Processing video (duration & language check)...")
            progress_bar.progress(40)
            
            # Step 3: Splitting
            status_text.text("✂️ Splitting video and audio...")
            progress_bar.progress(60)
            
            # Step 4: Uploading
            status_text.text("☁️ Uploading to MinIO...")
            progress_bar.progress(80)
            
            # Step 5: Database
            status_text.text("💾 Saving to database...")
            progress_bar.progress(90)
            
            # Call the processing function
            process_video(video_path, declared_topic, user_id)
            
            # Success
            progress_bar.progress(100)
            status_text.text("✅ Processing completed successfully!")
            
            st.success("🎉 Video processed successfully!")
            st.balloons()
            
            # Show results
            st.subheader("📊 Processing Results")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Status", "✅ Complete")
            with col2:
                st.metric("Duration Check", "✅ Passed")
            with col3:
                st.metric("Language Check", "✅ Passed")
            
            # Show next steps
            st.info("""
            **Next Steps:**
            1. Your video has been uploaded to MinIO
            2. Video and audio have been separated
            3. Database record created
            4. Ready for ASR and CV analysis
            """)
            
        except Exception as e:
            progress_bar.progress(0)
            status_text.text("❌ Processing failed")
            st.error(f"❌ Error: {str(e)}")
            
            # Show error details
            with st.expander("Error Details"):
                st.code(str(e))

# Footer
st.markdown("---")
st.markdown("**OratoAI** - AI-powered presentation analysis and feedback")
st.markdown("*Built with Streamlit and Python*")

# Instructions
with st.expander("📖 How to use"):
    st.markdown("""
    **Step 1:** Enter the full path to your MP4 video file
    **Step 2:** Describe what your presentation is about
    **Step 3:** Choose an existing user ID or generate a new one
    **Step 4:** Adjust processing options if needed
    **Step 5:** Click "Process Video" to start analysis
    
    **Requirements:**
    - Video must be MP4, AVI, MOV, or MKV format
    - Duration must be under the specified limit
    - Video must have an audio track
    - Audio should be in the selected language
    """)

# System status
with st.expander("🔧 System Status"):
    st.subheader("Environment Variables")
    
    env_vars = [
        "PGHOST", "PGPORT", "PGUSER", "PGDATABASE",
        "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_MEDIA_BUCKET",
        "MAX_DURATION_SECONDS", "SUPPORTED_LANGUAGE"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "Not set")
        if "PASSWORD" in var or "KEY" in var:
            value = "***" if value != "Not set" else value
        st.text(f"{var}: {value}")
