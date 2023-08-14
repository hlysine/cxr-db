import random
import streamlit as st
import pandas as pd
import time
import os.path
import subprocess
from streamlit_javascript import st_javascript as st_js
import urllib.parse
import psutil

# Define constants
path = 'sample/'

# Configure libraries
st.set_page_config(
    page_title="CXR Database",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="collapsed"
)
pd.set_option('display.max_columns', None)

# Initialize session state
if "expander_state" not in st.session_state:
    st.session_state["expander_state"] = True
if "history" not in st.session_state:
    st.session_state["history"] = []
if "forceload" not in st.session_state:
    st.session_state["forceload"] = False

# Show title and site check
st.write("""
# CXR Database

Filter and view the chest X-ray and diagnosis data from the NIH Chest X-ray database.

**Points to note**

- The provided findings may not be 100% accurate and may not be the only findings in the image.
""")

site_link = 'https://lysine-cxr-db.hf.space/'
st_cloud = os.path.isdir('/home/appuser')
if st_cloud:
    st.warning(f"""
**cxr-db has a new home with increased stability. Please access cxr-db from the new link below:**

Link to the new site: [{site_link}]({site_link}?{urllib.parse.urlencode(st.experimental_get_query_params(), doseq=True)})
""", icon='✨')
    if not st.session_state["forceload"]:
        with st.expander("If the new site is not working for you"):
            if st.button("Load the app here"):
                st.session_state["forceload"] = True
                st.experimental_rerun()
        st.stop()

# Download data from kaggle
if not os.path.isfile(path + 'sample_labels.csv'):
    placeholder = st.empty()
    already_downloading = False
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if "kaggle" in proc.name().lower():
                already_downloading = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if not already_downloading:
        try:
            placeholder.info(
                "**Downloading data.**\nThis may take a minute, but it only needs to be done once.", icon="⏳")
            subprocess.run(['pip', 'uninstall', '-y', 'kaggle'])
            subprocess.run(['pip', 'install', '--user', 'kaggle'])
            try:
                # Streamlit cloud
                subprocess.run(['/home/appuser/.local/bin/kaggle', 'datasets', 'download',
                                'nih-chest-xrays/sample', '--unzip'])
            except:
                # Hugging Face
                subprocess.run(['/home/user/.local/bin/kaggle', 'datasets', 'download',
                                'nih-chest-xrays/sample', '--unzip'])
            placeholder.empty()
        except Exception as error:
            placeholder.warning(
                "An error occurred while downloading the data. Please take a screenshot of the whole page and send to the developer.")
            st.write(error)
            st.stop()
    else:
        placeholder.info(
            "**Downloading data.**\nPlease refresh the page after a few minutes.", icon="⏳")
        st.stop()


def query_to_filters():
    filters = {}
    query_params = st.experimental_get_query_params()
    if "file" in query_params:
        filters["file"] = query_params["file"][0]
    if "finding" in query_params:
        filters["finding"] = query_params["finding"]
    if "view_position" in query_params:
        filters["view_position"] = query_params["view_position"][0]
    return filters


def filters_to_query():
    query_params = {}
    if "file" in filters:
        query_params["file"] = filters["file"]
    if "finding" in filters:
        query_params["finding"] = filters["finding"]
    if "view_position" in filters:
        query_params["view_position"] = filters["view_position"]
    st.experimental_set_query_params(**query_params)


filters = query_to_filters()


@st.cache_data(ttl=60 * 60)
def load_records():
    """
    Load and convert the ECG records to a DataFrame.
    One record for each ECG taken.
    """
    def array_split(x): return x.split('|')
    def age_parse(x): return int(x[:-1])

    record_df = pd.read_csv(
        path+'sample_labels.csv',
        index_col='Image Index',
        converters={
            'Finding Labels': array_split,
            'Patient Age': age_parse
        }
    )
    return record_df


try:
    record_df = load_records()
except Exception as error:
    st.warning(
        "An error occurred while loading data. Please refresh the page to try again.")
    st.write(error)
    st.stop()


# ===============================
# Browsing history
# ===============================

with st.sidebar:
    st.write("**Browsing history:**")
    if len(st.session_state['history']) == 0:
        st.write('No CXRs viewed yet.')
    else:
        for history in st.session_state['history']:
            st.write(
                f"""<a href="?file={history}">{history} - {', '.join(record_df.loc[history]['Finding Labels'])}</a>""", unsafe_allow_html=True)


# ===============================
# CXR Filters
# ===============================

with st.form("filter_form"):

    filters['view_position'] = st.selectbox("View Position", ('Any', 'PA', 'AP'), key='new_cxr1',
                                            index=0 if not 'view_position' in filters or filters['view_position'] == 'Any' else (1 if filters['view_position'] == 'PA' else 2))

    with st.expander("Filter by findings"):
        if 'finding' in filters:
            del filters['finding']
        findings = pd.unique(record_df['Finding Labels'].explode())
        cols = st.columns(4)
        for i in range(len(findings)):
            key = findings[i]
            selected_code = cols[i % 4].checkbox(
                key.replace('_', ' '), key=f'filter_condition_{i}', value=key in filters['finding'] if 'finding' in filters else False)
            if selected_code:
                if 'finding' not in filters:
                    filters['finding'] = [key]
                elif key not in filters['finding']:
                    filters['finding'].append(key)

    submitted = st.form_submit_button(
        label='Random CXR', help='Find a new chest X-ray with the selected filters')
    if submitted:
        if 'file' in filters:
            del filters['file']
        filters_to_query()
        st.session_state["expander_state"] = True


def applyFilter():
    """
    Filter records based on filters in session state.
    """
    global record_df
    filtered_record_df = record_df
    if "view_position" in filters and filters['view_position'] != 'Any':
        filtered_record_df = filtered_record_df[filtered_record_df['View Position']
                                                == filters['view_position']]

    if "finding" in filters:
        filtered_record_df = filtered_record_df[filtered_record_df['Finding Labels'].apply(
            lambda x: any(code in filters["finding"] for code in x))]

    return filtered_record_df


filtered_record_df = applyFilter()

if len(filtered_record_df) == 0:
    st.error('No CXRs found with the selected filters.')
    st.stop()

# Select a random CXR record
if "file" not in filters or filters["file"] == None:
    record = filtered_record_df.iloc[random.randint(
        0, len(filtered_record_df) - 1)]
    filters["file"] = record.name
    filters_to_query()
else:
    record = record_df.loc[filters["file"]]

if filters["file"] in st.session_state['history']:
    st.session_state['history'].remove(filters["file"])
st.session_state['history'].insert(0, filters["file"])

st.write(f'*{len(filtered_record_df)} CXRs with the selected filters*')

st.write("----------------------------")


# ===============================
# Patient Info
# ===============================

col1, col2, col3 = st.columns(3)

with col1:
    st.write(f"**Patient ID:** {record['Patient ID']}")
    st.write(f"**Follow-up #:** {record['Follow-up #']}")

with col2:
    st.write(f"**Age:** {record['Patient Age']}")
    st.write(f"**Gender:** {record['Patient Gender']}")

with col3:
    st.write(f"**View Position:** {record['View Position']}")


# ===============================
# CXR Image
# ===============================


if st.session_state["expander_state"] == False:
    with st.spinner('Loading CXR...'):
        st.image(f"{path}images/{record.name}")
else:
    st.info('**Loading CXR...**', icon='🔃')

# ===============================
# CXR Findings
# ===============================

# Only render the expander when this is the final re-render
if st.session_state["expander_state"] == False:
    with st.expander("CXR Findings", expanded=st.session_state["expander_state"]):
        st.write(', '.join(record['Finding Labels']).replace('_', ' '))
else:
    st.write('**Loading...**')

# Dirty hack to force Streamlit to invalid the whole page and collapse the expanders
if st.session_state["expander_state"] == True:
    theme = st_js(
        """window.getComputedStyle( document.body ,null).getPropertyValue('background-color')""")


# To forcibly collapse the expanders, the whole page is rendered twice.
# In the first rerender, the expander is replaced by a placeholder markdown text.
# In the second rerender, the expander is rendered and it defaults to collapsed
# because it did not exist in the previous render.
if st.session_state["expander_state"] == True:
    st.session_state["expander_state"] = False
    # Wait for the client to sync up
    time.sleep(0.2)
    # Start the second re-render
    st.experimental_rerun()
