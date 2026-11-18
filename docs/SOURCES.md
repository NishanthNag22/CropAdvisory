# Source provenance and extending crops

Knowledge entries are concise paraphrases of public TNAU guidance. They are stored locally for offline retrieval and retain their original URLs. Review date for the new records: 18 November 2026.

| Crop / topic | Source |
| --- | --- |
| Tomato soil pH | https://agritech.tnau.ac.in/horticulture/horti_vegetables_tomato_Soil.html |
| Tomato irrigation | https://www.agritech.tnau.ac.in/org_farm/orgfarm_tomato_water.html |
| Tomato nitrogen symptoms | https://agritech.tnau.ac.in/horticulture/plant_nutri/tomato_nitro.html |
| Transplanted rice irrigation and stages | https://agritech.tnau.ac.in/agriculture/agri_irrigationmgt_cereals_rice1.html |
| Wheat irrigation and stages | https://agritech.tnau.ac.in/agriculture/agri_irrigationmgt_wheat.html |
| Wheat soil-test-led nutrition | https://agritech.tnau.ac.in/agriculture/agri_cropproduction_wheat_fieldpreparation.html |
| Irrigated cotton irrigation and stages | https://agritech.tnau.ac.in/agriculture/agri_cotton_irri_irrigation%20management.html |

The legacy tomato records retain the original guidance and verification flags; their original review dates are unknown (null). The tomato water-management page could not be re-fetched during the final review. It retains prototype provenance rather than receiving a new review date. New rice, wheat and cotton records intentionally omit treatment dosages and fixed irrigation schedules. Regional practices are not generalized across all climates or production systems. `verified: true` means the source reference was reviewed; it does not mean every downstream claim has been independently verified.

## Add knowledge

1. Obtain authoritative crop- and region-specific references and review their applicability.
2. Add concise records with `crop`, `topic`, `guidance`, `region`, `source`, `source_url`, `reviewed_on` and `verified` to the knowledge JSON.
3. For a new crop, extend `CROPS` and the UI/CLI choices. For a new topic, add topic vocabulary in `ALIASES` or use the local semantic backend.
4. Add reviewed retrieval and abstention cases; ensure the crop never receives another crop's records.
5. Test claim screening and translation with numerical, negation and regional-scope cases.

Public provenance does not remove the need for crop experts to review advice for a particular field.

## Applicability fields

New records expose `regions`, `seasons`, `production_systems`, `published_on`, `reviewed_on` and optional `valid_until`. The bundled publication dates and unspecified seasons remain null/empty because they have not been verified. The application reports that gap rather than manufacturing dates or universal applicability. `max_source_age_days` marks older metadata for currency review; an explicit validity expiry excludes a record.
