# joistlogic-data

Public data for the JoistLogic app.

`price_index.json` holds the latest U.S. Producer Price Index value for each material category JoistLogic prices (lumber, plywood, gypsum, ready-mix, concrete products, asphalt roofing, insulation, paint, plastics, metals). The app scales its built-in September 2026 prices by `latest ÷ base` for each category.

- Source: U.S. Bureau of Labor Statistics PPI by commodity (public domain), with FRED as a fallback.
- Updated by `.github/workflows/price-index.yml` on the 20th of each month (or run it by hand from the Actions tab).
- Served by GitHub Pages at https://shanesuan.github.io/joistlogic-data/price_index.json

Optional: add a free BLS API key as the repository secret `BLS_API_KEY` (https://data.bls.gov/registrationEngine/).
