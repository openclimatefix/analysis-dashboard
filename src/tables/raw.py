import streamlit as st


def make_raw_table(df_mae, df_rmse):
    st.subheader("Raw Data")
    col1, col2 = st.columns([1, 1])
    col1.write(df_mae)
    col2.write(df_rmse)
