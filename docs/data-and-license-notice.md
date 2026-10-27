# Data and license notice

## Code

MarketAtlas source code and its tracked documentation are offered under the
[MIT License](../LICENSE). That license does not grant rights to third-party
data, source schemas, data dictionaries, extracts, screenshots, or derived
outputs.

## Public demonstration data

The portable fixture in this repository is deliberately synthetic. It is the
only data path approved for a public contributor walkthrough. Its manifest and
CLI output label it `synthetic: true`.

## Local source integration

MacroMedallion and EcoMedallion name the same optional local upstream asset.
The configured `macro_medallion` database is read only through the scoped
source-reader role. The six `supported_live` interfaces are approved for the
local technical contract only; they are classified restricted internal-only and
that approval is not redistribution permission.
All other readable relations are not onboarded.

Do not commit, publish, screenshot for public use, or attach to an issue any
raw source rows, credentials, connection strings, private hostnames, source
extracts, or unreviewed derived outputs. `configs/local.toml` and generated
local data remain ignored. Josh is the local source/data owner and has approved
internal-only use; a separate external terms decision is required before any
non-synthetic artifact is shared.

## Dependency and branding notice

The React demonstration follows the architectural pattern selected in
ADR-001; it does not copy QuantMeridian source modules. Review third-party
package notices from the locked dependency manifests before a distributed
binary or hosted release. MarketAtlas and its fixture labels must remain
visible in screenshots so synthetic content is not mistaken for real market
data.
