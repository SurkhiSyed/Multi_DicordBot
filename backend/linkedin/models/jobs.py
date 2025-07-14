from pydantic import BaseModel


class Jobs(BaseModel):
    """
    Represents the data structure of a Job.
    """

    name: str
    company: str
    location_type: str
    job_type: str
    posting_date: str
    application_link: str
    location: str
    description: str