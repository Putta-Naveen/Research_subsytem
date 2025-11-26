from pydantic import BaseModel
from typing import Optional

# This will be set from Rag_server.py when imported
END_USER_ID = None

class SearchQuery(BaseModel):
    query: str
    end_user_id: str = None  # Will use END_USER_ID at runtime
    
    def __init__(self, **data):
        # Set default for end_user_id if not provided and END_USER_ID is available
        if 'end_user_id' not in data and END_USER_ID:
            data['end_user_id'] = END_USER_ID
        super().__init__(**data)
