from pasqal_cloud import Job


class TestJob:
    def test_job_instantiation_with_extra_field(self, job):
        """Instantiating a job with an extra field should not raise an error.

        This enables us to add new fields in the API response on the jobs endpoint
        without breaking compatibility for users with old versions of the SDK where
        the field is not present in the Job class.
        """
        job_dict = job.dict()  # job data expected by the SDK
        # We add an extra field to mimick the API exposing new values to the user
        job_dict["new_field"] = "any_value"

        new_job = Job(**job_dict)  # this should raise no error
        assert (
            new_job.new_field == "any_value"
        )  # The new value should be stored regardless
