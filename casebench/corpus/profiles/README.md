# Bundled profiles

Each `<id>.yaml` here is a data provider's profile that `casebench init` lists by name ([decision 0033](../../../docs/decisions/0033-data-provider-profiles.md)). A profile joins only with:

- `samples/<id>/search.json` and `samples/<id>/fetch.json`: one recorded search and one recorded fetch that the provider allows to be published;
- a `maintainer` who answers issues about it;
- `uv run pytest tests/corpus/test_bundled_profiles.py` passing, which checks those recordings offline.

Every profile meets the same bar and is listed the same way: by name, in alphabetical order, here and in `casebench init`. None is listed above another, none is preselected unless its key is set on the user's machine, and none is described with ranking words.

[PLUGINS.md](../../../PLUGINS.md) has the steps.
