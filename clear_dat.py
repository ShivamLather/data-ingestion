from sqlalchemy.orm import Session
from models import TPA,DataSource,DataProvider,Vendor_list,Request,User

def delete_all_data(session: Session):
    """
    Deletes all data from ingestion tables in FK-safe order.
    """

    print("Deleting TPAs...")
    session.query(TPA).delete(synchronize_session=False)

    print("Deleting DataSources...")
    session.query(DataSource).delete(synchronize_session=False)

    print("Deleting DataProviders...")
    session.query(DataProvider).delete(synchronize_session=False)

    print("Deleting Vendors...")
    session.query(Vendor_list).delete(synchronize_session=False)

    print("Deleting Requests...")
    session.query(Request).delete(synchronize_session=False)

    print("Deleting Users...")
    session.query(User).delete(synchronize_session=False)

    session.commit()
    print("✅ All data deleted successfully")
