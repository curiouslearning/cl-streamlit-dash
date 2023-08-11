import streamlit as st
import pandas as pd
import json
import requests
import datetime
from datetime import date
from datetime import timedelta


# the first day that data is correct
# origin_date = date(2022, 6, 22)
origin_date = date(2022, 5, 14)  # the first day that data is correct
today = date.today()
tomorrow = today + datetime.timedelta(days=1)

CL_BASE_URL = st.secrets.db_credentials.cl_lrs_base_url

# DATA FUNCTIONS -----------------------------------------------------------


@st.cache_data
def load_actor_set(lang, ass_type, since, until):
    """Load completed statements for the Curious Learing LRS."""
    activity_param = f"activity=https://data.curiouslearning.org/xAPI/activities/assessment/{lang}/{ass_type}"
    VERB_PARAM = "verb=http://adlnet.gov/expapi/verbs/initialized"
    lrs_URL = f"{CL_BASE_URL}?{activity_param}&{VERB_PARAM}&since={since}&until={until}"

    # st.write(lrs_URL)
    actor_set = set()

    # st.write(lrs_URL)

    while lrs_URL:
        response = requests.get(lrs_URL)
        jsonResponse = json.loads(response.text)
        for s in jsonResponse['statements']:
            actor_set.add(json.dumps(s['actor']))
            # st.write(s)
        lrs_URL = jsonResponse['more']

    return actor_set


def data_clean_up(df):
    """Clean the data up."""
    if df.shape[0] > 0:
        # extract the options and place them in thier own column
        for i, r in df.iterrows():
            if r['verb.display.en-US'] == 'answered':
                for opt in r['object.definition.choices']:
                    df.at[i, opt['id']] = opt['description']['en-US']

# df[df.columns[df.columns.isin(['alcohol','hue','NON-EXISTANT COLUMN'])]]
        # Keep only columns wanted
        df = df[df.columns[df.columns.isin(['timestamp', 'verb.display.en-US', 'actor.name',
                                            'actor.account.name', 'actor.account.homePage',
                                            'object.definition.description.en-US',
                                            'result.response', 'result.duration',
                                            'result.score.raw', 'result.score.max',
                                            'object.location.lat', 'object.location.lng',
                                            'object.location.city', 'object.location.region',
                                            'object.location.country', 'option-0', 'option-1',
                                            'object.id', 'option-2', 'option-3'])]]

        df.rename(columns={"object.location.lat": "lat",
                           "object.location.lng": "lon",
                           'verb.display.en-US': "type",
                           'actor.name': "webSessionId",
                           'actor.account.name': "clUserId",
                           'actor.account.homePage': "userSource",
                           'object.definition.description.en-US': "question",
                           'result.response': "answer",
                           'result.duration': "responseTime",
                           'result.score.raw': "scoreRaw",
                           'result.score.max': "scoreRawMax",
                           'object.location.city': "city",
                           'object.location.region': "region",
                           'object.location.country': "country",
                           'object.id': "itemURL"},
                  inplace=True, errors="ignore")

        df['lat'] = pd.to_numeric(df['lat'])
        df['lon'] = pd.to_numeric(df['lon'])

        df.reset_index(drop=True)

    return df


@st.cache_data
def load_assessment_data(lang, ass_type, since, until):
    """Load all data for actors that have completed the assessment."""
    df = pd.DataFrame()

    actor_set = load_actor_set(lang, ass_type, since, until)
    base_objid = f"https://data.curiouslearning.org/xAPI/activities/assessment/{lang}/{ass_type}"

    if len(actor_set) > 0:
        for act in actor_set:
            actor_param = f"agent={act}"
            actor_url = f"{CL_BASE_URL}?{actor_param}&since={since}&until={until}"
            # st.write(actor_url)
            actor_response = requests.get(actor_url)
            actor_jsonResponse = json.loads(actor_response.text)
            df_actor_statements = pd.json_normalize(actor_jsonResponse['statements'])
            # keep only those statements for this assessment
            df_actor_statements = df_actor_statements[df_actor_statements['object.id'].str.startswith(
                base_objid)].reset_index(drop=True)
            df = pd.concat([df, df_actor_statements]).reset_index(drop=True)

    return data_clean_up(df)


@st.cache_data
def load_assessment_data_alt(lang, ass_type, since, until):
    """Load all statment over time periods and filter out what you need."""
    df = pd.DataFrame()

    lrs_URL = f"{CL_BASE_URL}?since={since}&until={until}"
    base_objid = f"https://data.curiouslearning.org/xAPI/activities/assessment/{lang}/{ass_type}"

    # st.write(lrs_URL)

    while lrs_URL:
        statement_response = requests.get(lrs_URL)
        statment_jsonResponse = json.loads(statement_response.text)
        df_statements = pd.json_normalize(statment_jsonResponse['statements'])

        # keep only those statement for this assessment
        df_statements = df_statements[df_statements['object.id'].str.startswith(
            base_objid)]

        df = pd.concat([df, df_statements]).reset_index(drop=True)
        lrs_URL = statment_jsonResponse['more']

    return data_clean_up(df)


@st.cache_data
def convert_df(df):
    """Convert a dataframe to CSV."""
    return df.to_csv().encode('utf-8')


st.title('assessment Data')  # -----------------------------------------

# sidebar --------------------------------------------------------------------
if origin_date > (today - timedelta(days=30)):
    start_date_init = origin_date
else:
    start_date_init = today - timedelta(days=30)


date_range_selection = st.sidebar.date_input(
    "Date Range",
    [start_date_init, tomorrow],
    min_value=origin_date,
    max_value=tomorrow)

language_selection = st.sidebar.selectbox(
    'Language',
    ('ukranian', 'english', 'zulu', 'hausa', 'hausaNN', 'bangla', 'french'))

assessment_selection = st.sidebar.selectbox(
    'Assessment',
    ('letter-sound', 'pseudo-word'))

# assessment data ------------------------------------------------------------

# Load data
start_date = date_range_selection[0]
end_date = date_range_selection[1]

# start_date = datetime.datetime(2022, 9, 16, 16, 48)
# end_date = datetime.datetime(2022, 9, 17, 0, 0)

data = load_assessment_data_alt(language_selection,
                                assessment_selection,
                                start_date,
                                end_date)

if len(data.index) > 0:

    st.header(assessment_selection)
    # display totals
    df_value_counts = data['type'].value_counts(sort=True)
    st.write(df_value_counts)

    # map the locations
    filter_data = data.dropna(subset=['lat', 'lon'], how='any')
    st.write(f"Number of location : {filter_data.shape[0]}")
    st.map(filter_data)

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
st.text("Assessment Data before 22 June 2022 could have users with 'anonymous' as name")
