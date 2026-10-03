# Data

Two kinds of data: the evidence that the problem exists (with source, year and country), and every dataset this project is built with (source, licence, size). Synthetic data is labelled as synthetic. The last section says what the data does not cover.

Every figure in the problem and device sections was found by one researcher and re-checked by a second against the source before it was copied here. Wording such as "reported" or "implementer source" is kept on purpose.

## 1. Problem evidence (Kenya unless stated)

**Children die, and care is late**

| # | Figure | Source |
|---|---|---|
| P1 | Under-5 mortality 41 per 1,000 live births; infant mortality 32 per 1,000 (5 years before the survey) | Kenya Demographic and Health Survey (KDHS) 2022, Key Indicators Report, p.48. https://dhsprogram.com/pubs/pdf/PR143/PR143.pdf |
| P2 | Pneumonia caused 15% of under-5 deaths, almost 9,000 deaths (2018 data) | *Fighting for Breath: Kenya*, UNICEF / Save the Children 2020, p.2 (underlying source: WHO MCEE). https://i.stci.uk/dam/kenya_fighting_for_breath_2020.pdf-ch11224991.pdf/t5351fms24ot0un3y8y1xx2qn06uhs10.pdf |
| P3 | At the Kenya CHAMPS sites, 74% (213/287) of deaths of children aged 1 to 59 months had at least one delay in care; 64% across all 7 CHAMPS sites (sites are not population-representative) | Garcia Gomez et al., PLOS Global Public Health 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC10852234/ |
| P4 | Advice or treatment was sought for 69.5% of under-5s with fever in the past 2 weeks (n=2,890) and 82.3% with ARI symptoms (n=293). "Sought" includes shops and drug sellers | KDHS 2022 Final Report (FR380), Tables 10.8 and 10.6. https://dhsprogram.com/pubs/pdf/FR380/FR380.pdf |
| P5 | 23.7% of women aged 15 to 49 say distance to a health facility is a serious problem when they need care for themselves (n=16,716) | KDHS 2022 FR380, Table 9.19 (same URL) |

**Health workers are scarce and often absent**

| # | Figure | Source |
|---|---|---|
| P6 | Health-worker absence 52.8% on unannounced visits (public facilities 56.7%); all four tracer conditions correctly diagnosed by 19.6% of providers (doctors 31.6%, clinical officers 25.7%, nurses 12.1%) | World Bank / Ministry of Health, Kenya Service Delivery Indicators (SDI) Health Survey 2018 report (May 2019), exec. summary and Table 15. https://microdata.worldbank.org/catalog/3872/download/49944 |
| P7 | 2.6 medical doctors and 12.12 nursing and midwifery personnel per 10,000 people (2024) | WHO Global Health Observatory, accessed Oct 2026. https://ghoapi.azureedge.net/api/HWF_0001?$filter=SpatialDim%20eq%20'KEN' and https://ghoapi.azureedge.net/api/HWF_0006?$filter=SpatialDim%20eq%20'KEN' |

**Referrals get lost**

| # | Figure | Source |
|---|---|---|
| P8 | In one sub-county (Endebess), of 112 children referred by volunteers in a childhood-pneumonia referral study, referral forms were on file at the hospital for 19 (17%) | Opuba et al. 2025, abstract. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=PMCID:PMC12135120&resultType=core&format=json |
| P9 | Integrated community case management (iCCM) implemented in 21 of 47 counties (2020) | *Fighting for Breath: Kenya* 2020, p.6 (URL above) |

**Distance (weak support for "too far"; P5 is the better figure)**

| # | Figure | Source |
|---|---|---|
| P10 | 95.8% of Kenyans are within 1 hour of a facility by motorised transport and 86.5% on foot (globally 91.1% / 56.7%) | Weiss et al. 2020, *Nature Medicine* 26:1835-1838, Supplementary Table 2. https://www.nature.com/articles/s41591-020-1059-1 ; https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41591-020-1059-1/MediaObjects/41591_2020_1059_MOESM2_ESM.xlsx |

**Phones and SMS**

| # | Figure | Source |
|---|---|---|
| F1 | Women aged 15 to 49: 77.5% own a mobile phone, 42.7% a smartphone; rural women 69.6% / 27.5% | KNBS / Communications Authority, *Key Indicators on Uptake of ICTs based on the 2022 KDHS*. https://www.ca.go.ke/sites/default/files/2024-12/ICT-KDHS%20Analytical%20Fact%20Sheet.pdf |
| F2 | Adults 18+ (2024): women 93% own a mobile, 42% a smartphone, 43% use mobile internet (men 95% / 50% / 55%) | GSMA, *The Mobile Gender Gap Report 2025*, Figure 2. https://www.gsma.com/wp-content/uploads/2025/12/The-Mobile-Gender-Gap-Report-2025.pdf |
| F3 | 48.7 million smartphone and 29.6 million feature-phone connections; 14.4 billion SMS in the quarter; average pay-as-you-go SMS price KES 1.18 | Communications Authority of Kenya, Sector Statistics Report Q2 FY2025/26 (Oct to Dec 2025). https://www.ca.go.ke/sites/default/files/2026-04/Sector%20Statistics%20Report%20Q2%202025-2026.pdf |

**Community health promoters (CHPs) and eCHIS**

| # | Figure | Source |
|---|---|---|
| C1 | Each CHP serves 100 households; 100,000 CHP kits with smartphones rolled out from 25 Sep 2023 to all 47 counties | President's speech at the flagging-off of CHP kits, 25 Sep 2023. https://president.go.ke/wp-content/uploads/AT-THE-FLAGGING-OFF-OF-COMMUNITY-HEALTH-PROMOTERS-KITS.pdf |
| C2 | 107,000 CHPs; the national government pays 50% of the stipend | Kenya Yearbook (government), 20 Feb 2024. https://governmentdevelopments.kenyayearbook.go.ke/?p=2615 |
| C3 | Kenya's electronic Community Health Information System (eCHIS) is built on Medic's Community Health Toolkit, planned for 95,000+ CHPs and CHAs in all 47 counties | Medic, Q3 2023 impact report (implementer source). https://medic.org/q3-2023-impact-report/ |
| C4 | About 110,000 smartphones provided to CHPs, "locally assembled and provided by Safaricom" | Press-reported: The Standard (https://www.standardmedia.co.ke/health/health-science/article/2001498549/health-ministry-rolls-out-electronic-system-to-boost-services); The Star, 20 Oct 2023 (https://www.the-star.co.ke/news/2023-10-20-state-to-provide-110000-smartphones-for-use-by-chp); Citizen Digital, 8 Nov 2023 (https://citizen.digital/news/cs-nakhumicha-distributes-kenyan-made-phones-to-community-health-promoters-n330897) |
| C6 | Risk: MPs said over 60% of the phones given to CHPs don't work | The Star, 13 May 2026 (press-reported). https://www.the-star.co.ke/news/2026-05-13-mps-question-quality-of-health-workers-phones |

**Earlier SMS tools named in the brief**

| # | Figure | Source |
|---|---|---|
| T1 | Mwana (Zambia): infant HIV results reached the facility in 26.7 days instead of 44.2, and the caregiver in 35.0 days instead of 66.8 | *Bulletin of the WHO* 2012;90(5):348-356. https://pmc.ncbi.nlm.nih.gov/articles/PMC3341697 |
| T2 | mTrac (Uganda): facilities without a malaria-drug stockout rose from 21% to 84.6%; on-time SMS reports by village volunteers fell from 60% to 9% | DFID 2014, via SDSN TReNDS case study 2018. https://files.unsdsn.org/CaseStudy_mTRAC_Sept2018.pdf |

## 2. Build data

**Synthetic data (written by AI models, generated by us on Sat 3 Oct 2026 unless stated; labels from case cards, never from the text)**

| Dataset | Written by | Size | Use | File |
|---|---|---|---|---|
| X train | GPT, `gpt-5.5` | 1,200 messages (1,195 after dedupe): 660 danger / 420 no-danger / 120 shared path | Training the encoder; mining the E2 keyword list; vocabulary trim | `data/x_train.jsonl` |
| Y-dev | GPT, `gpt-5.5` | 120: 60 / 45 / 15 | Go-live gate, k for E2, the model-size deployment rule. Not a test set | `data/y_dev.jsonl` |
| Y-test | Claude, `claude-opus-5-5` | 150: 80 / 55 / 15 | Test set, sealed unopened (commit 839a4a5) | `tests/y_test.jsonl` |
| Set (a) | Claude Opus 5.5, Fri 2 Oct, before the event, from a fixed case grid | 25: 12 / 13 / 0 | Test set, sealed before the pre-registration (commit b492142) | `tests/caregiver_set_a.csv` |
| Set (b) | Claude, `claude-opus-5-5`, Swahili, same grid | 25: 12 / 13 / 0 | Test set, sealed unopened (commit f76c92d) | `tests/caregiver_set_b.csv` |

The training and development data were written by GPT; every test set was written by Claude, so the model never trains on the test writer's style. The prompts are in `prompts/` and the card sampler in `gen/cards.py`, both committed before any generation call. Released with this repository.

**Public data and models**

| Item | Source | Licence | Size | Use |
|---|---|---|---|---|
| AfroXLMR-base | Alabi, Adelani, Mosbach and Klakow (Saarland University), COLING 2022. https://huggingface.co/Davlan/afro-xlmr-base ; https://aclanthology.org/2022.coling-1.382/ | MIT | 278.0 M parameters in our fine-tuned checkpoint (incl. 6,152 in our 8 heads); 17 African languages incl. Swahili; no Kikuyu; Luo not seen in training (M1) | The encoder |
| MASSIVE 1.1, sw-KE and en-US | Amazon. https://huggingface.co/datasets/AmazonScience/massive | CC BY 4.0 | sw-KE splits 11,514 / 2,033 / 2,974 (M4) | Train split: generic vocabulary for the model-size trim. Validation: tokenization drift check. Test split: exploratory false-alarm row only (1,000 sw-KE utterances, fixed seed). Never used for training or tuning |
| Kenya healthsites (OpenStreetMap) | healthsites.io / Open Healthsite Consulting on HDX. https://data.humdata.org/dataset/kenya-healthsites ; https://healthsites.io/ | ODbL, © OpenStreetMap contributors (M6) | 2,640 rows in the export we downloaded on 3 Oct 2026 (our count) | 5 real facility names in Busia County for the demo registry (`config/registry.yaml`, with OSM node ids); every phone number, CHU, CHP, CHA and village is synthetic |
| WHO/UNICEF, *Caring for the sick child in the community* (2011): CHW manual (S1) and chart booklet (S2) | https://www.who.int/publications/i/item/9789241548045 | © WHO 2011, all rights reserved (manual copyright page) | | Rule logic only (danger signs, thresholds, follow-up days, with page citations in `config/protocol.yaml`); no text reproduced |

Alternative facility source, not used in the demo: Maina et al. 2019, 98,745 public facilities in 50 countries, 6,146 in Kenya (102 without coordinates); data file CC0 (figshare 10.6084/m9.figshare.7725374.v1); article CC BY 4.0 (M5). https://pmc.ncbi.nlm.nih.gov/articles/PMC6658526

**Where a record would land.** In deployment the referral and arrival record would go to Kenya's national health information system (KHIS, the Ministry of Health's DHIS2 instance, https://hiskenya.org) and sit alongside eCHIS. No integration was built this weekend.

## 3. Device (for the on-device card)

| # | Fact | Source |
|---|---|---|
| M7 | Raspberry Pi 5: Broadcom BCM2712, 4x Arm Cortex-A76 at 2.4 GHz; our demo unit is the 8 GB model | https://www.raspberrypi.com/products/raspberry-pi-5/ |
| M8 | Entry-level phones sold in Kenya: Galaxy A05 and Tecno Spark 20 (MediaTek Helio G85: 2x Cortex-A75 + 6x Cortex-A55); itel A70 (8x Cortex-A55), from KES 11,999 | GSMArena: https://www.gsmarena.com/samsung_galaxy_a05-12583.php ; https://www.gsmarena.com/tecno_spark_20-12722.php ; https://www.gsmarena.com/itel_a70-12704.php ; retailer: https://phonegradekenya.odoo.com/shop/itel-a70-10208 |
| C5 | Phones issued to CHPs are reported to be the Safaricom Neon Ultra / Neon Smarta: 2 GB RAM, 32 GB storage, Android Go edition, about KES 8,000 to 9,000; the chipset is not published | Reported by WeAreTech Africa; specs from Kenya Times, Money254, TechTrendsKE. https://wearetech.africa/fr/fils/actualites/tech/kenya-le-ministere-de-la-sante-a-acquis-des-smartphones-assembles-localement-pour-ses-equipes-de-terrain ; https://www.techtrendske.co.ke/2023/11/14/kenya-assembled-safaricom-neon-ultra-first-impressions-review/ ; https://money254.co.ke/post/all-about-the-kenyan-made-smartphone-costing-ksh7-499-news |

## 4. What our data does not cover

- **No real caregiver or health-worker messages.** Every message the model was trained, tuned or tested on was written by an AI model.
- **No Swahili danger messages written by a native speaker.** The pre-registered claim needs them, so it is "NOT TESTED". Set (b) is AI-written Swahili that no native speaker checked.
- **No Sheng or dialect depth** beyond what the synthetic generators produced.
- **No voice.** Text SMS only; no speech data.
- **No adult or maternal cases.** Children 2 to 59 months only; pregnancy, adult and newborn messages are routed to a person, not read.
- **MASSIVE has no health content.** It is human-written Swahili (translated virtual-assistant commands), so it can only show false alarms, never danger detection.
- **Labels come from a protocol grid, not clinicians.** Danger / no-danger labels follow the WHO/UNICEF danger-sign rules applied to case cards; no clinician reviewed them (Y labels are not hand-checked).
- **Outgoing SMS are English only.** Swahili replies are future work and need a native speaker's back-translation.
- **No real facility or health-worker phone numbers.** Facility names are real (OpenStreetMap); every number, CHU, CHP, CHA and village is synthetic.
- **The test sets are AI-written and may favour the keyword list.** The keyword list's Swahili words and every test set come from Claude-written text.
- **Kikuyu and Luo are not covered** by the encoder (M1).
