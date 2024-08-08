import streamlit as st
import pandas as pd
import os
from PIL import Image

# Load the image
logo = Image.open("hf_logo.png")

# Display the image at the top of the app
st.image(logo, width=200)  # Adjust the width as needed

def read_rpt_file(file):
    """
    Function to read a .rpt file and convert it to a DataFrame.
    Assumes the .rpt file uses ';' as the delimiter.
    """
    # Read the .rpt file
    lines = file.readlines()
    # Decode and strip each line, then split by ';'
    lines = [line.decode('utf-8').strip() for line in lines]
    
    # Save the first row
    first_row = lines[0]
    
    # Skip the first row and use the second row as header
    header = lines[1].split(';')
    
    # Make header unique
    def make_unique(header):
        counts = {}
        new_header = []
        for name in header:
            if name in counts:
                counts[name] += 1
                new_name = f"{name}_{counts[name]}"
            else:
                counts[name] = 0
                new_name = name
            new_header.append(new_name)
        return new_header
    
    header = make_unique(header)
    
    # Initialize an empty list to store the data rows
    data = []
    
    # Loop through the remaining lines starting from the third line
    for line in lines[2:]:
        row = line.split(';')
        # Ensure the row has the same number of columns as the header
        if len(row) == len(header):
            data.append(row)
        else:
            # Handle rows with inconsistent number of columns
            # Here, we'll skip such rows, but you can handle them differently if needed
            pass
    
    # Create a DataFrame
    df = pd.DataFrame(data, columns=header)
    
    # Convert numeric columns to appropriate data types
    df = df.apply(pd.to_numeric, errors='ignore')
    
    return df, first_row

def save_as_excel(dataframes, first_rows, filename):
    """
    Function to save multiple DataFrames as separate sheets in an Excel file.
    """
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        for i, (df, first_row) in enumerate(zip(dataframes, first_rows)):
            sheet_name = f'Sheet{i+1}'
            # Write the DataFrame to the Excel sheet starting from the second row
            df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)
            # Access the worksheet object
            worksheet = writer.sheets[sheet_name]
            # Write the first row to the first row of the sheet
            worksheet.write(0, 0, first_row)

# Streamlit app
st.title("RPT to Excel Converter")

# File uploader
uploaded_files = st.file_uploader("Upload .rpt files", type="rpt", accept_multiple_files=True)

if uploaded_files:
    dataframes = []
    first_rows = []
    for uploaded_file in uploaded_files:
        # Read the .rpt file
        df, first_row = read_rpt_file(uploaded_file)
        dataframes.append(df)
        first_rows.append(first_row)
    
    # Display the DataFrames
    for i, df in enumerate(dataframes):
        st.write(f"DataFrame from {uploaded_files[i].name}")
        st.dataframe(df)
    
    # Input for the Excel file name
    excel_filename = st.text_input("Enter the Excel file name", "output.xlsx")
    
    # Button to save as Excel and provide download link
    if st.button("Save and Download Excel"):
        save_as_excel(dataframes, first_rows, excel_filename)
        st.success(f"File saved as {excel_filename}")
        
        # Provide download link
        with open(excel_filename, "rb") as file:
            btn = st.download_button(
                label="Download Excel file",
                data=file,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
