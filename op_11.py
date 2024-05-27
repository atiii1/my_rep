import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import re

# Load the image
try:
    logo = Image.open("hf_logo.png")
    st.image(logo, width=200)  # Adjust the width as needed
except Exception as e:
    st.error(f"Error loading image: {e}")

# Add the title and rest of your app content
st.title("My Streamlit App")

st.markdown("### 🔧 Settings")

# Function to read and process Excel data
@st.experimental_memo
def read_excel_data(uploaded_file):
    try:
        sheets_dict = pd.read_excel(uploaded_file, sheet_name=None)
        combined_df = pd.DataFrame()
        for sheet_name, df in sheets_dict.items():
            df['Sheet'] = sheet_name
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        return sheets_dict, combined_df
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return None, None

# Upload the Excel file
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

if uploaded_file:
    sheets_dict, combined_df = read_excel_data(uploaded_file)
    if sheets_dict and combined_df:
        columns = combined_df.columns.tolist()

        # Create selectboxes for column and cycle time
        selected_column = st.selectbox("Choose a column to plot", columns)
        cycle_time_column = st.selectbox("Choose the cycle time column", columns)
        
        # Add CSS styling for the "Show" button
        st.markdown(
        """
        <style>
        .stButton>button {
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 10px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        </style>
        """, unsafe_allow_html=True
        )

        if st.button('Download Data'):
            cleaned_df = combined_df[[selected_column, cycle_time_column]].dropna()

            # Prepare data to be written to Excel
            data_dict = {}
            for sheet_name, df in sheets_dict.items():
                data_dict[sheet_name] = df[selected_column]

            # Clean the selected column name for a valid file and sheet name
            safe_selected_column = re.sub(r'[\\/*?:"<>|]', "", selected_column)[:31]

            # Save to Excel
            output_path = f"{safe_selected_column}.xlsx"
            try:
                with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                    result_df = pd.DataFrame(data_dict)
                    result_df.to_excel(writer, index=False, sheet_name=safe_selected_column)
                st.success(f"Data for {selected_column} saved to {output_path}")
            except Exception as e:
                st.error(f"Error saving Excel file: {e}")

        if st.button('Show'):
            try:
                cleaned_df = combined_df[[selected_column, cycle_time_column]].dropna()

                # Group by cycle time and calculate statistics
                grouped = cleaned_df.groupby(cycle_time_column)
                mean_values = grouped.mean().reset_index()
                median_values = grouped.median().reset_index()
                std_values = grouped.std().reset_index()

                # Create a Plotly figure with better aspect ratio
                fig = go.Figure()

                st.markdown("## 📈 Analytics Section")

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
                    autosize=True,
                    width=900,
                    height=600,
                    font=dict(size=14)
                )

                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating plot: {e}")
