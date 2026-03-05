from helper import ingest_requestors,ingest_requests,ingest_vendors,copy_data_providers,seed_extra_data_providers,ingest_datasources,ingest_tpas
from models import get_engine,Base
from sqlalchemy.orm import sessionmaker
from models import TPA
from clear_dat import delete_all_data

def main():
    session = None
    try:
        engine = get_engine()
        # Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        ingest_requestors(session)
        ingest_requests(session)
        ingest_vendors(session)
        copy_data_providers(session)
        seed_extra_data_providers(session)
        ingest_datasources(session)
        ingest_tpas(session)
        
        # delete_all_data(session)
        print(session)
    except Exception:
        if session is not None:
            session.rollback()
        raise
    finally:
        if session is not None:
            session.close()

main()