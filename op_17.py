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

        # Create selectboxes for column, cycle time, and step number
        selected_column = st.selectbox("Choose a column to plot", columns)
        cycle_time_column = st.selectbox("Choose the cycle time column", columns)
        step_number_column = st.selectbox("Choose the step number column", columns)

        # Ensure filtering logic is only executed after step_value is set by the user
        if selected_column and cycle_time_column and step_number_column:
            step_value = st.number_input("Enter the step number value", min_value=0, value=1, step=1)

            # Convert the step number column to numeric if it's not already
            try:
                combined_df[step_number_column] = pd.to_numeric(combined_df[step_number_column], errors='coerce')
            except Exception as e:
                st.error(f"Error converting {step_number_column} to numeric: {e}")
                st.stop()

            # Filter the data based on the selected step number only after all inputs are set
            if step_value is not None:
                filtered_df = combined_df[combined_df[step_number_column] >= step_value + 1].dropna()

                # Create a new cycle time column starting from 0
                filtered_df['New Cycle Time'] = filtered_df.groupby('Sheet').cumcount()

                # Button to preview the filtered dataset
                if st.button('Preview Filtered Data'):
                    st.markdown("### Preview of Filtered Dataset with New Cycle Time Column")
                    st.dataframe(filtered_df)

                # Button to show data as a table
                if st.button('Show Data'):
                    selected_data = pd.DataFrame()

                    for sheet_name, df in sheets_dict.items():
                        if selected_column in df.columns:
                            sanitized_sheet_name = sanitize_sheet_name(sheet_name)
                            selected_data[sanitized_sheet_name] = df[df[step_number_column] >= step_value + 1][selected_column]

                    # Drop rows with None values in the selected column
                    selected_data = selected_data.dropna()

                    # Calculate mean and ±1 standard deviation grouped by new cycle time
                    cleaned_df = filtered_df[[selected_column, 'New Cycle Time']].dropna()
                    grouped = cleaned_df.groupby('New Cycle Time')
                    mean_values = grouped.mean().reset_index()
                    std_values = grouped.std().reset_index()

                    selected_data['Mean'] = mean_values[selected_column]
                    selected_data['+1 Std Dev'] = mean_values[selected_column] + std_values[selected_column]
                    selected_data['-1 Std Dev'] = mean_values[selected_column] - std_values[selected_column]

                    # Store the selected data in session state
                    st.session_state.selected_data = selected_data

                # Button to show the graph
                if st.button('Show Graph'):
                    cleaned_df = filtered_df[[selected_column, 'New Cycle Time']].dropna()

                    # Group by new cycle time and calculate statistics
                    grouped = cleaned_df.groupby('New Cycle Time')
                    mean_values = grouped.mean().reset_index()
                    median_values = grouped.median().reset_index()
                    std_values = grouped.std().reset_index()

                    # Create a Plotly figure
                    fig = go.Figure()

                    # Add data trace for each sheet
                    for sheet_name, df in sheets_dict.items():
                        filtered_sheet_df = df[df[step_number_column] >= step_value + 1].dropna(subset=[selected_column, cycle_time_column])
                        if not filtered_sheet_df.empty:
                            filtered_sheet_df['New Cycle Time'] = filtered_sheet_df.groupby('Sheet').cumcount()
                            fig.add_trace(go.Scatter(x=filtered_sheet_df['New Cycle Time'], y=filtered_sheet_df[selected_column], mode='lines', line=dict(color='blue'), showlegend=False))

                    # Add mean, median, and std deviation lines
                    fig.add_trace(go.Scatter(x=mean_values['New Cycle Time'], y=mean_values[selected_column], mode='lines', name='Overall mean', line=dict(color='red', dash='dash')))
                    fig.add_trace(go.Scatter(x=median_values['New Cycle Time'], y=median_values[selected_column], mode='lines', name='Overall median', line=dict(color='green', dash='dot')))
                    fig.add_trace(go.Scatter(x=std_values['New Cycle Time'], y=mean_values[selected_column] + std_values[selected_column], mode='lines', name='Overall +1 std dev', line=dict(color='orange', dash='dashdot')))
                    fig.add_trace(go.Scatter(x=std_values['New Cycle Time'], y=mean_values[selected_column] - std_values[selected_column], mode='lines', name='Overall -1 std dev', line=dict(color='orange', dash='dashdot')))

                    # Update plot layout
                    fig.update_layout(
                        title=f'<b>Line Chart of {selected_column}</b> across all sheets',
                        xaxis_title='New Cycle Time',
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
                        combined_selection = ['New Cycle Time'] + selected_columns
                        cleaned_df = filtered_df[combined_selection].dropna(subset=combined_selection)

                        # Convert necessary columns to numeric
                        for col in combined_selection:
                            if isinstance(cleaned_df[col], pd.Series):
                                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

                        # Drop rows with NaNs again to ensure alignment
                        cleaned_df = cleaned_df.dropna(subset=combined_selection)

                        # Group by new cycle time and calculate mean values
                        grouped = cleaned_df.groupby('New Cycle Time').mean().reset_index()

                        # Determine the range for each selected column
                        column_ranges = {column: (grouped[column].max() - grouped[column].min()) for column in selected_columns}

                        # Sort columns by range in descending order
                        sorted_columns = sorted(column_ranges, key=column_ranges.get, reverse=True)

                        # Create a Plotly figure for selected variables
                        fig_selected = go.Figure()

                        # Add traces for each selected column, dynamically setting the axis based on the range
                        for i, column in enumerate(sorted_columns):
                            axis = 'y1' if i == 0 else 'y2'
                            fig_selected.add_trace(go.Scatter(
                                x=grouped['New Cycle Time'],
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
