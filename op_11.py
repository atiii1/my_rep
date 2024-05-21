import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Function to read and process Excel data
@st.cache_data
def read_excel_data(uploaded_file):
    sheets_dict = pd.read_excel(uploaded_file, sheet_name=None)
    combined_df = pd.DataFrame()
    for sheet_name, df in sheets_dict.items():
        df['Sheet'] = sheet_name
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    return sheets_dict, combined_df

# Upload the Excel file
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

if uploaded_file:
    sheets_dict, combined_df = read_excel_data(uploaded_file)
    columns = combined_df.columns.tolist()

    # Create selectboxes for column and cycle time
    selected_column = st.selectbox("Choose a column to plot", columns)
    cycle_time_column = st.selectbox("Choose the cycle time column", columns)

    if st.button('Show'):
        cleaned_df = combined_df[[selected_column, cycle_time_column]].dropna()

        # Group by cycle time and calculate statistics
        grouped = cleaned_df.groupby(cycle_time_column)
        mean_values = grouped.mean().reset_index()
        median_values = grouped.median().reset_index()
        std_values = grouped.std().reset_index()

        # Create a Plotly figure with better aspect ratio
        fig = go.Figure()

        # Add data trace for each sheet in blue
        for sheet_name, df in sheets_dict.items():
            fig.add_trace(go.Scatter(x=df[cycle_time_column], y=df[selected_column], mode='lines', line=dict(color='blue'), showlegend=False))

        # Add mean line
        fig.add_trace(go.Scatter(x=mean_values[cycle_time_column], y=mean_values[selected_column], mode='lines', name='Overall mean', line=dict(color='red', dash='dash')))

        # Add median line
        fig.add_trace(go.Scatter(x=median_values[cycle_time_column], y=median_values[selected_column], mode='lines', name='Overall median', line=dict(color='green', dash='dot')))

        # Add standard deviation lines
        fig.add_trace(go.Scatter(x=std_values[cycle_time_column], y=mean_values[selected_column] + std_values[selected_column], mode='lines', name='Overall +1 std dev', line=dict(color='orange', dash='dashdot')))
        fig.add_trace(go.Scatter(x=std_values[cycle_time_column], y=mean_values[selected_column] - std_values[selected_column], mode='lines', name='Overall -1 std dev', line=dict(color='orange', dash='dashdot')))

        # Set the title and labels with dimensions for better aspect ratio
        fig.update_layout(
            title=f'Line chart of {selected_column} across all sheets',
            xaxis_title=cycle_time_column,
            yaxis_title=selected_column,
            autosize=True,  # Enable autosize for better aspect ratio
            width=900,  # Adjust width for balanced aspect ratio
            height=600,  # Adjust height for balanced aspect ratio
            font=dict(size=14)  # Increase font size for better readability
        )

        # Display the plot with improved aspect ratio
        st.plotly_chart(fig, use_container_width=True)
