import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
from datetime import date
from datetime import timedelta


origin_date = date(2022, 5, 14)  # the first day that data is correct
today = date.today()


# DATA FUNCTIONS -----------------------------------------------------------
@st.cache
def load_assessment_completed_data(lang, ass_type, since, until):
    """Load completed statement for the lrs."""
    # geting values out of secrets.toml file
    CL_BASE_URL = st.secrets.db_credentials.cl_lrs_base_url
    activity_param = f"activity=https://data.curiouslearning.org/xAPI/activities/assessment/{lang}/{ass_type}"
    VERB_PARAM = "verb=http://adlnet.gov/expapi/verbs/completed"
    lrs_URL = f"{CL_BASE_URL}?{activity_param}&{VERB_PARAM}&since={since}&until={until + timedelta(days=1)}"
    df = pd.DataFrame()

    while lrs_URL:
        response = requests.get(lrs_URL)
        jsonResponse = json.loads(response.text)
        df_statements = pd.json_normalize(jsonResponse['statements'])
        df = pd.concat([df, df_statements])
        lrs_URL = jsonResponse['more']

    if len(df.index) > 0:
        # convert timestamp to datetime type
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # convert to time series data
        # df = df.set_index(df['timestamp'], inplace=True)
        # Keep only columns wanted
        # df = df[['col1', 'col2']]
    return df


st.title('Curious Learning Data')  # -----------------------------------------

# sidebar --------------------------------------------------------------------
date_range_selection = st.sidebar.date_input(
    "Date Range",
    [origin_date, today],
    min_value=origin_date,
    max_value=today)
language_selection = st.sidebar.selectbox(
    'Language',
    ('ukranian', 'english', 'zulu'))
assessment_data_select = st.sidebar.checkbox('Assessment Data')

# assessment data ------------------------------------------------------------
if assessment_data_select:
    st.header('Assessments')

    # Load data
    # TODO add progress bar
    data = load_assessment_completed_data(language_selection,
                                          'letter-sound',
                                          date_range_selection[0],
                                          date_range_selection[1])

    if len(data.index) > 0:
        # create count by days
        df = pd.Series.to_frame(data.groupby([data['timestamp'].dt.date]).size())
        df.rename(columns={0: 'letter-sound'}, inplace=True)

        # display totals a and last day change
        st.metric(label="letter-sound",
                  value=df['letter-sound'].sum(),
                  delta=int(df.loc[df.index[-1], 'letter-sound']))

        st.line_chart(df)

        if st.checkbox('Show Histogram'):
            st.subheader('Histogram of scores')
            hist_values = np.histogram(
                data['result.score.raw'], bins=25, range=(0, 500))[0]
            st.bar_chart(hist_values)

        if st.checkbox('Show raw data'):
            st.subheader('letter-sound')
            st.write(data)
    else:
        st.text("NO DATA for this date range")

    st.text(f"Assessment Data not valid before {origin_date}.")


# TODO add CVS data downloads
# @st.cache
# def convert_df(df):
#     return df.to_csv().encode('utf-8')
#
# csv = convert_df(df)
#
# st.download_button(
#     "Press to Download",
#     csv,
#     "browser_visits.csv",
#     "text/csv",
#     key='browser-data'
# )
