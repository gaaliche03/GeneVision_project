import streamlit as st
import re
import io
import base64
from werkzeug.security import check_password_hash
from PIL import Image

from scripts.database import (
    get_user_by_id,
    update_user_profile,
    reset_user_password,
    log_activity,
    users_col
)


def display_profile_page():
    
    st.title("Account Settings")
    
    # check if user is logged in
    if 'user_id' not in st.session_state or not st.session_state['user_id']:
        st.error("You must be logged in to access this page.")
        return
    
    user_id = st.session_state['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        st.error("User not found.")
        return
    
    # display profile photo section
    display_profile_photo_section(user, user_id)
    
    st.markdown("---")
    
    # display section de update username
    display_username_section(user, user_id)
    
    st.markdown("---")

    # display section de change password
    display_password_section(user, user_id)

def display_profile_photo_section(user, user_id):
    st.subheader("Edit Profile Photo")
    
    # Styling for the profile photo section
    st.markdown("""
    <style>
    .profile-photo-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        text-align: center;
    }
    .photo-instructions {
        font-size: 16px;
        color: #6c757d;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    .profile-circular-image {
        width: 160px;
        height: 160px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #e6e6e6;
        margin: 0 auto;
    }
    .preview-circular-image {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #e6e6e6;
    }

    </style>
    """, unsafe_allow_html=True)
    
    # Change column ratio to give more space to the form
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Display current profile photo with circular styling
        st.markdown('<div class="profile-photo-container">', unsafe_allow_html=True)
        
        if 'profile_photo' in user and user['profile_photo']:
            try:
                photo_data = base64.b64decode(user['profile_photo'])
                image = Image.open(io.BytesIO(photo_data))
                
                # Save the image to a bytes buffer
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # Display the image with circular CSS
                st.markdown(f"""
                <img src="data:image/png;base64,{img_str}" class="profile-circular-image" alt="Profile Photo">
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying profile photo: {str(e)}")
                # Use a better default profile icon with circular shape
                st.markdown("""
                <img src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png" 
                     class="profile-circular-image" alt="Default Profile">
                """, unsafe_allow_html=True)
        else:
            # Use a better default profile icon with circular shape
            st.markdown("""
            <img src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png" 
                 class="profile-circular-image" alt="Default Profile">
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:

        
        with st.form(key="photo_form"): 
            # Make the file uploader more prominent
            uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
            
            st.write("")  # Add some spacing
            
            # Preview of uploaded photo before saving with circular shape
            if uploaded_file is not None:
                try:
                    preview_image = Image.open(uploaded_file)
                    preview_col1, preview_col2 = st.columns([1, 2])
                    with preview_col1:
                        st.markdown("### Preview:")
                        
                        # Convert to bytes for preview with circular shape
                        buffered = io.BytesIO()
                        preview_image.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Display larger circular preview
                        st.markdown(f"""
                        <img src="data:image/png;base64,{img_str}" class="preview-circular-image" alt="Preview">
                        """, unsafe_allow_html=True)
                    
                    # Reset file pointer for later use
                    uploaded_file.seek(0)
                except Exception as e:
                    st.error(f"Error previewing image: {str(e)}")
            
            st.write("")  # Add more spacing before buttons
            
            # Buttons with better layout and styling
            button_col1, button_col2, button_col3 = st.columns(3)
            
            with button_col1:
                submit_button = st.form_submit_button(
                    label="✔️ **Validate Photo**", 
                    use_container_width=True,
                    help="Upload a new profile photo"
                )
            
            with button_col3:
                remove_button = st.form_submit_button(
                    label="✖️ **Remove Photo**", 
                    use_container_width=True,
                    help="Remove your current profile photo"
                )
            
            if submit_button and uploaded_file is not None:
                update_result, message = update_profile_photo(user_id, uploaded_file)
                
                if not update_result:
                    st.error(message)
                else:
                    st.success("Profile photo updated successfully!")
                    # Add a small delay to ensure the image is processed
                    import time
                    time.sleep(2)
                    st.experimental_rerun()
            
            if remove_button:
                update_result, message = remove_profile_photo(user_id)
                
                if not update_result:
                    st.error(message)
                else:
                    st.success("Profile photo removed successfully!")
                    st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


# Fonctions à remplacer dans account_settings.py pour le traitement des photos

def update_profile_photo(user_id, uploaded_file):
    try:
        # Open the uploaded image
        image = Image.open(uploaded_file)
        
        # Convert to RGB if the image is in RGBA mode (handles PNG transparency)
        if image.mode == 'RGBA':
            # Create a white background image
            background = Image.new('RGB', image.size, (255, 255, 255))
            # Paste the image on the background
            background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Make the image square by cropping to a square from the center
        width, height = image.size
        if width != height:
            # Determine the size of the square (min of width/height)
            new_size = min(width, height)
            # Calculate coordinates for cropping from center
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            
            # Crop the image
            image = image.crop((left, top, right, bottom))
        
        # Resize image to standard size (150x150 px)
        image = image.resize((150, 150), Image.LANCZOS)  # LANCZOS is better quality than the default
        
        # Convert to bytes
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=90)  # Use higher quality
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Update the profile photo in database
        result = update_user_profile(user_id, {"profile_photo": img_str})
        
        if result:
            # Log the profile photo update
            log_activity(user_id, "profile_photo_update", "Updated profile photo")
            return True, "Profile photo updated successfully!"
        else:
            return False, "Failed to update profile photo."
    except Exception as e:
        return False, f"Error updating profile photo: {str(e)}"

def remove_profile_photo(user_id):
    try:
        # Set the profile_photo field to None
        result = update_user_profile(user_id, {"profile_photo": None})
        
        if result:
            # Log the profile photo removal
            log_activity(user_id, "profile_photo_remove", "Removed profile photo")
            return True, "Profile photo removed successfully!"
        else:
            return False, "Failed to remove profile photo."
    except Exception as e:
        return False, f"Error removing profile photo: {str(e)}"

# display section de update username
def display_username_section(user, user_id):
    
    st.subheader("Profile Information")
    
    # get current user information
    current_username = user.get("username", "")
    current_email = user.get("email", "")
    
    with st.form(key="username_form"):
        # Username field
        new_username = st.text_input("Username", value=current_username)
        
        # Email field (readonly as it's the login ID)
        st.text_input("Email", value=current_email, disabled=True)
        
        st.write("")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col3:
            # update username btn
            submit_button = st.form_submit_button(label="👤 **Update Username**",use_container_width=True)
        
        if submit_button:
            if new_username != current_username:
                update_result, message = update_username(user_id, new_username)
                
                if not update_result:
                    st.error(message)
                else:
                    st.success("Username updated successfully!")
                    st.experimental_rerun()
            else:
                st.info("No changes detected.")

#fonction de update username
def update_username(user_id, new_username):
    # Validate username
    if not is_valid_username(new_username):
        return False, "Username must be 3-30 characters and contain only letters, numbers, underscores, and hyphens."
    
    try:
        # Check if username already exists
        if users_col.find_one({"username": new_username, "_id": {"$ne": user_id}}):
            return False, "Username already taken."
        
        # Update the username
        result = update_user_profile(user_id, {"username": new_username})
        
        if result:
            # Log the username change
            log_activity(user_id, "username_update", f"Username changed to {new_username}")
            return True, "Username updated successfully!"
        else:
            return False, "Failed to update username."
    except Exception as e:
        st.error(f"Error updating username: {str(e)}")
        return False, f"Error updating username: {str(e)}"

#fonction de validation de username (num caracteres..)
def is_valid_username(username):
    # Username must be 3-30 chars and contain only letters, numbers, underscores, and hyphens
    if not username or len(username) < 3 or len(username) > 30:
        return False
    
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, username))

#fonction de validation de password
def is_valid_password(password):
   
    # longueur de pwd
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    
    # min 2 digits
    if sum(c.isdigit() for c in password) < 2:
        return False, "Password must contain at least 2 digits."
    
    # min 1 special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must include at least 1 special character."
    
    return True, "Password meets requirements."

#display and change pwd
def display_password_section(user, user_id):
    
    st.subheader("Change Password")
    
    with st.form(key="password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col3:
            submit_button = st.form_submit_button(label="🔒 **Change Password**",use_container_width=True)
        
        if submit_button:
            if not current_password or not new_password or not confirm_password:
                st.error("All fields are required.")
                
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                # Validate password requirements
                is_valid, message = is_valid_password(new_password)
                if not is_valid:
                    st.error(message)
                else:
                    # Verify current password first
                    
                    if not check_password_hash(user["password_hash"], current_password):
                        st.error("Current password is incorrect.")
                    else:
                        # Reset password
                        if reset_user_password(user["email"], new_password):
                            st.success("Password changed successfully!")
                            log_activity(user_id, "password_change", "Changed password")
                        else:
                            st.error("Failed to change password.")