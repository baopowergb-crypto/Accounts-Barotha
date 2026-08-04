
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from pyngrok import ngrok
"/mount/src/accounts-barotha/Accounts app.py"
import threading
import time

# ============================================================
# GHAZI BAROTHA ACCOUNTS MANAGEMENT SYSTEM
# Streamlit + SQLite
# ============================================================

DATABASE = "ghazi_barotha_accounts.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    # Cash Book
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            account_code TEXT,
            description TEXT,
            cheque_no TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            remarks TEXT
        )
    """)

    # Cheque Register
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cheques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cheque_no TEXT,
            cheque_date TEXT,
            payee TEXT,
            bank TEXT,
            amount REAL,
            status TEXT,
            remarks TEXT
        )
    """)

    conn.commit()
    conn.close()


create_database()


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Ghazi Barotha Accounts",
    page_icon="🏦",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.main {
    background-color: #f4f6f8;
}

.header {
    background-color: #123b5d;
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
}

.header p {
    margin: 5px;
}

.card {
    background-color: white;
    padding: 20px;
    border-radius: 10px;
    border: 1px solid #ddd;
    text-align: center;
}

.amount {
    font-size: 25px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="header">

<h1>WAPDA - GHAZI BAROTHA</h1>

<p>Accounts Management System</p>

</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR MENU
# ============================================================

st.sidebar.title("📋 Main Menu")

page = st.sidebar.radio(
    "Select Module",
    [
        "🏠 Dashboard",
        "💰 Cash Book",
        "➕ Add Transaction",
        "🧾 Cheque Register",
        "➕ Add Cheque",
        "📊 Reports"
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("🏠 Accounts Dashboard")

    conn = get_connection()

    receipts = conn.execute("""
        SELECT COALESCE(SUM(credit),0)
        FROM transactions
    """).fetchone()[0]

    payments = conn.execute("""
        SELECT COALESCE(SUM(debit),0)
        FROM transactions
    """).fetchone()[0]

    transactions = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
    """).fetchone()[0]

    pending_cheques = conn.execute("""
        SELECT COUNT(*)
        FROM cheques
        WHERE status = 'Pending'
    """).fetchone()[0]

    cleared_cheques = conn.execute("""
        SELECT COUNT(*)
        FROM cheques
        WHERE status = 'Cleared'
    """).fetchone()[0]

    conn.close()

    balance = receipts - payments

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "💵 Total Receipts",
            f"Rs. {receipts:,.2f}"
        )

    with col2:
        st.metric(
            "💸 Total Payments",
            f"Rs. {payments:,.2f}"
        )

    with col3:
        st.metric(
            "💰 Cash Book Balance",
            f"Rs. {balance:,.2f}"
        )

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📒 Transactions",
            transactions
        )

    with col2:
        st.metric(
            "⏳ Pending Cheques",
            pending_cheques
        )

    with col3:
        st.metric(
            "✅ Cleared Cheques",
            cleared_cheques
        )

    st.divider()

    st.subheader("Recent Transactions")

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            date AS Date,
            type AS Type,
            account_code AS "Account Code",
            description AS Description,
            cheque_no AS "Cheque No.",
            debit AS Debit,
            credit AS Credit,
            remarks AS Remarks
        FROM transactions
        ORDER BY id DESC
        LIMIT 10
    """, conn)

    conn.close()

    if len(df) > 0:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transactions have been entered yet.")


# ============================================================
# ADD TRANSACTION
# ============================================================

elif page == "➕ Add Transaction":

    st.title("➕ Add Cash Book Transaction")

    with st.form("transaction_form"):

        col1, col2 = st.columns(2)

        with col1:

            transaction_date = st.date_input(
                "Date",
                value=date.today()
            )

            transaction_type = st.selectbox(
                "Transaction Type",
                [
                    "Receipt",
                    "Payment"
                ]
            )

            account_code = st.text_input(
                "Account Code",
                placeholder="e.g. 3101"
            )

            cheque_no = st.text_input(
                "Cheque No."
            )

        with col2:

            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=100.0,
                format="%.2f"
            )

            description = st.text_area(
                "Description"
            )

            remarks = st.text_area(
                "Remarks"
            )

        submitted = st.form_submit_button(
            "💾 Save Transaction",
            use_container_width=True
        )

    if submitted:

        if amount <= 0:
            st.error("Please enter an amount.")

        elif description.strip() == "":
            st.error("Please enter a description.")

        else:

            debit = amount if transaction_type == "Payment" else 0
            credit = amount if transaction_type == "Receipt" else 0

            conn = get_connection()

            conn.execute("""
                INSERT INTO transactions
                (
                    date,
                    type,
                    account_code,
                    description,
                    cheque_no,
                    debit,
                    credit,
                    remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(transaction_date),
                transaction_type,
                account_code,
                description,
                cheque_no,
                debit,
                credit,
                remarks
            ))

            conn.commit()
            conn.close()

            st.success(
                "✅ Transaction saved successfully."
            )


# ============================================================
# CASH BOOK
# ============================================================

elif page == "💰 Cash Book":

    st.title("💰 Cash Book")

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            id AS ID,
            date AS Date,
            type AS Type,
            account_code AS "Account Code",
            description AS Description,
            cheque_no AS "Cheque No.",
            debit AS Debit,
            credit AS Credit,
            remarks AS Remarks
        FROM transactions
        ORDER BY date, id
    """, conn)

    conn.close()

    if len(df) == 0:

        st.info(
            "No Cash Book transactions available."
        )

    else:

        # Running Balance
        df["Balance"] = (
            df["Credit"].fillna(0)
            -
            df["Debit"].fillna(0)
        ).cumsum()

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        total_debit = df["Debit"].sum()
        total_credit = df["Credit"].sum()
        closing_balance = total_credit - total_debit

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Total Debit",
                f"Rs. {total_debit:,.2f}"
            )

        with col2:
            st.metric(
                "Total Credit",
                f"Rs. {total_credit:,.2f}"
            )

        with col3:
            st.metric(
                "Closing Balance",
                f"Rs. {closing_balance:,.2f}"
            )

        # Excel download
        excel_data = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Cash Book",
            excel_data,
            "Ghazi_Barotha_Cash_Book.csv",
            "text/csv"
        )


# ============================================================
# ADD CHEQUE
# ============================================================

elif page == "➕ Add Cheque":

    st.title("➕ Add Cheque")

    with st.form("cheque_form"):

        col1, col2 = st.columns(2)

        with col1:

            cheque_no = st.text_input(
                "Cheque No."
            )

            cheque_date = st.date_input(
                "Cheque Date",
                value=date.today()
            )

            payee = st.text_input(
                "Payee"
            )

            bank = st.text_input(
                "Bank"
            )

        with col2:

            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=100.0,
                format="%.2f"
            )

            status = st.selectbox(
                "Status",
                [
                    "Pending",
                    "Cleared",
                    "Cancelled"
                ]
            )

            remarks = st.text_area(
                "Remarks"
            )

        submitted = st.form_submit_button(
            "💾 Save Cheque",
            use_container_width=True
        )

    if submitted:

        if cheque_no.strip() == "":
            st.error("Please enter cheque number.")

        elif amount <= 0:
            st.error("Please enter cheque amount.")

        else:

            conn = get_connection()

            conn.execute("""
                INSERT INTO cheques
                (
                    cheque_no,
                    cheque_date,
                    payee,
                    bank,
                    amount,
                    status,
                    remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cheque_no,
                str(cheque_date),
                payee,
                bank,
                amount,
                status,
                remarks
            ))

            conn.commit()
            conn.close()

            st.success(
                "✅ Cheque saved successfully."
            )


# ============================================================
# CHEQUE REGISTER
# ============================================================

elif page == "🧾 Cheque Register":

    st.title("🧾 Cheque Register")

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            id AS ID,
            cheque_no AS "Cheque No.",
            cheque_date AS "Cheque Date",
            payee AS Payee,
            bank AS Bank,
            amount AS Amount,
            status AS Status,
            remarks AS Remarks
        FROM cheques
        ORDER BY cheque_date DESC, id DESC
    """, conn)

    conn.close()

    if len(df) == 0:

        st.info(
            "No cheques have been entered."
        )

    else:

        # Search
        search = st.text_input(
            "🔎 Search Cheque No. / Payee"
        )

        if search:

            df = df[
                df["Cheque No."]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
                |
                df["Payee"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            [
                "All",
                "Pending",
                "Cleared",
                "Cancelled"
            ]
        )

        if status_filter != "All":

            df = df[
                df["Status"] == status_filter
            ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        if len(df) > 0:

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Number of Cheques",
                    len(df)
                )

            with col2:
                st.metric(
                    "Total Amount",
                    f"Rs. {df['Amount'].sum():,.2f}"
                )


# ============================================================
# REPORTS
# ============================================================

elif page == "📊 Reports":

    st.title("📊 Accounts Reports")

    report = st.selectbox(
        "Select Report",
        [
            "Daily Summary",
            "Account Code Summary",
            "Cheque Status Summary"
        ]
    )

    conn = get_connection()

    # --------------------------------------------------------
    # DAILY SUMMARY
    # --------------------------------------------------------

    if report == "Daily Summary":

        df = pd.read_sql_query("""
            SELECT
                date AS Date,
                SUM(debit) AS Debit,
                SUM(credit) AS Credit
            FROM transactions
            GROUP BY date
            ORDER BY date DESC
        """, conn)

        st.subheader("Daily Cash Book Summary")

        if len(df) > 0:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No data available.")

    # --------------------------------------------------------
    # ACCOUNT CODE SUMMARY
    # --------------------------------------------------------

    elif report == "Account Code Summary":

        df = pd.read_sql_query("""
            SELECT
                account_code AS "Account Code",
                SUM(debit) AS Debit,
                SUM(credit) AS Credit
            FROM transactions
            GROUP BY account_code
            ORDER BY account_code
        """, conn)

        st.subheader("Account Code Summary")

        if len(df) > 0:

            df["Balance"] = (
                df["Credit"] -
                df["Debit"]
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No data available.")

    # --------------------------------------------------------
    # CHEQUE STATUS
    # --------------------------------------------------------

    elif report == "Cheque Status Summary":

        df = pd.read_sql_query("""
            SELECT
                status AS Status,
                COUNT(*) AS "Number of Cheques",
                SUM(amount) AS "Total Amount"
            FROM cheques
            GROUP BY status
        """, conn)

        st.subheader("Cheque Status Summary")

        if len(df) > 0:

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No cheque data available.")

    conn.close()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "WAPDA - Ghazi Barotha Accounts Management System"
)
import subprocess
import time

process = subprocess.Popen(
    [
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8501",
        "--server.address",
        "0.0.0.0"
    ]
)

time.sleep(5)

print("Streamlit server started.")
from pyngrok import ngrok

public_url = ngrok.connect(8501)

print("======================================")
print("GHAZI BAROTHA ACCOUNTS SYSTEM")
print("======================================")
print("Open this link:")
print(public_url)
