from pydantic import BaseModel, validator


class TestModel(BaseModel):
    set: int | None = None

    @validator("set", always=True)
    def _validate_set(cls, set):
        print("validating")
        return 3


test = TestModel(**{})
print(test.set)
