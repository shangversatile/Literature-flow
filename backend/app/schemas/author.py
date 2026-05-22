from pydantic import BaseModel


class AuthorRead(BaseModel):
    id: int
    name: str
    normalized_name: str


class PaperAuthorRead(BaseModel):
    author: AuthorRead
    author_order: int
