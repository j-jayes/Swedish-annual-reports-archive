from pydantic import BaseModel
from typing import List

class YearNames(BaseModel):
    year: int
    names: List[str]

# Example usage
data = {
    "year": 1901,
    "names": [
        "O. Fr. Wijkman",
        "V. Åkerman",
        "G. A. Granström",
        "Sven Gyllensvärd",
        "G. Wenström"
    ]
}

model = YearNames(**data)
print(model.json(indent=2))
