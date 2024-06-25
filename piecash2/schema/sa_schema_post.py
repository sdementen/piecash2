# mypy: ignore-errors
# list all glasses with a guid property (that can be linked to in Slot/Recurrence through obj_guid)
gl = globals()
name2kls = {n: gl[n] for n in klswithguid_names}  # noqa: F821
