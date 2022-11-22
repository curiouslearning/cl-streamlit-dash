import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
import altair as alt
from datetime import date
from datetime import timedelta


origin_date = date(2022, 6, 22)  # the first day that data is correct
origin_date = date(2022, 5, 14)  # the first day that data is correct
today = date.today()


# DATA FUNCTIONS -----------------------------------------------------------

@st.cache
def load_assessment_completed_data(lang, ass_type, since, until):
    """Load completed statements for the Curious Learing LRS."""
    # geting values out of secrets.toml file
    CL_BASE_URL = st.secrets.db_credentials.cl_lrs_base_url
    activity_param = f"activity=https://data.curiouslearning.org/xAPI/activities/assessment/{lang}/{ass_type}"
    VERB_PARAM = "verb=http://adlnet.gov/expapi/verbs/completed"
    lrs_URL = f"{CL_BASE_URL}?{activity_param}&{VERB_PARAM}&since={since}&until={until + timedelta(days=1)}"
    df = pd.DataFrame()

    # st.write(lrs_URL)

    while lrs_URL:
        response = requests.get(lrs_URL)
        jsonResponse = json.loads(response.text)
        df_statements = pd.json_normalize(jsonResponse['statements'])
        df = pd.concat([df, df_statements]).reset_index(drop=True)
        lrs_URL = jsonResponse['more']

    if len(df.index) > 0:
        # Keep only columns wanted
        df = df[['timestamp', 'actor.name', 'actor.account.name',
                 'result.score.raw', 'result.duration', 'verb.display.en-US',
                 'actor.account.homePage', 'result.score.max']]
        # remove Text from duration fomated as PTxx.xxS to just xx.xx
        df['result.duration'].replace(to_replace="PT([0-9\.]+).*",
                                      value=r"\1", regex=True, inplace=True)
        # remove duplicates -- for some reason double reporting can happen
        # TODO

        # rename the columns
        df.rename(columns={
            'actor.name': "webSessionId",
            'actor.account.name': "clUserId",
            'result.score.raw': "scoreRaw",
            'result.duration': "duration",
            'verb.display.en-US': "type",
            'actor.account.homePage': "userSource",
            'result.score.max': "scoreRawMax"},
            inplace=True, errors="ignore")

        # convert timestamp to datetime type
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    return df


@st.cache
def convert_df(df):
    """Convert a dataframe to CSV."""
    return df.to_csv().encode('utf-8')


st.title('Assessment Scores')  # -----------------------------------------
st.write('Some completion event (scores) seem to be dublicated. Still need to clear those out.')

# sidebar --------------------------------------------------------------------
date_range_selection = st.sidebar.date_input(
    "Date Range",
    [today - timedelta(days=30), today],
    min_value=origin_date,
    max_value=today)
language_selection = st.sidebar.selectbox(
    'Language',
    ('ukranian', 'english', 'zulu', 'hausa', 'hausaNN', 'bangla', 'french'))

assessment_selection = st.sidebar.selectbox(
    'Assessment',
    ('letter-sound', 'pseudoword'))

# assessment data ------------------------------------------------------------


# Load data
data = load_assessment_completed_data(language_selection,
                                      assessment_selection,
                                      date_range_selection[0],
                                      date_range_selection[1])

if len(data.index) > 0:
    # create count by days
    df = pd.Series.to_frame(data.groupby([data['timestamp'].dt.date]).size())
    df.rename(columns={0: assessment_selection}, inplace=True)

    # display totals a and last day change
    st.metric(label=assessment_selection,
              value=df[assessment_selection].sum(),
              delta=int(df.loc[df.index[-1], assessment_selection]))
    if st.checkbox('Show Timeline'):
        st.bar_chart(df)

    # usersByDay = df[df['event_name'] == 'first_open'].groupby(
    # ['event_date'])['event_date'].count().reset_index(name='count')
    #
    # usersByDayFig = px.line(usersByDay, x='event_date', y='count', labels={
    #                      "event_date": "Date (Day)",
    #                      "count": "New Users"},
    #                      title = "New User Count by Day")
    # st.plotly_chart(usersByDayFig)

    # # look at a count by user to find how many have complete multiply assmessments
    # df_assbyuser_count = data.groupby(["clUserId"])[
    #     "clUserId"].count().reset_index(name="count")
    # st.write(df_assbyuser_count)
    #
    # test_data = data.groupby(["clUserId"])["timestamp"].agg(['min', 'max', 'count']).reset_index()
    # # test_data['timespan'] = date(test_data['max']) - date(test_data['min'])
    # st.write(test_data)

    if st.checkbox('Show Histogram'):
        st.subheader('Histogram of scores')
        max_score = int(data['scoreRawMax'][0])
        num_bins = int(max_score / 20)

        h_data = pd.DataFrame()
        h_data['bins'] = list(range(0, max_score+1, 20))
        h_data['counts'] = np.histogram(data['scoreRaw'],
                                        bins=num_bins+1,
                                        range=(0, max_score))[0]

        hist_chart = alt.Chart(h_data).mark_bar().encode(
            x='bins',
            y='counts',
            # tooltips=['counts', 'bins']
        ).interactive()

        st.altair_chart(hist_chart)

    if st.checkbox('Show raw data'):
        st.subheader(assessment_selection)
        st.write(data)

    csv = convert_df(data)
    csv_filename = f"{language_selection}-{assessment_selection}-{date_range_selection[0]}-{date_range_selection[1]}.csv"

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=csv_filename,
        mime='text/csv',
    )
else:
    st.text("NO DATA for this date range")

st.text(f"Assessment scores not valid before 14 May 2022.")
st.text("Assessment Data before 22 June 2022 could have users with 'anonymous' as id")
