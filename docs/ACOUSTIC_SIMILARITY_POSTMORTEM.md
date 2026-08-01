# Technical Post-Mortem: Acoustic Similarity Vector Distortion & Resolution

**Document Path**: [`docs/ACOUSTIC_SIMILARITY_POSTMORTEM.md`](file:///home/adley/repos/university/AudioGraph-AI/docs/ACOUSTIC_SIMILARITY_POSTMORTEM.md)  
**Date**: August 2026  
**Status**: Resolved  

---

## 1. Problem Statement & Symptoms

During initial manual verification using the seed track **'Comedy' by Gen Hoshino** (genre tagged as `acoustic`), the system generated a recommendation stream containing wildly mismatched genres and energy levels:

* **Seed Track**: *'Comedy'* by Gen Hoshino (Mid-tempo Acoustic/J-Pop, 87.9 BPM)
* **Generated Queue (Before Fix)**:
  1. `Kamariya` - Aastha Gill *(Indian Pop)*
  2. `Blue Flame` - LE SSERAFIM *(K-Pop Dance, 112 BPM)*
  3. `This Is It` - Oh The Larceny *(Heavy Blues Rock)*
  4. `Bhool Bhulaiyaa` - Pritam *(Bollywood)*
  5. `PING PONG` - HyunA&DAWN *(K-Pop Hype Dance)*
  6. `This Place Hotel` - The Jacksons *(80s Funk/Disco)*
  7. `Hope` - The Chainsmokers *(EDM)*

Despite these tracks belonging to completely incongruous genres and tempos, the system reported false similarity scores of **0.90 to 1.00**.

---

## 2. Root Cause Analysis

A deep-dive investigation into the mathematical and feature scaling pipeline revealed four distinct root causes:

### Root Cause 1: Non-Acoustic Metadata Contamination
`popularity` and `duration_ms` were included in the audio feature similarity vector.
* **Impact**: Because both *'Comedy'* and *'Blue Flame'* had high popularity scores (~75), the vector similarity dot product received a massive **+0.17 artificial similarity boost** purely because both tracks were popular, distorting acoustic distance.

### Root Cause 2: Negative $\times$ Negative Vector Inflation (`StandardScaler`)
Continuous audio features were normalized using zero-mean `StandardScaler`.
* **Impact**: Features like `instrumentalness` and `acousticness` naturally bound between $[0, 1]$. In zero-mean space, two vocal pop tracks with $0.0$ instrumentalness both receive negative scaled values (e.g. $-0.20$).
* When computing dot products: `(-0.20) * (-0.20) = +0.04` **positive similarity**. Vocal tracks across unrelated genres (EDM, K-Pop, Heavy Metal, Bollywood) were artificially rewarded with positive similarity for both having zero instrumentalness.

### Root Cause 3: Magnitude Invariance of Cosine Similarity
The builder computed Cosine Similarity ($S = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$), which measures only the **angle / direction** between vectors while ignoring absolute magnitude.
* **Impact**: A high-energy electronic dance track and a low-energy acoustic track sharing similar feature proportions received a **1.00 Cosine Similarity** (0-degree angle), even though their absolute energy, loudness, and volume were drastically different.

### Root Cause 4: Unpenalized Speed & Energy Discrepancies
Feature weights for `tempo` and `energy` were insufficiently weighted, allowing 25+ BPM tempo jumps to go unpenalized.

---

## 3. Implemented Solutions & Architectural Refactoring

### Fix 1: Pure Acoustic Feature Isolation ([`src/graph/loader.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/loader.py))
`popularity` and `duration_ms` were removed from the similarity vector matrix $X_{\text{scaled}}$. They are preserved in raw track metadata dictionaries for UI display and filtering, but no longer distort acoustic distance.

### Fix 2: Non-Negative $[0, 1]$ Bounded Space (`MinMaxScaler`)
Replaced `StandardScaler` with `MinMaxScaler` in $[0, 1]$ bounded space.
* **Effect**: In $[0, 1]$ space, zero instrumentalness yields `0.0 * 0.0 = 0.0` (eliminating artificial similarity inflation).

### Fix 3: Gaussian RBF Weighted Euclidean Distance ([`src/graph/builder.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/builder.py))
Replaced Cosine Similarity with **Gaussian RBF Weighted Euclidean Distance**:

$$S(A, B) = \exp\left( - \gamma \cdot \sqrt{\sum_{f} w_f \cdot (x_{A, f} - x_{B, f})^2} \right)$$

* **Effect**: Measures absolute intensity and volume differences. A quiet ambient track and a loud electronic track now receive low Euclidean similarity ($S < 0.2$), eliminating false $1.00$ scores.

### Fix 4: Layer 1 Metadata Boost Multipliers ([`src/graph/recommender.py`](file:///home/adley/repos/university/AudioGraph-AI/src/graph/recommender.py))
Added `artist_boost` (+35%) and `genre_boost` (+20%) parameters to 1-hop sampling, allowing natural genre and artist affinity to guide recommendations alongside acoustic proximity.

---

## 4. Empirical Verification Results

Starting Seed: **'Comedy' by Gen Hoshino** (`track_genre`: `acoustic`, 87.9 BPM)

| # | Before Fix ([`report.txt`](file:///home/adley/repos/university/AudioGraph-AI/report.txt)) | After Fix (Gaussian RBF + $[0, 1]$ Scaling) |
| :- | :--- | :--- |
| **01** | `Kamariya` - Aastha Gill *(Indian Pop)* | `Pop Virus` - **Gen Hoshino** *(Acoustic/Pop)* |
| **02** | `Blue Flame` - LE SSERAFIM *(K-Pop Dance)* | `Look For The Good` - **Jason Mraz** *(Acoustic/Folk)* |
| **03** | `This Is It` - Oh The Larceny *(Blues Rock)* | `SUN` - **Gen Hoshino** *(Acoustic/Pop)* |
| **04** | `Bhool Bhulaiyaa` - Pritam *(Bollywood)* | `I Am So Mad at You` - **AJJ** *(Acoustic Folk)* |
| **05** | `PING PONG` - HyunA&DAWN *(K-Pop Hype)* | `別れの予感` - **Hanare Gumi** *(Acoustic Pop)* |
| **06** | `Lamborghini` - Meet Bros. *(Pop-Film)* | `Living in the Moment` - **Jason Mraz** *(Acoustic)* |
| **07** | `This Place Hotel` - The Jacksons *(80s Disco)* | `So Far so Good` - **Gabrielle Aplin** *(Acoustic)* |
| **08** | `Lovers In The Night` - Seori *(K-Pop)* | `I Wanna Be Your Ghost` - **Gen Hoshino** *(Acoustic)* |
| **09** | `Hope` - The Chainsmokers *(EDM)* | `Outside Villanova` - **Eric Hutchinson** *(Acoustic)* |
| **10** | `Baby Girl` - Guru Randhawa *(Hip-Hop)* | `The Woman I Love` - **Jason Mraz** *(Acoustic)* |

All 13 unit tests (`pytest`) pass cleanly.
