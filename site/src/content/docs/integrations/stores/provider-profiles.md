---
title: Provider profiles
description: How a data provider describes its API once, so its users connect it with one command and no questions, and how a profile joins the bundled list.
sidebar:
  order: 3
---

A profile is a provider's saved answer to `casebench corpus add`: its address, its connector options, the variable its key lives in, the jurisdictions it covers and a search known to find a document. A user with the key connects it with one command and answers nothing.

## For users

```sh
casebench corpus add profile provider.yaml
casebench init --profile provider.yaml
```

The workbench's Jurisdictions page takes a profile too, as a source for a country.

Casebench first checks that every variable the profile names is set, in the shell or in the `.env` file `keys:` names for it. It then makes one live search with the profile's `probe` and one fetch with your key, and stops before writing anything if a required field comes back empty. Then it writes the profile's options into `casebench.yaml` under `corpora:`, along with `profile:`, the file's name, so the config stays reproducible if the profile changes later. It also writes the profile's `probe`, and its `metered`, `search_filters` and `keep` when the profile sets them, so `casebench check` and `corpus check` can search a store that cannot list its documents. A profile is read from a local file only; Casebench never fetches one from a URL.

`--jurisdiction` covers only the jurisdictions you give instead of the profile's, and `--name` names the corpus. `init --profile` can be given once for each provider.

### Bundled profiles

A bundled profile is named by its id instead of a file, such as `casebench corpus add profile ID`. `casebench init` lists bundled profiles by name, sorted, with no default. One whose key is set on your machine is marked as found, and the cursor starts on it; nothing else is ever preselected. Casebench 0.5.1 bundles none.

## For providers

Write the file in the [profile format](/developers/reference/formats/profile/) and check it:

```sh
casebench validate provider.yaml
```

Two fields matter beyond the connection:

- `metered`: `search`, `fetch` or `none`. A provider that charges per search gets each search kept, so the same search costs one call, ever.
- `keep`: what your terms let a customer keep on disk, `documents` and `searches`. `keep: []` keeps nothing, and Casebench tells the user that each call is then paid again on every run.

A profile cannot carry `link`, the address where a person reads a document on your site; your users add it to their corpus block. Hand the file to your users, from your docs for example. A provider whose API needs logic a profile cannot hold, such as OAuth or signed requests, publishes a connector plugin and a profile that names it. See [Write a plugin or a profile](/integrations/extend/plugins/).

## Neutrality

The bundled list has no default, no order but the name, and no ranking words. A test checks that profiles are sorted and that none is preselected without its key. Every provider meets the same bar to be bundled.
