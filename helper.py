import pandas as pd
from sqlalchemy.orm import Session
from models import User,Request,Vendor_list,DataProvider,TruthDataProvider,DataSource,TPA,Vendor
import uuid
from utils import EXTRA_DATA_PROVIDERS,PROVIDER_KEYWORDS,STATUS_MAPPING
import pandas as pd
import random
import json

excel_path = "C:/Users/ShivamLather/OneDrive - ProcDNA Analytics Pvt. Ltd/Desktop/DataInjestionScript/c.xlsx"
sheet_name = "Sheet1"

df = pd.read_excel(excel_path, sheet_name=sheet_name)


def extract_from_excel(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Extracts data from excel
    """
    return (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )
    
def extract_requests(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["used_name"] = (
        df["used_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["Request Number"] = (
        df["Request Number"]
        .astype(str)
        .str.strip()
    )

    return df

def extract_provider_from_text(text: str) -> str | None:
    text = text.lower()

    for keyword, provider_name in PROVIDER_KEYWORDS.items():
        if keyword in text:
            return provider_name

    return None

def get_data_provider_map(session: Session) -> dict:
    return {
        dp.name.lower(): dp.data_provider_id
        for dp in session.query(DataProvider).all()
    }

def get_existing_datasources(session: Session) -> set:
    return {
        (ds.data_provider_id, ds.data_source_name.lower())
        for ds in session.query(DataSource).all()
    }

def get_existing_user_ids(session: Session):
    return {
        str(user_id)
        for (user_id,) in session.query(User.user_id).all()
    }

def get_existing_vendor_names(session: Session) -> set:
    return {
        name.strip().lower()
        for (name,) in session.query(Vendor_list.name).all()
        if name
    }
 
def get_existing_chat_names(session: Session) -> set:
    return {
        chat_name
        for (chat_name,) in session.query(Request.chat_name).all()
        if chat_name
    }
   
def build_new_users(df: pd.DataFrame, existing_user_ids: set):

    users = []
    seen_user_ids = set()
    for _, row in df.iterrows():
        if pd.isna(row["user_id"]):
            continue

        if row["user_id"] in existing_user_ids:
            continue
        if row["user_id"] in seen_user_ids:
            continue
        user = User(
            user_id=row["user_id"],
            name=row["used_name"],
            email=row["email"],
            application_role="requestor",
        )

        users.append(user)
        existing_user_ids.add(row["user_id"])
        seen_user_ids.add(row["user_id"])

    return users

def build_requests(df: pd.DataFrame, existing_chat_names: set):
    requests = []
    seen_chat_names = set()

    for _, row in df.iterrows():
        chat_name = str(row["Request Number"]).strip()
        requestor_id = row.get("user_id")

        # Skip if already exists in DB
        if chat_name in existing_chat_names:
            continue

        # Skip duplicates within Excel
        if chat_name in seen_chat_names:
            continue

        if pd.isna(requestor_id):
            continue

        seen_chat_names.add(chat_name)

        project_name = (
            str(row.get("Project Name (TPA Name)")).strip()
            if pd.notna(row.get("Project Name (TPA Name)"))
            else None
        )

        req = Request(
            chat_name=chat_name,
            requestor_id=requestor_id,
            submission_date=row.get("Request Received Date"),
            status="under_review",
            is_cloned=False,
            project_name=project_name
        )

        requests.append(req)

    return requests

def build_new_vendors(vendor_names, existing_names):
    vendors = []

    for name in vendor_names:
        if name not in existing_names:
            vendors.append(
                Vendor_list(
                    name=name,
                )
            )

    return vendors

def build_datasources(
    df: pd.DataFrame,
    provider_map: dict,
    existing_datasources: set
):
    datasources = []

    for _, row in df.iterrows():
        raw_text = row.get("TPA Required with (IQVIA/VOD/others)")

        if not isinstance(raw_text, str) or not raw_text.strip():
            continue

        provider_name = extract_provider_from_text(raw_text)
        if not provider_name:
            continue

        provider_key = provider_name.lower()
        if provider_key not in provider_map:
            continue

        provider_id = provider_map[provider_key]
        datasource_name = raw_text.strip()

        key = (provider_id, datasource_name.lower())
        if key in existing_datasources:
            continue

        ds = DataSource(
            data_provider_id=provider_id,
            data_source_name=datasource_name,
            processing_time_est=None
        )

        datasources.append(ds)
        existing_datasources.add(key)

    return datasources

def get_user_map_from_df(df: pd.DataFrame):

    return {
        str(row["Request Number"]).strip(): row["user_id"]
        for _, row in df.iterrows()
        if pd.notna(row["user_id"])
    }
   
def ingest_users(session: Session, users):
    if users:
        session.bulk_save_objects(users)
        session.commit()

def ingest_requestors(session: Session):

    existing_user_ids = get_existing_user_ids(session)
    new_users = build_new_users(df, existing_user_ids)

    ingest_users(session, new_users)

    print(f"Inserted {len(new_users)} new users")

def ingest_requests(session: Session):
    global df
    df = extract_requests(df)
    existing_chat_names = get_existing_chat_names(session)

    request_objects = build_requests(
        df,
        existing_chat_names
    )

    if request_objects:
        session.bulk_save_objects(request_objects)
        session.commit()

    print(f"Inserted {len(request_objects)} new requests")

def ingest_vendors(session: Session):

    vendor_series = extract_from_excel(df,"3rd Party Vendor")
    unique_vendors = vendor_series.unique()

    existing_vendor_names = get_existing_vendor_names(session)
    new_vendors = build_new_vendors(unique_vendors, existing_vendor_names)

    if new_vendors:
        session.bulk_save_objects(new_vendors)
        session.commit()

    print(f"Inserted {len(new_vendors)} new vendors")

def copy_data_providers(session: Session):
    """
    Copies data from truth_data_provider → truth_data_providers
    """

    source_rows = session.query(TruthDataProvider).all()
    existing_names = {
        name for (name,) in session.query(DataProvider.name).all()
    }

    new_rows = []

    for row in source_rows:
        if row.name in existing_names:
            continue
        dp = DataProvider(
            name=row.name,
            stake_holder_email=row.stake_holder_email,
            email_cc=row.email_cc,
            form_url=row.form_url,
            process_type=row.process_type,
            process_info=row.process_info
        )
        new_rows.append(dp)

    if new_rows:
        session.bulk_save_objects(new_rows)
        session.commit()

    print(f"Copied {len(new_rows)} data providers")

def seed_extra_data_providers(session: Session):
    existing_names = {
        name.lower()
        for (name,) in session.query(DataProvider.name).all()
        if name
    }

    new_rows = []

    for dp in EXTRA_DATA_PROVIDERS:
        if dp["name"].lower() in existing_names:
            continue

        new_rows.append(DataProvider(**dp))

    if new_rows:
        session.bulk_save_objects(new_rows)
        session.commit()

    print(f"Inserted {len(new_rows)} extra data providers")

def ingest_datasources(session: Session):
    provider_map = get_data_provider_map(session)
    existing_datasources = get_existing_datasources(session)

    new_datasources = build_datasources(
        df,
        provider_map,
        existing_datasources
    )

    if new_datasources:
        session.bulk_save_objects(new_datasources)
        session.commit()

    print(f"Inserted {len(new_datasources)} data sources")

def map_tpa_status(raw_status: str) -> str | None:
    if not isinstance(raw_status, str):
        return None

    raw = raw_status.strip().lower()
    return STATUS_MAPPING.get(raw)

def get_datasource_map(session: Session) -> dict:
    return {
        ds.data_source_name.lower(): ds.data_source_id
        for ds in session.query(DataSource).all()
    }

def get_vendor_map(session: Session) -> dict:
    """
    { vendor_name(lower) -> vendor_id }
    """
    return {
        v.name.lower(): v.id
        for v in session.query(Vendor_list).all()
    }

def get_existing_tpas(session: Session) -> set:
    rows = session.query(
        TPA.request_id,
        TPA.data_source_id,
        TPA.vendor_id,
        TPA.tpa_name
    ).all()

    return {
        (r_id, ds_id, v_id, name.lower())
        for r_id, ds_id, v_id, name in rows
        if name
    }

def clean_datetime(value):
    if pd.isna(value):
        return None
    return value

def resolve_datasource_id(tpa_required: str, datasource_map: dict):
    if not isinstance(tpa_required, str):
        return None

    key = tpa_required.strip().lower()
    return datasource_map.get(key)

def get_request_map(session: Session) -> dict:
    """
    { chat_name -> request_id }
    """
    return {
        r.chat_name.strip(): r.request_id
        for r in session.query(Request).all()
    }

def generate_unique_tpa_name(existing_tpas, request_id, datasource_id, vendor_id):
    while True:
        name = f"TPA_{random.randint(0, 9_999_999):07d}"
        dedupe_key = (request_id, datasource_id, vendor_id, name.lower())
        if dedupe_key not in existing_tpas:
            return name

def build_tpas(
    df: pd.DataFrame,
    request_map: dict,
    datasource_map: dict,
    vendor_map:dict,
    existing_tpas: set
):
    tpas = []

    for _, row in df.iterrows():

        # --- Request lookup ---
        chat_name = str(row.get("Request Number")).strip()
        request_id = request_map.get(chat_name)
        if not request_id:
            continue
        
        raw_ds = row.get("TPA Required with (IQVIA/VOD/others)")
        if not isinstance(raw_ds, str):
            continue
        # --- Data source lookup ---
        datasource_id = datasource_map.get(raw_ds.strip().lower())
        if not datasource_id:
            continue
        
        # --- vendor ---
        raw_vendor = row.get("3rd Party Vendor")
        if not isinstance(raw_vendor, str):
            continue

        vendor_id = vendor_map.get(raw_vendor.strip().lower())
        if not vendor_id:
            continue
        
        # --- TPA name ---
        tpa_name = row.get("TPA#")
        if not isinstance(tpa_name, str) or not tpa_name.strip():
            tpa_name = generate_unique_tpa_name(existing_tpas,request_id,datasource_id,vendor_id)
        else:
            tpa_name = tpa_name.strip()

        dedupe_key = (request_id, datasource_id,vendor_id, tpa_name.lower())
        if dedupe_key in existing_tpas:
            continue
        
        # --- Status mapping ---
        mapped_status = map_tpa_status(row.get("Current Status"))
        if not mapped_status:
            continue
        
        tpa = TPA(
            request_id=request_id,
            data_source_id=datasource_id,
            vendor_id=vendor_id,
            tpa_name=tpa_name.strip(),
            datasource_tpa_status=mapped_status,
            data_access_period_start_date=row.get("Data Share Approval Date"),
            tpa_signing_date=clean_datetime(row.get("TPA Approved date")),
            tpa_ineffect=(mapped_status == "IN_EFFECT"),
            tpa_ineffect_date=clean_datetime(row.get("Agreement Effective Start Date")),
            tpa_expiry_date=clean_datetime(row.get("Agreement Effective End Date")),
            remarks=None if pd.isna(row.get("Comments")) else str(row.get("Comments")).strip(),
        )

        tpas.append(tpa)
        existing_tpas.add(dedupe_key)

    return tpas

def ingest_tpas(session: Session):

    request_map = get_request_map(session)
    datasource_map = get_datasource_map(session)
    existing_tpas = get_existing_tpas(session)
    vendor_map = get_vendor_map(session)
    
    tpa_objects = build_tpas(
        df,
        request_map,
        datasource_map,
        vendor_map,
        existing_tpas
    )

    if tpa_objects:
        session.bulk_save_objects(tpa_objects)
        session.commit()
    ingest_formdata(session,df,request_map)
    print(f"Inserted {len(tpa_objects)} TPAs")

def build_formdata(request, tpas, vendor_map, datasource_map):

    vendors = []
    vendor_seen = set()

    datasources = []
    ds_seen = set()

    for tpa in tpas:

        # --- Vendor ---
        vendor_name = vendor_map.get(tpa.vendor_id)

        if vendor_name and vendor_name not in vendor_seen:
            vendors.append({
                "vendor_name": vendor_name,
                "vendor_type": "Primary"
            })
            vendor_seen.add(vendor_name)

        # --- Datasource ---
        datasource_name = datasource_map.get(tpa.data_source_id)

        if datasource_name and datasource_name not in ds_seen:
            datasources.append(datasource_name)
            ds_seen.add(datasource_name)

    formdata = [
        {
            "question": "Hello!\nI'm your Data Access Assistant\nHere, you can easily request the data you need through a simple conversation. Just tell me what you're working on and I'll guide you through the rest, step-by-step. Let's get started!",
            "in_pdc_flow": False,
            "question_id": 1,
            "question_type": "text",
            "parent_ques_ids": [],
            "suggested_response": [],
            "previous_edit_response": "",
            "response": f"I'm working on a project titled '{request.project_name}'"
        },
        {
            "key": "",
            "modes": [
                "general"
            ],
            "options": [
            {
                "option": "Boehringer employees or contractors(Working as part of Boehringer team)"
            },
            {
                "option": "External third-party vendors"
            }
            ],
            "question": "Before we continue, who will be using this data?",
            "response": "External third-party vendors",
            "question_id": 2,
            "question_type": "single_select",
            "question_label": "Who will be using the data",
            "parent_ques_ids": [],
            "suggested_response": [],
            "previous_edit_response": ""
        },
        {
            "key": "data_access_type",
            "modes": [
                "general",
                "internal"
            ],
            "options": [
            {
                "option": "I want access to Patient de-identified data"
            },
            {
                "option": "I want access to Octopoda / DataLand"
            }
            ],
            "question": "Are you looking for a patient level dataset? Please note, in case you are looking for patient identified data, reach out to [Sanjeev Garr](mailto:sanjeev.garr@boehringer-ingelheim.com) for further assistance.",
            "response": "I want access to de-identified data",
            "question_id": 3,
            "question_type": "single_select",
            "question_label": "Data Access Disclaimer",
            "parent_ques_ids": [],
            "suggested_response": [],
            "previous_edit_response": ""
        },
        {
            "key": "usecase_name",
            "question": "What is the project name for this usecase?",
            "response": request.project_name,
            "in_pdc_flow": False,
            "question_id": 5,
            "question_type": "text",
            "question_label": "Project Name",
            "parent_ques_ids": [],
            "suggested_response": [
            "CKD PDT Q4 '24"
            ],
            "previous_edit_response": ""
        },
        {
            "key": "selected_datasource",
            "options": [],
            "question": "Given a few data sources, which one would you prefer to leverage here?",
            "in_pdc_flow": False,
            "question_id": 7,
            "question_type": "datasource_list",
            "question_label": "Data Source Selected",
            "parent_ques_ids": [],
            "suggested_response": [],
            "previous_edit_response": "",
            "response": datasources
        },
        {
                "key": "vendors",
            "options": [],
            "question": "Could you list the vendors involved in this project? \nNOTE: If you plan to share this information with any secondary vendor, please provide their details below.",
            "response": vendors,
            "in_pdc_flow": False,
            "question_id": 9,
            "question_type": "vendor_list",
            "question_label": "Vendors Involved",
            "parent_ques_ids": [
            7
            ],
            "suggested_response": [],
            "previous_edit_response": ""
        },
        {
            "key": "promotional_use",
            "question": "Will the data be used for any promotional purpose, disease state awareness education, or non-personal communication purpose?",
            "response": "No",
            "in_pdc_flow": False,
            "question_id": 17,
            "question_type": "boolean",
            "question_label": "Promotional Use of Data",
            "parent_ques_ids": [],
            "suggested_response": [
            "No"
            ],
            "previous_edit_response": ""
        },
        {
            "question_id": 26,
            "response": True
        }
    ]

    return formdata

def get_vendor_name_map(session):
    return {
        v.id: v.name
        for v in session.query(Vendor_list).all()
    }


def get_datasource_name_map(session):
    return {
        ds.data_source_id: ds.data_source_name
        for ds in session.query(DataSource).all()
    }
    
def ingest_formdata(session, df, request_map):
    vendor_name_map = get_vendor_name_map(session)
    datasource_name_map = get_datasource_name_map(session)
    processed_requests = set()

    for _, row in df.iterrows():

        chat_name = str(row["Request Number"]).strip()

        if chat_name not in request_map:
            continue

        request_id = request_map[chat_name]

        # Prevent duplicate processing (multiple TPAs per request)
        if request_id in processed_requests:
            continue

        request = session.query(Request).filter(
            Request.request_id == request_id
        ).first()

        if not request:
            continue

        # Skip if formdata already exists
        if request.form_data:
            processed_requests.add(request_id)
            continue

        tpas = session.query(TPA).filter(
            TPA.request_id == request_id
        ).all()

        if not tpas:
            continue

        formdata = build_formdata(request, tpas,vendor_name_map,datasource_name_map)

        request.form_data = formdata

        processed_requests.add(request_id)

    session.commit()
    
def ingest_requested_vendors(session: Session, df: pd.DataFrame, request_map: dict):

    vendors_to_insert = []
    seen_pairs = set()

    # Load existing vendors to avoid duplicates
    existing = {
        (v.vendor_id, v.request_id)
        for v in session.query(Vendor.vendor_id, Vendor.request_id).all()
    }

    for _, row in df.iterrows():

        chat_name = str(row.get("Request Number")).strip()
        request_id = request_map.get(chat_name)

        if not request_id:
            continue

        vendor_name = row.get("3rd Party Vendor")
        vendor_email = row.get("Vendor Email")
        vendor_contact = row.get("Vendor Contact")
        vendor_type = row.get("Vendor Type")

        if not isinstance(vendor_name, str):
            continue

        vendor_name = vendor_name.strip()

        # Generate deterministic vendor_id per row
        vendor_id = uuid.uuid4()

        key = (vendor_id, request_id)

        if key in existing or key in seen_pairs:
            continue

        vendor = Vendor(
            vendor_id=vendor_id,
            request_id=request_id,
            company_name=vendor_name,
            vendor_email=vendor_email if isinstance(vendor_email, str) else "",
            vendor_name=vendor_name,
            vendor_contact_details=[vendor_contact] if pd.notna(vendor_contact) else None,
            vendor_type=vendor_type if isinstance(vendor_type, str) else "Primary"
        )

        vendors_to_insert.append(vendor)
        seen_pairs.add(key)

    if vendors_to_insert:
        session.bulk_save_objects(vendors_to_insert)
        session.commit()

    print(f"Inserted {len(vendors_to_insert)} requested vendors")