# Phase 9: Offline Crop and Disease Vision (+F8)

- **Date:** 2026-11-18
- **Runs of record** (logged in `ml/experiments/`; full results in `ml/reports/data/`):

| Run | What | Run id | Output |
|---|---|---|---|
| Dataset | 70,002 images, leakage groups and splits | `958fd1f67731` | `vision_dataset_958fd1f67731.json` |
| Training | 2 experiments x 3 seeds, 8 epochs, test scored once | `560b033f785d` | `vision_train_560b033f785d.json` |
| Zero-shot baseline | BioCLIP, no training on our labels | `75a953a61436` | `vision_zero_shot_75a953a61436.json` |
| Field recalibration | Confidence refitted on field validation rows | `6e5a127ea6ea` | `vision_recalibrate_6e5a127ea6ea.json` |
| Served export | All-data seed 2, field-calibrated, 4 auto-accept crops | `e301c3c33a55` | artifact `ml/artifacts/vision/vision-560b033f785d-202611180856/` (git-ignored) |

Earlier `vision_dataset_*` and `vision_train_262e500ef8f4` files are smoke or superseded runs and are not evidence.

**Integrity notes.**
- **Validation only for choices:** the served seed, temperatures, confirmation threshold and auto-accept crop list were all chosen on validation rows.
- **Test scored once per configuration:** the training and recalibration scripts refuse a repeat.
- **Recalibration is a second look at the test set.** It changes only confidence values, not predictions, and is reported separately. The problem it fixes was found by reading the first test result, so its test figures are less independent than the training run's.
- **No real farmer photos.** PlantDoc (web photos) and the India rice set are **field proxies**.

## 1. Data and leakage control

| Source | Setting | Train | Val | Test |
|---|---|---|---|---|
| PlantVillage | Lab | 44,706 | 5,298 | 5,421 |
| PlantDoc (leaf crops from boxes) | Field proxy | 7,016 | 1,222 | 407 |
| India rice (Odisha) | Field proxy | 4,790 | 575 | 567 |

There are 16 crop labels and 43 crop-condition classes. Seven labels are catalog crops: citrus, grapes, maize, paddy, potato, soybean and tomato.

- **Augmented rice set:** its 5,932 images reduce to **242 independent photo groups**. Copies are flipped or rotated, and some identical photos carry different file numbers, so file names alone are not enough. Groups combine class and file number with pixel correlation >= 0.95 under flips and 90-degree rotations.
- **Other sources:** near-duplicates (dHash within 6 bits) are grouped across sources, and all crops of one PlantDoc photo stay together. Test images matching training groups were dropped: PlantDoc 38, PlantVillage 22.
- **Rice test is small in independent terms:** bacterial blight 246 images from 10 groups, blast 216 from 12, brown spot 32 from 2, tungro 73 from 14.

## 2. Results

Means over 3 seeds, with the range in brackets. "Disease" is condition accuracy when the true crop is known, which is what happens after the farmer confirms the crop.

| Test set | n | All-data crop accuracy | Lab-only crop accuracy | All-data disease accuracy | All-data disease macro-F1 |
|---|---|---|---|---|---|
| Lab (PlantVillage) | 5,421 | 99.94% (99.94-99.94) | 99.94% (99.93-99.96) | 99.56% (99.50-99.59) | 0.993 |
| **PlantDoc** | 407 | **86.00% (84.52-86.98)** | **40.05% (33.91-45.21)** | 77.15% (76.17-78.62) | 0.768 |
| India rice | 567 | 98.88% (98.06-100) | 0% (no rice in training) | 81.07% (78.48-82.54) | 0.793 |
| All field | 974 | 93.50% (92.71-94.35) | 16.74% (14.17-18.89) | 79.43% (77.72-80.70) | 0.771 |

- **Headline crop figure: 86.0% on PlantDoc.** The combined field figure is lifted by rice, where the task is close to recognising one visually distinct set.
- **Fair lab-versus-field comparison: PlantDoc, 40.05% versus 86.00%.** Both models trained on those crops. The lab-only rice score of 0% only reflects that rice was absent.
- **Lab accuracy does not predict field accuracy:** the lab-only model scores 99.94% on lab photos.

### Zero-shot comparison

| Test set | Measure | BioCLIP | All-data model (mean of 3 seeds) |
|---|---|---|---|
| Field (974) | Crop accuracy | 64.68% | 93.50% |
| Field (974) | Disease accuracy, crop known | 49.18% | 79.43% |
| Field (974) | Disease macro-F1, crop known | 0.428 | 0.771 |
| Lab (5,292) | Crop accuracy | 38.85% | 99.94% (on 5,421) |
| Lab (5,292) | Disease accuracy, crop known | 58.75% | 99.56% (on 5,421) |

BioCLIP chose among 15 crops because background photos have no species name; the trained model chooses among 16. BioCLIP used one fixed prompt template, with no prompt tuning.

## 3. Calibration and crop confirmation

The training run fitted temperatures on validation data that is mostly lab photos, and disease confidence was poorly calibrated on field photos. Recalibration refits on field validation rows only (crop temperature; condition temperature with logits limited to the true crop) and picks the lowest threshold at which auto-accepted PlantDoc validation crops reach 95% accuracy. The thresholds were 0.92, 0.91 and 0.93 across seeds.

Expected calibration error on test (mean of 3 seeds; lower is better):

| Test set | Crop, before | Crop, after | Disease, before | Disease, after |
|---|---|---|---|---|
| All field | 0.032 | 0.043 | **0.134** | **0.059** |
| PlantDoc | 0.083 | 0.048 | 0.131 | 0.052 |
| India rice | 0.021 | 0.060 | 0.137 | 0.087 |

Pooling helped PlantDoc crop confidence and disease confidence everywhere, but made rice crop confidence worse. A single temperature cannot suit both sources.

Crop auto-acceptance on test, counting only catalog crops as the app does (all seven at this stage; mean of 3 seeds):

| Test set | Setting | Accepted without asking | Accuracy of accepted | Wrong and accepted, share of all photos |
|---|---|---|---|---|
| PlantDoc | Before (threshold 0.6) | 57.7% | 92.5% | 4.3% |
| PlantDoc | **After (0.91-0.93)** | **41.0%** | **97.8%** | **0.9%** |
| All field | Before | 81.9% | 97.1% | 2.4% |
| All field | **After** | **71.1%** | **99.3%** | **0.5%** |

The cost is more questions: on PlantDoc the farmer is asked to confirm about 59% of photos.

## 4. Served model

All-data seed 2 had the best field validation score (0.7722). It is exported to ONNX (16.9 MB). ONNX and PyTorch outputs differ by at most 7.2e-06. It uses crop temperature 0.869, condition temperature 1.462 and confirmation threshold 0.93.

Auto-accept crops were chosen with a rule applied to field validation rows: at least 30 photos, at least 20 auto-accepted, and at least 95% accuracy among them.

| Crop | Field val photos | Crop recall | Auto-accepted | Accuracy of accepted | Disease accuracy, crop known | Auto-accept? |
|---|---|---|---|---|---|---|
| Paddy | 575 | 98.3% | 513 | 100% | 89.2% | Yes |
| Tomato | 438 | 88.8% | 289 | 97.2% | 61.9% | Yes |
| Maize | 68 | 95.6% | 56 | 96.4% | 79.4% | Yes |
| Grapes | 33 | 84.8% | 21 | 100% | 100% | Yes (small sample) |
| Potato | 83 | 75.9% | 43 | 88.4% | 74.7% | No |
| Soybean | 13 | 92.3% | 13 | 69.2% | 100% (1 class) | No |
| Citrus | 0 | n/a | 0 | n/a | n/a | No |

The catalog's `vision_supported` flag is true for those four crops only. Other crops always go through farmer confirmation. **This four-crop configuration has not been scored on test**, and its per-crop figures share the validation rows used for the calibration, so they are optimistic.

Through the backend provider on 300 field validation photos, inference took a median of about 0.3 s per photo on CPU while other jobs were running. That check used the first export, before recalibration.

## 5. Product integration

- **Photo turn:** `POST /conversation/photo-turns` runs quality checks, the local model, and the normal dialogue. An unsure or unsupported crop produces crop chips; a blurry photo or no plant asks for a retake. The answer carries vision, yield and active-bulletin cards in the farmer's language. Findings are always worded as possibilities.
- **F8 surveillance:** a report stores district, crop, condition, confidence, model version and a keyed reporter pseudonym, with no image, GPS or user id. Healthy findings are not stored. At least 3 distinct farmers in a week and at least 2x the previous 4-week mean creates an officer-review draft. No farmer is alerted unless an officer publishes it.
- **Enabling it:** `VISION_PROVIDER` still defaults to `mock-v1`. Set `VISION_PROVIDER=onnx-crop-classifier` and `ML_ARTIFACTS_DIR`, with the backend `local-ml` dependencies installed. Mock findings are never shown to farmers or counted as reports.

## 6. Verification

| Suite | Result |
|---|---|
| Backend | 322 passed, 11 skipped (the database tests, run separately) |
| Backend database integration, migrated to 0017 | 11 passed, including photo turn to outbreak draft |
| ML | 40 passed |
| Frontend | 33 test files passed; TypeScript check passed |

## 7. Limitations

- **No field validation with farmers.** Results come from public proxies, and PlantDoc photos come from the web.
- **Crop coverage:** no cotton, chilli or wheat data, and no citrus field validation data.
- **Paddy:** no healthy paddy class, one regional source, few independent test groups. Its diseases are identified from four classes only.
- **Tomato disease accuracy is weak** on field validation (61.9%), and the crop has the most condition classes.
- **Calibration differs by source**, so confidence values remain approximate on unseen sources.
- **Outbreak detection is untested on real outbreaks.** The thresholds are design choices, and low-confidence findings currently count towards reports.
- **Leakage effect not yet measured:** no model was trained on a naive random split, so the size of the accuracy inflation it would cause is unknown.
- **PlantVillage grouping is conservative:** its largest chained group has 18,875 images.
- **Licence:** weights are distributed under CC BY-SA 3.0 with attribution, by the project owner's decision.
- **Pending human review:** Hindi and Telugu wording of the new messages.
- **Satellite NDVI** was processed separately (run `44b6f843e847`: 299 months, 730 districts) and is not part of this phase's results.
- **Indian field photos:** see section 8. No model is trained on them yet.

## 8. Independent test on Indian field photos (added 2026-11-19)

**Data.** `scripts/download_india_vision.py` sampled five Mendeley Data sets within the 5 GB limit (4.26 GB transferred): potato (Uttar Pradesh), chilli (Krishna), tomato (BSKKV), soybean (Maharashtra) and wheat leaf rust (IARI). `scripts/check_india_vision.py` then removed repeats:

- **Exact copies:** 12 rows. Five chilli files appear under both bacterial spot and Cercospora leaf spot, and are dropped.
- **Near copies:** a 64-bit hash grouped 2,020 extra photos, but on inspection it was matching layouts (a single wheat leaf on black, wide black borders on potato photos). A 256-bit hash of the photo with dark borders trimmed finds 295 real repeats (bursts of the same leaf), and one photo per group is kept.
- **Overlap with training data:** 333 photos matched a training image on the 64-bit hash; none matched when rechecked against the cached training photo.
- **Kept:** 4,281 photos.

Possible shortcuts for later training: chilli photos are all 1000x1000; most potato early blight photos are 8160x3672 with black borders while most healthy ones are 3468x4624; wheat photos are single leaves on a black background, not field scenes.

**Result** (run `07389f462bb7`, served artifact, backend preprocessing, threshold 0.93; 95% intervals in `reports/data/vision_india_07389f462bb7.json`):

| Photos | n | Crop recognised | Auto-accepted as a supported crop | Wrong and auto-accepted |
|---|---|---|---|---|
| Tomato | 105 | 98.1% | 70.5% | 0 |
| Potato | 1,310 | 52.2% | 3.6% (as tomato) | 47 |
| Soybean | 420 | 23.3% | 2.9% (as tomato) | 12 |
| Chilli (not a model crop) | 1,627 | n/a | 9.5% (as tomato) | 155 |
| Wheat (not a model crop) | 819 | n/a | **50.2% (as maize)** | 411 |

Disease with the crop confirmed by the farmer:

| Photos | n | Correct | Main error |
|---|---|---|---|
| Potato early blight | 449 | 95.8% | |
| Potato late blight | 447 | 28.6% | 318 called early blight |
| Potato healthy | 414 | 31.4% | 191 called early blight |
| Tomato Alternaria (early blight) | 20 | 5% | 9 called late blight |

**Reading.**
- The confirmation threshold was tuned on crops the model knows. It does not protect against crops it has never seen: a wheat leaf looks like maize with high confidence. Raising the threshold does not fix this (at 0.97, 75 wrong auto-accepts remain and only 27% of tomato is still accepted; at 0.99 nothing is accepted).
- Potato disease reading leans heavily towards early blight on these photos, and tomato early blight is rarely recognised. The validation figures in section 4 were optimistic for Indian field conditions.
- **Serving change (project owner's decision):** auto-accept is now off by default
  (`VISION_AUTO_ACCEPT_CROP=false`). The farmer confirms the crop on every photo; the model's top
  crops are still offered first as chips. It should be switched back on only for a model that
  passes this test.
- Next: retrain with these photos (chilli and wheat as new crops, more potato and soybean field photos), split by near-copy group, with border trimming to remove the size and border shortcut.

## 9. Retraining with the Indian field photos (added 2026-11-21)

**Training** (run `a87c979112a1`, experiment `E3_india`; Colab Tesla T4, 3.6 hours, from a code bundle checked identical to commit `9b0fa2c`). The Phase 9 data plus 4,553 Indian photos (`scripts/prepare_india_vision.py`, run `73ce1378a499`): chilli and wheat are new crops; potato, soybean and tomato get field photos. Whole near-copy groups were split 70/15/15 by label. Before training, Colab rebuilt the Phase 9 split, and it matched the laptop's exactly (0 differing rows). There were three seeds, and each checkpoint was chosen on field validation.

**Test photos, mean of 3 seeds** (Phase 9 run `560b033f785d` vs `a87c979112a1`, the same test rows; temperatures from the training run):

| Test photos | Phase 9 | With Indian photos |
|---|---|---|
| All field photos (1,667): crop correct | 93.5% | 95.7% |
| All field photos: disease with crop confirmed (macro F1) | 0.771 | 0.806 |
| All field photos: crop calibration error (ECE) | 0.032 | 0.014 |
| PlantDoc (407): crop correct / disease F1 | 86.0% / 0.768 | 86.7% / 0.759 |
| India rice (567): crop correct / disease F1 | 98.9% / 0.793 | 97.6% / 0.823 |
| PlantVillage lab (5,421): crop correct | 99.9% | 99.9% |
| Indian field photos (693): crop correct | n/a | 99.5% |

**Calibration** (run `7cc27e2425d7`, the Phase 9 rule set before seeing any test result: temperatures fitted on field validation; threshold = the lowest at which auto-accepted crops reach 95% on PlantDoc validation). The thresholds were 0.94 for seed 0 and 0.95 for seed 1. For seed 2, no threshold reached 95%, so it never auto-accepts. On the field test photos, the refitted temperatures had a *higher* crop calibration error than the training ones (seed 2: 0.008 to 0.032), while PlantDoc improved (0.064 to 0.044). The rule was kept as decided, without choosing between them on test results.

**Exported model:** `vision-a87c979112a1-202611211255`. This is seed 2, the best validation score (0.835 vs 0.834 and 0.827), with the calibration above. ONNX parity is 5.5e-6. It has no confirmation threshold, so the farmer always confirms the crop. Its licence adds the five Mendeley Data sets (each CC BY 4.0) to the Phase 9 licence.

**Same 693 Indian test photos, served model vs retrained** (runs `ef7dfa341360` and `ac0689811e70`; backend preprocessing; the served model's numbers reproduce run `51c828f4f74a` exactly):

| Photos | n | Crop correct: served | Crop correct: retrained |
|---|---|---|---|
| Chilli | 281 | not a model crop (9.3% auto-accepted, mostly as tomato) | 100% |
| Wheat | 129 | not a model crop (48.1% auto-accepted as maize) | 100% |
| Potato | 204 | 52.5% | 99.0% |
| Soybean | 66 | 19.7% | 98.5% |
| Tomato | 13 | 92.3% | 100% |

Disease with the crop confirmed (balanced accuracy over the labels the model has a class for):

| Crop | Served | Retrained | Notes |
|---|---|---|---|
| Potato (3 labels, 68 each) | 53.4% | 96.1% | Late blight is 91% (was 32%). Healthy is 99% (was 31%). |
| Chilli (6 labels, 23-69 each) | n/a | 100% | Every chilli label is 100%. |
| Wheat (2 labels) | n/a | 95.5% | "Diseased" is 91%. The 74 "control" photos are read as healthy, and that mapping still needs the dataset authors' confirmation. |
| Soybean (6 labels, 11 each) | healthy only | 57.6% | The five diseases are each 45-64%, with wide intervals. |
| Tomato (Alternaria 3, leaf miner 10) | 0 of 3 | 1 of 3; leaf miner 8 of 10 | Too few photos to judge. |

**Shortcut check** (from the predictions of run `ac0689811e70`). Within each potato label, accuracy on photos whose size is not the usual one for that label stays high: early blight 93% (n = 14), healthy 100% (n = 38), late blight 86% (n = 37). The test photos mix sizes across labels; for example, 30 of the 68 healthy photos have the size that is usual for early blight. Photo size is therefore not what drives the potato result.

The same check is impossible for chilli and wheat. Each comes from one data set with a single photo size (1000x1000 and 3024x2016). The test photos share the farms, cameras and sessions of the training photos. Near-copies were kept within one split, but photos of the same plants on the same day were not. The border trimming planned in section 8 was not applied.

**Reading.**
- The retrained model is better than the served one on every comparable test: field crop accuracy, field disease, calibration error, and above all the Indian photos. It is not worse on the lab or PlantDoc photos. India rice crop accuracy dips by about one point, while rice disease improves.
- The Indian-photo scores (99-100%) are **within-data-set** results and are optimistic. The perfect chilli scores especially point to same-session photos rather than proof that the model generalises to new farms. These figures do not show how the model does on photos from other places, phones or seasons.
- Soybean disease (about 58%) and tomato early blight remain weak.
- Auto-accept stays off (`VISION_AUTO_ACCEPT_CROP=false`), and this model has no threshold anyway. Every photo still asks the farmer to confirm the crop, now with chilli and wheat among the offered crops.
- **Before claiming field accuracy,** test on Indian photos from a different source: other states, and photos taken by farmers or extension staff. Add border trimming at preparation time.
