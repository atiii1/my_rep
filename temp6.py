import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import os
import re
import bcrypt
import streamlit_authenticator as stauth

# Clear session state to avoid referencing old credentials
if 'authenticator' not in st.session_state:
    st.session_state['authenticator'] = None

# Define user credentials
names = ["Admin User"]
usernames = ["admin"]
passwords = ["hbfb"]

# Hash passwords using bcrypt
hashed_passwords = [bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode() for password in passwords]

# Create a dictionary for credentials
credentials = {
    "usernames": {
        "admin": {"name": "Admin User", "password": hashed_passwords[0]},
    }
}

# Initialize the authenticator
if st.session_state['authenticator'] is None:
    authenticator = stauth.Authenticate(
        credentials,
        "some_cookie_name",
        "some_signature_key",
        cookie_expiry_days=3
    )
    st.session_state['authenticator'] = authenticator
else:
    authenticator = st.session_state['authenticator']

# Custom fields for login
fields = {
    "Form name": "Login",
    "Username": "Username",
    "Password": "Password",
    "Login": "Login"
}

# Login widget with fields parameter
name, authentication_status, username = authenticator.login("main", fields=fields)

if authentication_status:
    # Set the theme
    st.set_page_config(
        page_title="Temperature Coefficient Calculation App",
        page_icon="🌡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # Load the image
    logo = Image.open("hf_logo.png")

    # Display the image at the top of the app
    st.image(logo, width=200)  # Adjust the width as needed

    # Apply Seaborn theme
    sns.set_theme(style="darkgrid")

    # Function to process uploaded file and detect intervals
    def process_file(df, time_col, Power_col, Tc_col, Tm_col, active_Temp_col, tolerance, cooling_s, manual_Tc, manual_Tm, use_manual):
        # Ensure the time column is treated as float
        df[time_col] = df[time_col].astype(float)
        
        # Sorting by time column to ensure data is in chronological order
        df = df.sort_values(by=time_col).reset_index(drop=True)

        results = []
        start_index = 0
        while start_index < len(df):
            start_time = df[time_col].iloc[start_index]
            active_Temp_value = df[active_Temp_col].iloc[start_index]
            
            # Find the end of the phase where Active Temp is constant within the tolerance
            end_index = start_index
            while end_index < len(df) and abs(df[active_Temp_col].iloc[end_index] - active_Temp_value) <= tolerance:
                end_index += 1

            end_time = df[time_col].iloc[end_index - 1]
            duration = (end_time - start_time)

            if duration >= 10:
                # Calculate mean values during this interval
                interval_data = df.iloc[start_index:end_index]
                mean_Power = interval_data[Power_col].mean()
                
                if Tc_col:
                    mean_Tc = interval_data[Tc_col].mean()
                else:
                    mean_Tc = manual_Tc

                if Tm_col:
                    mean_Tm = interval_data[Tm_col].mean()
                else:
                    mean_Tm = manual_Tm

                if mean_Tc is None or mean_Tm is None:
                    st.error(f"Error: mean_Tc or mean_Tm is None. mean_Tc: {mean_Tc}, mean_Tm: {mean_Tm}")
                    continue

                alpha = (mean_Power * 1000) / (cooling_s * (mean_Tc - mean_Tm))
                results.append({
                    'Active Temp': active_Temp_value,
                    'interval_start': start_time,
                    'interval_end': end_time,
                    'Power values': interval_data[Power_col].tolist(),
                    'mean of Power': mean_Power,
                    'mean of Tc': mean_Tc,
                    'mean of Tm': mean_Tm,
                    'alpha': alpha
                })

            # Move to the next phase
            start_index = end_index

        return results

    # Custom function to deduplicate column names
    def deduplicate_columns(columns):
        seen = {}
        new_columns = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                new_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                new_columns.append(col)
        return new_columns

    # Title of the app
    st.title('Temperature Coefficient Calculation App 🌡️')

    # Sidebar settings
    st.sidebar.header('Settings')
    uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])

    if uploaded_file is not None:
        # Read the uploaded file
        df = pd.read_excel(uploaded_file)
        st.write("Uploaded Data:")
        st.dataframe(df.head())

        # Ensure all column names are unique
        df.columns = deduplicate_columns(df.columns.tolist())
        
        # Drop the first row
        df = df.drop(0).reset_index(drop=True)

        # Column selection
        time_col = st.sidebar.selectbox("Select the time column", df.columns)
        Power_col = st.sidebar.selectbox("Select the Power column", df.columns)
        active_Temp_col = st.sidebar.selectbox("Select the Active Temp column", df.columns)

        # Option to select column or manual input for Compound Temp
        Tc_option = st.sidebar.radio("Select Compound Temp input method", ["Select column", "Manual input"])
        if Tc_option == "Select column":
            Compound_Temp_col = st.sidebar.selectbox("Select the Compound Temp column", df.columns)
            manual_Tc = None
        else:
            manual_Tc = st.sidebar.number_input("Enter the Compound Temp value", value=0.0)
            Compound_Temp_col = None

        # Option to select column or manual input for Machine Temp
        Tm_option = st.sidebar.radio("Select Machine Temp input method", ["Select column", "Manual input"])
        if Tm_option == "Select column":
            Machine_Temp_col = st.sidebar.selectbox("Select the Machine Temp column", df.columns)
            manual_Tm = None
        else:
            manual_Tm = st.sidebar.number_input("Enter the Machine Temp value", value=0.0)
            Machine_Temp_col = None

        tolerance = st.sidebar.number_input("Enter the tolerance for Active Temp", min_value=0.0, value=0.0)
        cooling_s = st.sidebar.number_input("Enter the Cooling Surface", min_value=0.0, value=0.0)

        if st.sidebar.button("Calculate"):
            use_manual = (Tc_option == "Manual input") or (Tm_option == "Manual input")
            results = process_file(df, time_col, Power_col, Compound_Temp_col, Machine_Temp_col, active_Temp_col, tolerance, cooling_s, manual_Tc, manual_Tm, use_manual)

            if results:
                # Display the results
                st.write("Mean Value Calculation:")

                for result in results:
                    st.write(f"**Active Temp value:** {result['Active Temp']}")
                    st.write(f"**Interval start:** {result['interval_start']}")
                    st.write(f"**Interval end:** {result['interval_end']}")
                    #st.write(f"**Power values:** {result['Power values']}")
                    st.write(f"**Mean Power value:** {result['mean of Power']}")
                    st.write(f"**Mean Compound Temp:** {result['mean of Tc']}")
                    st.write(f"**Mean Machine Temp:** {result['mean of Tm']}")
                    st.write(f"**Alpha:** {result['alpha']}")
                    st.write(f"**Cooling surface:** {cooling_s}")
                    st.write("---")

                # Convert results to DataFrame
                results_df = pd.DataFrame(results)

                # Display the results DataFrame for reference
                st.write("Summary of Intervals:")
                st.dataframe(results_df[['Active Temp', 'interval_start', 'interval_end', 'mean of Power', 'mean of Tc', 'mean of Tm', 'alpha']])

                # Plot Active Temp over time and highlight constant intervals
                plt.figure(figsize=(12, 8))
                plt.plot(df[time_col], df[active_Temp_col], label='Active Temp', color='blue')
                for result in results:
                    plt.axvspan(result['interval_start'], result['interval_end'], color='red', alpha=0.3)
                plt.xlabel('Time')
                plt.ylabel('Active Temp')
                plt.title('Active Temp over Time with Constant Intervals Highlighted')
                plt.legend()
                st.pyplot(plt)

            else:
                st.write("No intervals found where Active Temp is constant for at least 10 seconds within the given tolerance.")
elif authentication_status == False:
    st.error("Username/password is incorrect")
elif authentication_status == None:
    st.warning("Please enter your username and password")
