from sqlalchemy import Column, String, Boolean,Text,TIMESTAMP,ForeignKey,Integer,Date,DateTime,ForeignKeyConstraint
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import UUID,JSONB
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import uuid
import os
load_dotenv()

class Base(DeclarativeBase):
    pass

def get_database_url() -> str:
    user = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")

    if not all([user, password, host, port, name]):
        raise RuntimeError("Database environment variables are not fully set")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

def get_engine():
    return create_engine(get_database_url())

class User(Base):
    __tablename__ = 'testing_users'
 
    # Primary Key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
 
    # Basic user info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    application_role = Column(Text, nullable=False)
    department = Column(String(255), nullable=True)
    contact_number = Column(String(20), nullable=True)
   
    # Login tracking
    is_first_login = Column(Boolean, default=True)
    last_login_time = Column(TIMESTAMP, server_default=func.now())
 
    def __repr__(self):
        return f"<User(name={self.name}, email={self.email}, role={self.application_role})>"
    
class Request(Base):
    __tablename__ = 'testing_requests'
    created_date = Column(TIMESTAMP, server_default=func.now())
 
    # Primary Key
    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
 
    # Foreign Key to users.user_id
    requestor_id = Column(UUID(as_uuid=True), ForeignKey('testing_users.user_id'), nullable=False)
 
    # JSON-based data storage
    status = Column(Text, nullable=False)
    submission_date = Column(TIMESTAMP)
    chat_name = Column(String(255), nullable=False)
    is_cloned = Column(Boolean, nullable=False, default=False, server_default="false")
    # chat_data = Column(JSONB, nullable=True)
    form_data = Column(MutableList.as_mutable(JSONB), nullable=True)
    curr_ques_id = Column(Integer, nullable=True)
    latest_ques_id = Column(Integer, nullable=True)
    remarks = Column(String(500), nullable=True)
    current_stakeholder_email = Column(String(255), nullable=True)
    request_metadata = Column(JSONB, nullable=True)
    suggested_datasource = Column(JSONB, nullable=True)
 
    # Foreign Key to self (for sub-requests)
    parent_request_id = Column(UUID(as_uuid=True), ForeignKey('testing_requests.request_id'), nullable=True)
 
    # Counters for various data sources
    veeva_counter = Column(Integer,nullable=True)
    iqvia_counter = Column(Integer,nullable=True)
    validation = Column(JSONB, nullable=True)
    project_name = Column(String(255), nullable=True)
    requires_pdc_approval = Column(Boolean, default=False, nullable=False)
 
    def __repr__(self):
        return f"<Request(requestor_id={self.requestor_id}, status={self.status}, chat_name={self.chat_name})>"

class Vendor_list(Base):
    __tablename__ = 'truth_table_testing2'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=uuid.uuid4,
                unique=True,
                nullable=False)

    name = Column(String(255),
                  nullable=False,
                  unique=True)

    is_open_data_approved = Column(Boolean,
                         nullable=False,
                         default=False)

    is_compass_approved = Column(Boolean,
                           nullable=False,
                           default=False)

    def __repr__(self):
        return f"<Vendor_list(id={self.id}, name='{self.name}')>"
    
class DataSource(Base):
    __tablename__ = 'testing_truth_datasources'

    # Primary Key
    data_source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
 
    # Foreign Key to data_provider.data_provider_id
    data_provider_id = Column(UUID(as_uuid=True), ForeignKey('testing_truth_data_providers.data_provider_id'), nullable=False)

    # Data source details
    data_source_name = Column(String(255), nullable=False)
    processing_time_est = Column(TIMESTAMP, nullable=True)
    def __repr__(self):
        return f"<DataSource(data_source_id={self.data_source_id}, data_source_name={self.data_source_name})>"
    
class TruthDataProvider(Base):
    __tablename__ = "truth_data_providers"

    # Primary Key
    data_provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
 
    # Basic provider info
    name = Column(String(255), nullable=False)
    stake_holder_email = Column(String(255), nullable=False)
    email_cc = Column(Text, nullable=True)  # NEW: comma-separated CC emails
    form_url = Column(String(255), nullable=True)
    process_type = Column(String(50), nullable=False)  
    process_info = Column(String(255), nullable=True)  
    def __repr__(self):
        return f"<DataProvider(name={self.name}, stake_holder_email={self.stake_holder_email})>"
   
class DataProvider(Base):
    __tablename__ = 'testing_truth_data_providers'

    # Primary Key
    data_provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
 
    # Basic provider info
    name = Column(String(255), nullable=False)
    stake_holder_email = Column(String(255), nullable=False)
    email_cc = Column(Text, nullable=True)  # NEW: comma-separated CC emails
    form_url = Column(String(255), nullable=True)
    process_type = Column(String(50), nullable=False)  
    process_info = Column(String(255), nullable=True)  
    def __repr__(self):
        return f"<DataProvider(name={self.name}, stake_holder_email={self.stake_holder_email})>"
                
class TPA(Base):
    __tablename__ = 'testing_requested_tpa'

    # Primary Key
    TPA_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    
    tpa_name = Column(String(100), nullable=True, index=True)
   
    # Foreign Key
    request_id = Column(UUID(as_uuid=True), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), nullable=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey('testing_truth_datasources.data_source_id'), nullable=False)
 
    # TPA details
    additional_info_prev_status = Column(Text, nullable=True)
    datasource_tpa_status = Column(Text, nullable=False)
    tpa_signing_date = Column(TIMESTAMP, server_default=func.now(), nullable=True)
    data_access_period_start_date = Column(Date, nullable=True)
    tpa_expiry_date = Column(TIMESTAMP, nullable=True)
    usecase_for_tpa = Column(Text, nullable=True)
    remarks = Column(String(500), nullable=True)
    provider_email_to = Column(JSONB, nullable=True)  # store ["a@x.com","b@y.com"]
    provider_email_cc = Column(JSONB, nullable=True)  # store ["c@x.com"]
    data_steward_approved =  Column(Boolean,nullable=False,default=False)
    data_steward_action_date = Column(DateTime, nullable=True)
    reviewer_approved = Column(Boolean,nullable=False,default=False)
    reviewer_action_date = Column(DateTime, nullable=True)
    additional_info_required_by_reviewer = Column(Boolean, nullable=False, default=False)
    reviewer_additional_info_required_action_date = Column(DateTime, nullable=True)
    additional_info_required_by_pdc = Column(Boolean, nullable=False, default=False)
    pdc_additional_info_required_action_date = Column(DateTime, nullable=True)
    tpa_ineffect = Column(Boolean,nullable=False,default=False)
    tpa_ineffect_date = Column(Date, nullable=True)
    # __table_args__ = (
    #     ForeignKeyConstraint(
    #         ['vendor_id', 'request_id'],
    #         ['requested_vendors.vendor_id', 'requested_vendors.request_id'],
    #         name='tpa_vendor_fkey'
    #     ),
    # )
    def __repr__(self):
        return f"<TPA(TPA_id={self.TPA_id}, vendor_id={self.vendor_id}, data_source_id={self.data_source_id})>"