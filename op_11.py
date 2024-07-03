import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import os
import re

# Load the image
logo = Image.open("hf_logo.png")

# Display the image at the top of the app
st.image(logo, width=200)  # Adjust the width as needed

# Add the title and rest of your app content
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
            title=f'Line chart of {selected_column} across all sheets',
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

    # Display the "Analytics Section" heading consistently below the buttons
    st.markdown("## 📈 Analytics Section")

    # Display the DataFrame as a table if available
    if 'selected_data' in st.session_state and not st.session_state.selected_data.empty:
        st.dataframe(st.session_state.selected_data)

    # Display the graph if available
    if 'plot' in st.session_state:
        st.plotly_chart(st.session_state.plot, use_container_width=True)

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
