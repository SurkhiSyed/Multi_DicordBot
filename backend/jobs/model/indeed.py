from pydantic import BaseModel


class Indeed(BaseModel):
    """
    Represents the data structure of a Indeed job posting.
    """

    name: str
    company: str
    location_type: str
    job_type: str
    # posting_date: str
    application_link: str
    location: str
    description: str