import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Acurex SMS Formatter", layout="centered")

st.title("Acurex SMS CSV Formatter")
st.write(
    """
    Upload a CSV file containing patient data (columns: Patient Name, NHS Number, Date of Birth, Telephone Number, First Name, Email Address).
    The app will format the data for Acurex SMS messaging.
    """
)

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        st.error("Could not read the CSV file. Please check the format.")
        st.stop()

    # Display the uploaded data
    st.subheader("Uploaded Data")
    st.dataframe(df)

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
        st.error(f"Missing columns: {', '.join(missing_cols)}")
        st.stop()

    # Validate and clean UK mobile numbers
    import re
    def clean_mobile(mobile):
        if pd.isna(mobile):
            return ""
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
        return ""
    original_mobiles = df["Preferred telephone number"].copy()
    df["Preferred telephone number"] = df["Preferred telephone number"].apply(clean_mobile)
    # Warn about corrections and blanked numbers
    corrected = (original_mobiles != df["Preferred telephone number"]) & (df["Preferred telephone number"] != "")
    blanked = (df["Preferred telephone number"] == "")
    if corrected.any():
        st.warning(
            "The following row(s) had their mobile number corrected to a valid UK format: " +
            ", ".join(str(idx) for idx in df[corrected].index.tolist())
        )
    if blanked.any():
        st.warning(
            "The following row(s) had invalid mobile numbers and have been blanked: " +
            ", ".join(str(idx) for idx in df[blanked].index.tolist())
        )

    # Extract valid email from any cell with extra text
    email_extract_pattern = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
    def extract_email(cell):
        match = email_extract_pattern.search(str(cell))
        return match.group(1) if match else ""
    df["Email address"] = df["Email address"].apply(extract_email)

    # After extraction, warn if any are still blank (could not extract)
    still_blank_mask = df["Email address"].astype(str).str.strip() == ""
    if still_blank_mask.any():
        blanked_emails = df.loc[still_blank_mask].index.tolist()
        st.warning(
            f"The following row(s) had no valid email address and have been left blank: {blanked_emails}"
        )

    # Check that NHS number is 10 digits long, drop rows that do not match
    nhs_valid = df["NHS number"].astype(str).str.match(r"^\d{10}$")
    dropped_count = (~nhs_valid).sum()
    if dropped_count > 0:
        st.warning(f"{dropped_count} row(s) dropped due to invalid NHS number (must be exactly 10 digits).")
    df = df[nhs_valid].reset_index(drop=True)

    # Drop rows where both mobile number and email are missing
    both_missing = (df["Preferred telephone number"].astype(str).str.strip() == "") & (df["Email address"].astype(str).str.strip() == "")
    both_missing_count = both_missing.sum()
    if both_missing_count > 0:
        st.warning(f"{both_missing_count} row(s) dropped because both mobile number and email address were missing.")
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

    st.subheader("Cleaned Data")
    st.dataframe(cleaned_df)

    # Download button for cleaned CSV
    csv_buffer = io.StringIO()
    cleaned_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download Cleaned CSV",
        data=csv_buffer.getvalue(),
        file_name="acurex_sms_cleaned.csv",
        mime="text/csv"
    )
