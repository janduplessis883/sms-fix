import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import time

st.set_page_config(page_title="SMS-Fix for Accurx", layout="centered")

st.title("SMS-Fix for Accurx")
st.caption(
    """
    :material/sms: **SMS-Fix** will format your csv file for use with Accurx SMS. Uplodaded CSV files must contain the following columns: NHS Number, Preferred Telephone Number, Date of Birth, First Name, and Email Address.
    """
)

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is None:
    st.image("smsfix.png")
else:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        st.error("Could not read the CSV file. Please check the format.")
        st.stop()

    # Display the uploaded data
    st.subheader("Uploaded Data")
    st.dataframe(df, height=200)
    st.info(f"Uploaded DataFrame row count: **{df.shape[0]}**")

    # Check for required columns
    required_cols = [
        "NHS number",
        "Preferred telephone number",
        "Date of birth",
        "First name",
        "Email address"
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.toast(f"Missing columns: {', '.join(missing_cols)}", icon=":material/build_circle:")
        st.stop()

    # Validate and clean UK mobile numbers

    def clean_mobile(mobile):
        if pd.isna(mobile):
            return np.nan
        s = str(mobile).strip()
        # Correct O7/o7 to 07
        if s.startswith("O7") or s.startswith("o7"):
            s = "07" + s[2:]
        # If starts with 7 and is 10 digits, prepend 0
        if s.startswith("7") and len(s) == 10 and s.isdigit():
            s = "0" + s
        # Remove spaces, dashes, parentheses
        s = re.sub(r"[ \-\(\)]", "", s)
        # Accept 07XXXXXXXXX (11 digits) or +447XXXXXXXXX (13 chars)
        if re.match(r"^07\d{9}$", s):
            return s
        if re.match(r"^\+447\d{9}$", s):
            return s
        return np.nan
    original_mobiles = df["Preferred telephone number"].copy()
    df["Preferred telephone number"] = df["Preferred telephone number"].apply(clean_mobile)
    # Warn about corrections and blanked numbers
    corrected = (original_mobiles != df["Preferred telephone number"]) & (df["Preferred telephone number"] != "")
    blanked = (df["Preferred telephone number"] == "")
    if corrected.any():
        time.sleep(0.3)  # Small delay to ensure toast appears after processing
        st.toast(
            "The following row(s) had their mobile number corrected to a valid UK format: " +
            ", ".join(str(idx) for idx in df[corrected].index.tolist()), icon=":material/build_circle:"
        )
    if blanked.any():
        time.sleep(0.3)
        st.toast(
            "The following row(s) had invalid mobile numbers and have been blanked: " +
            ", ".join(str(idx) for idx in df[blanked].index.tolist()), icon=":material/build_circle:"
        )

    # Extract valid email from any cell with extra text (remove text after first space)
    def extract_email(cell):
        s = str(cell).strip()
        if " " in s:
            return s.split(" ")[0]
        return s
    df["Email address"] = df["Email address"].apply(extract_email)
    # Replace empty strings or 'nan' (string) with np.nan
    df["Email address"] = df["Email address"].replace(["", "nan", "NaN", "None"], np.nan)

    # After extraction, warn if any are still blank (could not extract)
    still_blank_mask = df["Email address"].isna()
    if still_blank_mask.any():
        blanked_emails = df.loc[still_blank_mask].index.tolist()
        time.sleep(0.3)
        st.toast(
            f"The following row(s) had no valid email address and have been left blank: {blanked_emails}", icon=":material/build_circle:"
        )

    # Check that NHS number is 10 digits long, drop rows that do not match
    nhs_valid = df["NHS number"].astype(str).str.match(r"^\d{10}$")
    dropped_count = (~nhs_valid).sum()
    if dropped_count > 0:
        time.sleep(0.3)
        st.toast(f"**{dropped_count}** row(s) dropped due to invalid NHS number (must be exactly 10 digits).", icon=":material/build_circle:")
    df = df[nhs_valid].reset_index(drop=True)

    # Drop rows where both mobile number and email are missing (treat NaN and empty as missing)
    mobile_missing = df["Preferred telephone number"].isna() | (df["Preferred telephone number"].astype(str).str.strip() == "")
    email_missing = df["Email address"].isna() | (df["Email address"].astype(str).str.strip() == "")
    both_missing = mobile_missing & email_missing
    both_missing_count = both_missing.sum()
    if both_missing_count > 0:
        time.sleep(0.3)
        st.toast(f"**{both_missing_count}** row(s) dropped because both mobile number and email address were missing.", icon=":material/build_circle:")
    df = df[~both_missing].reset_index(drop=True)

    # Keep only the required columns in the cleaned DataFrame
    output_cols = [
        "NHS number",
        "Preferred telephone number",
        "Date of birth",
        "First name",
        "Email address"
    ]
    cleaned_df = df[output_cols].copy()
    st.divider()
    time.sleep(0.3)
    st.toast("### Scroll down!!", icon=":material/south:")
    st.subheader(":material/household_supplies: Cleaned Data")
    st.dataframe(cleaned_df, height=200)
    st.info(f"Cleaned DataFrame row count: **{cleaned_df.shape[0]}**")

    st.subheader(":material/download: Download Cleaned CSV")

    # Text input for custom filename
    filename = st.text_input(
        "Enter a name for the downloaded CSV file (optional, without .csv extension):",
        value="acurex_sms_cleaned"
    )
    # Download button for cleaned CSV
    csv_buffer = io.StringIO()
    cleaned_df.to_csv(csv_buffer, index=False)
    download_name = filename.strip() + ".csv" if filename.strip() else "acurex_sms_cleaned.csv"
    st.download_button(
        label="Download Cleaned CSV",
        data=csv_buffer.getvalue(),
        file_name=download_name,
        mime="text/csv"
    )
