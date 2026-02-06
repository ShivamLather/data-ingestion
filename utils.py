EXTRA_DATA_PROVIDERS = [
    {
        "name": "MMIT",
        "stake_holder_email": "mmit@demo.com",
        "email_cc": None,
        "form_url": None,
        "process_type": "email",
        "process_info": "TPA initiation via email using MMIT DSF template."
    },
    {
        "name": "Optum",
        "stake_holder_email": "optum@demo.com",
        "email_cc": None,
        "form_url": None,
        "process_type": "email",
        "process_info": "TPA initiation via email using Optum DSF template."
    },
    {
        "name": "DRG",
        "stake_holder_email": "drg@demo.com",
        "email_cc": None,
        "form_url": None,
        "process_type": "email",
        "process_info": "TPA initiation via email using DRG DSF template."
    },
    {
        "name": "Others",
        "stake_holder_email": "others@demo.com",
        "email_cc": None,
        "form_url": None,
        "process_type": "email",
        "process_info": "TPA initiation via email for other data providers."
    },
]


PROVIDER_KEYWORDS = {
    "iqvia": "Iqvia",
    "veeva": "Veeva",
    "evernorth": "Evernorth",
    "optum": "Optum",
    "clarivate": "Clarivate",
    "monocl": "monocl",
    "integrichain": "Integrichain",
    "mmit": "MMIT",
    "drg": "DRG",
    "others": "Others", 
}

STATUS_MAPPING = {
    "cancelled by data provider": "CANCELLED",
    "cancelled by requestor": "CANCELLED",
    "cancelled by ssl dg": "CANCELLED",
    "expired": "EXPIRED",
    "in effect": "IN_EFFECT",
    "request initiated": "AWAITING_REVIEWER_ACTION",
    "re-submitted": "AWAITING_REVIEWER_ACTION",
    "awaiting vendor submission": "AWAITING_REVIEWER_ACTION",
    "reject": "REJECTED",
    "return to requestor": "REJECTED",
    "approved": "TPA_INITIATED",
}
