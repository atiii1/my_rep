import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import re
import bcrypt
import streamlit_authenticator as stauth

# Load the image
logo = Image.open("hf_logo.png")

# Display the image at the top of the app
st.image(logo, width=200)  # Adjust the width as needed

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
    authenticator.logout("Logout", "sidebar")
    st.sidebar.title(f"Welcome {name}")
    st.title("Data Processing App")

    st.markdown("### 🔧 Settings")

    # Function to read and process Excel data
    @st.cache_data
    def read_excel_data(uploaded_file):
        sheets_dict = pd.read_excel(uploaded_file, sheet_name=None)
        combined_df = pd.DataFrame()
        for sheet_name, df in sheets_dict.items():
            df['Sheet'] = sheet_name
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        return sheets_dict, combined_df

    # Function to sanitize sheet names
    def sanitize_sheet_name(sheet_name):
        sanitized_name = re.sub(r'[\\/*?:\[\]]', '', sheet_name)
        return sanitized_name[:31]  # Truncate to 31 characters

    # Upload the Excel file
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

    if uploaded_file:
        sheets_dict, combined_df = read_excel_data(uploaded_file)
        columns = combined_df.columns.tolist()

        # Create selectboxes for column and cycle time
        selected_column = st.selectbox("Choose a column to plot", columns)
        cycle_time_column = st.selectbox("Choose the cycle time column", columns)

        # Button to show data as a table
        if st.button('Show Data'):
            selected_data = pd.DataFrame()

            for sheet_name, df in sheets_dict.items():
                if selected_column in df.columns:
                    sanitized_sheet_name = sanitize_sheet_name(sheet_name)
                    selected_data[sanitized_sheet_name] = df[selected_column]

            # Calculate mean and ±1 standard deviation grouped by cycle time
            cleaned_df = combined_df[[selected_column, cycle_time_column]].dropna()
            grouped = cleaned_df.groupby(cycle_time_column)
            mean_values = grouped.mean().reset_index()
            std_values = grouped.std().reset_index()

            selected_data['Mean'] = mean_values[selected_column]
            selected_data['+1 Std Dev'] = mean_values[selected_column] + std_values[selected_column]
            selected_data['-1 Std Dev'] = mean_values[selected_column] - std_values[selected_column]

            # Store the selected data in session state
            st.session_state.selected_data = selected_data

        # Button to show the graph
        if st.button('Show Graph'):
            cleaned_df = combined_df[[selected_column, cycle_time_column]].dropna()

            # Group by cycle time and calculate statistics
            grouped = cleaned_df.groupby(cycle_time_column)
            mean_values = grouped.mean().reset_index()
            median_values = grouped.median().reset_index()
            std_values = grouped.std().reset_index()

            # Create a Plotly figure
            fig = go.Figure()

            # Add data trace for each sheet
            for sheet_name, df in sheets_dict.items():
                fig.add_trace(go.Scatter(x=df[cycle_time_column], y=df[selected_column], mode='lines', line=dict(color='blue'), showlegend=False))

            # Add mean, median, and std deviation lines
            fig.add_trace(go.Scatter(x=mean_values[cycle_time_column], y=mean_values[selected_column], mode='lines', name='Overall mean', line=dict(color='red', dash='dash')))
            fig.add_trace(go.Scatter(x=median_values[cycle_time_column], y=median_values[selected_column], mode='lines', name='Overall median', line=dict(color='green', dash='dot')))
            fig.add_trace(go.Scatter(x=std_values[cycle_time_column], y=mean_values[selected_column] + std_values[selected_column], mode='lines', name='Overall +1 std dev', line=dict(color='orange', dash='dashdot')))
            fig.add_trace(go.Scatter(x=std_values[cycle_time_column], y=mean_values[selected_column] - std_values[selected_column], mode='lines', name='Overall -1 std dev', line=dict(color='orange', dash='dashdot')))

            # Update plot layout
            fig.update_layout(
                title=f'<b>Line Chart of {selected_column}</b> across all sheets',
                xaxis_title=cycle_time_column,
                yaxis_title=selected_column,
                title_font=dict(size=18, color='navy'),
                autosize=True,
                width=900,
                height=700,
                font=dict(size=16)
            )
            # Store the plot in session state
            st.session_state.plot = fig

        # Mean Graphs Setting section
        st.markdown("### Mean Graphs Setting")
        
        # User input for the number of fields
        num_fields = st.slider("How many fields do you want to analyze?", min_value=1, max_value=7, value=1)

        selected_columns = []
        for i in range(num_fields):
            selected_columns.append(st.selectbox(f"Choose Parameter {i+1}", columns, key=f"col_{i}"))

        # Button to show the graph for selected variables
        if st.button('Show Graph for Selected Variables'):
            if len(selected_columns) != len(set(selected_columns)):
                st.error("Please select unique parameters for all fields.")
            else:
                # Ensure all columns have the same length by dropping rows with NaNs
                combined_selection = [cycle_time_column] + selected_columns
                cleaned_df = combined_df[combined_selection].dropna(subset=combined_selection)

                # Convert necessary columns to numeric
                for col in combined_selection:
                    if isinstance(cleaned_df[col], pd.Series):
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

                # Drop rows with NaNs again to ensure alignment
                cleaned_df = cleaned_df.dropna(subset=combined_selection)

                # Check the data types of the selected columns
                #st.write("Data types of selected columns:")
               # st.write(cleaned_df.dtypes)

                # Group by cycle time and calculate mean values
                grouped = cleaned_df.groupby(cycle_time_column).mean().reset_index()

                # Ensure the DataFrame is correctly structured
                #st.write("Grouped DataFrame:")
                #st.write(grouped.head())

                # Determine the range for each selected column
                column_ranges = {column: (grouped[column].max() - grouped[column].min()) for column in selected_columns}

                # Debugging: Display column ranges
                #st.write("Column ranges:")
                #st.write(column_ranges)

                # Sort columns by range in descending order
                sorted_columns = sorted(column_ranges, key=column_ranges.get, reverse=True)

                # Debugging: Display sorted columns
                #st.write("Sorted columns:")
                #st.write(sorted_columns)

                # Create a Plotly figure for selected variables
                fig_selected = go.Figure()

                # Add traces for each selected column, dynamically setting the axis based on the range
                for i, column in enumerate(sorted_columns):
                    axis = 'y1' if i == 0 else 'y2'
                    fig_selected.add_trace(go.Scatter(
                        x=grouped[cycle_time_column],
                        y=grouped[column],
                        mode='lines',
                        name=f'Mean {column}',
                        yaxis=axis
                    ))


                # Update layout for multiple y-axes
                fig_selected.update_layout(
                    title=f'<b>Mean Values of Selected Parameters across all sheets</b>',
                    xaxis_title=cycle_time_column,
                    yaxis=dict(
                        title=sorted_columns[0],
                        titlefont=dict(color="blue"),
                        tickfont=dict(color="blue"),
                        side='left'
                    ),
                    yaxis2=dict(
                        title=sorted_columns[1] if len(sorted_columns) > 1 else "",
                        titlefont=dict(color="red"),
                        tickfont=dict(color="red"),
                        overlaying='y',
                        side='right'
                    ),
                    legend=dict(
                        x=1.05,
                        y=1,
                        traceorder="normal",
                        font=dict(size=12),
                    ),
                    title_font=dict(size=18, color='navy'),
                    autosize=True,
                    width=900,
                    height=700,
                    font=dict(size=16)
                )

                # Store the plot in session state
                st.session_state.plot_selected = fig_selected

        # Display the "Analytics Section" heading consistently below the buttons
        st.markdown("## 📈 Analytics Section")
        st.markdown("----")  # Adds a horizontal line for visual separation

        # Display the text and DataFrame as a table if available
        if 'selected_data' in st.session_state and not st.session_state.selected_data.empty:
            st.markdown(f'<h3 style="color: navy; font-size: 18px;"><b>Table of Data: {selected_column}</b></h3>', unsafe_allow_html=True)
            st.dataframe(st.session_state.selected_data)

        # Display the graph if available
        if 'plot' in st.session_state:
            st.plotly_chart(st.session_state.plot, use_container_width=True)

        # Display the graph for selected variables if available
        if 'plot_selected' in st.session_state:
            st.plotly_chart(st.session_state.plot_selected, use_container_width=True)



    # Add CSS styling for the "Show" button
    st.markdown(
    """
    <style>
    /* Change button size */
    .stButton>button {
        padding: 10px 20px;
        font-size: 16px;
        border-radius: 10px;
        background-color: #1E90FF;
        color: white;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4169E1;
    }
    </style>
    """, unsafe_allow_html=True
    )

elif authentication_status == False:
    st.error("Username/password is incorrect")

elif authentication_status == None:
    st.warning("Please enter your username and password")
