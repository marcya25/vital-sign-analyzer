import streamlit as st
import pandas as pd
import sqlite3
import os
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- Setup ----------------

st.set_page_config(page_title="Clinical Decision Support System", layout="wide")

if not os.path.exists("Patient_Reports"):
    os.makedirs("Patient_Reports")

advice_file = "hospital_vital_decision_tables.csv"
advice_df = pd.read_csv(advice_file)

conn = sqlite3.connect("patients.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS patients
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT,
             age INTEGER,
             gender TEXT,
             date TEXT,
             weight REAL,
             height REAL,
             BMI REAL,
             SpO2 REAL,
             pulse REAL,
             temp REAL,
             systolic REAL,
             diastolic REAL)''')

conn.commit()

# ---------------- Advice Function ----------------

def get_advice(vital,value):

    df = advice_df[advice_df["Vital"] == vital]

    for _,row in df.iterrows():
        if row["Min Value"] <= value <= row["Max Value"]:
            return row["Notes"]

    return "No advice available."


# ---------------- Title ----------------

st.title("Clinical Decision Support System")

# ---------------- Tabs ----------------

tab1, tab2, tab3 = st.tabs(["Take Vitals", "Generate PDF", "Patient Database"])


# ====================================================
# TAB 1 — TAKE VITALS
# ====================================================

with tab1:

    st.subheader("Patient Information")

    col1,col2 = st.columns(2)

    with col1:
        name = st.text_input("Name")
        age = st.number_input("Age",0,120)
        gender = st.selectbox("Gender",["Male","Female"])

    with col2:
        date = st.date_input("Date",datetime.today())
        weight = st.number_input("Weight (kg)")
        height = st.number_input("Height (m)")

    st.subheader("Vital Signs")

    col3,col4 = st.columns(2)

    with col3:
        spo2 = st.number_input("SpO2 (%)")
        pulse = st.number_input("Pulse")

    with col4:
        temp = st.number_input("Temperature (°C)")
        sys = st.number_input("Systolic BP")
        dia = st.number_input("Diastolic BP")

    if st.button("Analyze Patient"):

        bmi = round(weight/(height**2),1)

        c.execute('''INSERT INTO patients
        (name,age,gender,date,weight,height,BMI,SpO2,pulse,temp,systolic,diastolic)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (name,age,gender,str(date),weight,height,bmi,spo2,pulse,temp,sys,dia))

        conn.commit()

        st.success("Patient Stored in Database")

        report=f"""
PATIENT CLINICAL REPORT

Name: {name}
Age: {age}
Gender: {gender}
Date: {date}

BMI: {bmi}
Blood Pressure: {sys}/{dia}
SpO2: {spo2}
Pulse: {pulse}
Temperature: {temp}
"""

        categories=[("BMI",bmi),("SpO2",spo2),("Pulse",pulse),("Blood Pressure",sys),("Temperature",temp)]

        for cat,val in categories:
            report+=f"\n{cat} Advice:\n{get_advice(cat,val)}\n"

        st.text_area("Clinical Report",report,height=300)

        vitals=["BMI","SpO2","Pulse","Temp","SysBP"]
        values=[bmi,spo2,pulse,temp,sys]

        fig,ax=plt.subplots()
        ax.bar(vitals,values)
        ax.set_title(f"{name} Vital Signs")

        st.pyplot(fig)


# ====================================================
# TAB 2 — PDF GENERATION
# ====================================================

with tab2:

    st.subheader("Generate Patient Report PDF")

    patient_name = st.text_input("Enter Patient Name for PDF")

    if st.button("Generate PDF"):

        query=f"SELECT * FROM patients WHERE name='{patient_name}' ORDER BY id DESC LIMIT 1"
        data=pd.read_sql(query,conn)

        if data.empty:
            st.error("Patient not found")
        else:

            row=data.iloc[0]

            report=f"""
PATIENT CLINICAL REPORT

Name: {row['name']}
Age: {row['age']}
Gender: {row['gender']}
Date: {row['date']}

BMI: {row['BMI']}
Blood Pressure: {row['systolic']}/{row['diastolic']}
SpO2: {row['SpO2']}
Pulse: {row['pulse']}
Temperature: {row['temp']}
"""

            filename=f"Patient_Reports/{row['name']}_{row['date']}.pdf"

            styles=getSampleStyleSheet()
            elements=[]

            elements.append(Paragraph("PATIENT CLINICAL REPORT",styles["Title"]))
            elements.append(Spacer(1,20))

            for line in report.split("\n"):
                elements.append(Paragraph(line,styles["Normal"]))

            doc=SimpleDocTemplate(filename,pagesize=letter)
            doc.build(elements)

            st.success("PDF Generated")

            st.download_button(
                "Download PDF",
                open(filename,"rb"),
                file_name=os.path.basename(filename)
            )


# ====================================================
# TAB 3 — DATABASE
# ====================================================

with tab3:

    st.subheader("Patient Database")

    df=pd.read_sql("SELECT * FROM patients",conn)

    search=st.text_input("Search patient")

    if search:
        df=df[df["name"].str.contains(search,case=False)]

    st.dataframe(df,use_container_width=True)

    if st.button("Factory Reset Database"):

        c.execute("DELETE FROM patients")
        conn.commit()

        st.warning("Database Cleared")