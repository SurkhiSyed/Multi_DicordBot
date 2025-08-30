from pydantic import BaseModel


class Linkedin(BaseModel):
    """
    Represents the data structure of a Linkedin job posting.
    """

    name: str
    company: str
    location_type: str
    job_type: str
    posting_date: str
    application_link: str
    location: str
    description: str