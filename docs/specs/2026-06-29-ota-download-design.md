# OTA download command design

## Goal

Add `tb ota download` to fetch an OTA package's binary to disk. The package can
be selected four ways: by UUID, by device profile, by device, or by package
title. For profile and device selectors the default is the *currently assigned*
package; a `--version` narrows to a specific version. For the title selector the
default is the *latest* version.

## Module and registration

- New `download` command in the existing `tb/commands/ota.py` group.
- Reuses `resolve_device_id` and `handle_api_error` from `tb/commands/_client.py`.
- Adds a `device_profile_api(profile)` builder in `_client.py` alongside the
  existing `device_api` / `telemetry_api` / `owner_api` builders.

## Generated client surface

`OtaPackageControllerApi` provides:

- `get_ota_package_info_by_id(ota_package_id)` -> `OtaPackageInfo`
- `get_ota_packages(page_size, page, text_search, sort_property, sort_order)` ->
  `PageDataOtaPackageInfo` (no type filter; filter client-side)
- `get_ota_packages1(device_profile_id, type, page_size, page, text_search,
  sort_property, sort_order)` -> `PageDataOtaPackageInfo`
- `download_ota_package(ota_package_id)` -> `bytes`

`DeviceControllerApi.get_device_by_id(device_id)` -> `Device` and
`DeviceProfileControllerApi`:

- `get_device_profile_names(active_only)` -> `List[EntityInfo]` (id + name)
- `get_device_profile_by_id(device_profile_id)` -> `DeviceProfile`

`OtaPackageInfo` carries `id`, `title`, `version`, `type`, `file_name`,
`created_time`. `Device` and `DeviceProfile` each carry `firmware_id` and
`software_id` (`OtaPackageId` references).

## Command signature

```
tb ota download [PACKAGE_ID]
  --device-profile, -p  NAME|UUID
  --device,         -D  NAME|UUID
  --name,           -n  TITLE
  --version,        -v  VERSION
  --latest                          (only with --name; it is the default there)
  --type,           -t  FIRMWARE|SOFTWARE   default FIRMWARE
  --output,         -o  PATH
  --force,          -f
```

## Resolution

Every selector resolves to a single `OtaPackageInfo`; its `id` is then passed to
`download_ota_package`. `--type` (default `FIRMWARE`) selects firmware vs
software for the profile/device/name selectors.

| Selector | default (no `--version`) | `--version V` |
|---|---|---|
| `PACKAGE_ID` | `get_ota_package_info_by_id` | error (id is already exact) |
| `--device-profile` | profile's assigned `firmware_id`/`software_id` per type | list packages for profile + type, pick `version == V` |
| `--device` | device's `firmware_id`/`software_id`; else its profile's | device's profile -> packages + type, pick `version == V` |
| `--name` | newest `created_time` among matching title + type | matching title + type, pick `version == V` |

- **Profile resolution** (`--device-profile`): UUID passed through; otherwise
  `get_device_profile_names()` matched on name (case-insensitive, exact). Zero
  matches -> `Device profile '<name>' not found.`; multiple -> ambiguity error.
- **Device resolution** (`--device`): via `resolve_device_id` (UUID or name).
- **Title listing** (`--name`): `get_ota_packages(text_search=TITLE, ...)` then
  client-side exact title match (the API filter is a substring) and `--type`
  filter.
- **Version selection**: filter the candidate list to `version == V`; none ->
  `No <type> package '<title-or-profile>' at version '<V>'.`; multiple sharing a
  version -> newest `created_time` wins.
- **Latest**: sort candidates by `created_time` descending, take the first.
- **Assigned-but-empty**: profile/device current with no assigned package of the
  requested type -> clear error naming the entity and type.

## Validation

- Exactly one selector required (positional id *or* one of
  `--device-profile`/`--device`/`--name`). Zero or multiple -> error.
- `--version` and `--latest` are mutually exclusive.
- `--latest` is only valid with `--name`.
- `--version` with a positional id -> error.
- `--type` must be `FIRMWARE` or `SOFTWARE`.

## Output

- `--output PATH` if given; otherwise the package's `file_name` written into the
  current directory. If the API returns no `file_name`, fall back to
  `<title>-<version>.bin`.
- Refuse to overwrite an existing target unless `--force`; error suggests
  `--force` or a different `--output`.
- Write bytes binary; print `Wrote <path> (<size>)` using the existing
  `_format_size` helper.

## Error handling

All API calls wrapped via `handle_api_error`. Resolution failures (unknown
profile/device, no matching version, empty assignment) print a specific message
and exit 1 before any download is attempted.

## Testing

`tests/test_ota.py`, mocking `OtaPackageControllerApi`, `DeviceControllerApi`,
and `DeviceProfileControllerApi` in the existing style:

- by id; by profile current (firmware and software); by profile version.
- by device current (direct id); by device current (falls back to profile);
  by device version.
- by name latest; by name specific version.
- output: `--output` path; default `file_name`; fallback name when `file_name`
  is absent; refuse overwrite without `--force`; overwrite with `--force`.
- validation errors: no selector; multiple selectors; `--version` + `--latest`;
  `--latest` without `--name`; `--version` with id.
- resolution errors: profile not found; ambiguous profile; version not found;
  title not found; profile/device with no assigned package of that type.

## Out of scope

- Resuming/streaming partial downloads and checksum verification.
- `--latest` for profile/device (they resolve to the assigned package instead).
- Bulk download of multiple packages in one invocation.
