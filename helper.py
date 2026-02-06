import pandas as pd
from sqlalchemy.orm import Session
from models import User,Request,Vendor_list,DataProvider,TruthDataProvider,DataSource,TPA
import uuid
from utils import EXTRA_DATA_PROVIDERS,PROVIDER_KEYWORDS,STATUS_MAPPING
import pandas as pd
excel_path = "C:/Users/ShivamLather/OneDrive - ProcDNA Analytics Pvt. Ltd/Desktop/DataInjestionScript/DSF Requests - History.csv.xlsx"
sheet_name = "DSF Requests - History"

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

    df["Requestor"] = (
        df["Requestor"]
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

def get_existing_user_names(session: Session):
    """
    Fetches Users from database
    
    :param session: Description
    :type session: Session
    """
    return {
        name.strip().lower()
        for (name,) in session.query(User.name).all()
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
   
def build_new_users(unique_requestors, existing_names):
    new_users = []

    for name in unique_requestors:
        if name not in existing_names:
            user = User(
                name=name,
                email=f"{name.replace(' ', '.')}.{uuid.uuid4().hex[:6]}@placeholder.com",
                application_role="requestor",
                department=None,
                contact_number=None,
                is_first_login=True
            )
            new_users.append(user)

    return new_users

def build_requests(df: pd.DataFrame, user_map: dict, existing_chat_names: set):
    requests = []
    seen_chat_names = set()

    for _, row in df.iterrows():
        chat_name = str(row["Request Number"]).strip()
        requestor_name = str(row["Requestor"]).strip().lower()

        # Skip if already exists in DB
        if chat_name in existing_chat_names:
            continue

        # Skip duplicates within Excel
        if chat_name in seen_chat_names:
            continue

        if requestor_name not in user_map:
            continue

        seen_chat_names.add(chat_name)

        project_name = (
            str(row.get("Project Name (TPA Name)")).strip()
            if pd.notna(row.get("Project Name (TPA Name)"))
            else None
        )

        req = Request(
            chat_name=chat_name,
            requestor_id=user_map[requestor_name],
            created_date=row.get("Request Received Date"),
            status="submitted",
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
                    is_open_data_approved=False,
                    is_compass_approved=False
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

def get_user_name_id_map(session: Session) -> dict:
    return {
        user.name.strip().lower(): user.user_id
        for user in session.query(User).all()
    }
   
def ingest_users(session: Session, users):
    if users:
        session.bulk_save_objects(users)
        session.commit()

def ingest_requestors(session: Session):
    requestors = extract_from_excel(df, "Requestor")


    unique_requestors = requestors.unique()

    existing_names = get_existing_user_names(session)
    new_users = build_new_users(unique_requestors, existing_names)

    ingest_users(session, new_users)

    print(f"Inserted {len(new_users)} new users")

def ingest_requests(session: Session):
    df = pd.read_excel(
        excel_path,
        sheet_name="DSF Requests - History"
    )

    df = extract_requests(df)
    user_map = get_user_name_id_map(session)
    existing_chat_names = get_existing_chat_names(session)

    request_objects = build_requests(
        df,
        user_map,
        existing_chat_names
    )

    if request_objects:
        session.bulk_save_objects(request_objects)
        session.commit()

    print(f"Inserted {len(request_objects)} new requests")

def ingest_vendors(session: Session):
    df = pd.read_excel(
        excel_path,
        sheet_name="DSF Requests - History"
    )

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
    df = pd.read_excel(
        excel_path,
        sheet_name="DSF Requests - History"
    )

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
    return {
        (t.request_id, t.data_source_id,t.vendor_id, t.tpa_name.lower())
        for t in session.query(TPA).all()
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
        if not isinstance(tpa_name, str):
            continue

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
    df = pd.read_excel(
        excel_path,
        sheet_name="DSF Requests - History"
    )

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

    print(f"Inserted {len(tpa_objects)} TPAs")
