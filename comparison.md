# BibTeX Source Comparison

Comparison of BibTeX from **Google Scholar**, **Semantic Scholar**, **Official sources**, and **bibtools**.

## Summary

**Google Scholar and Semantic Scholar have errors across all fields:**

| | GS | S2 | bibtools |
|---|---|---|---|
| venue | 6/13 wrong (arXiv) | 7/13 wrong (arXiv) | 1/13 wrong* |
| year | 1/13 wrong | 5/13 wrong | ✓ |
| title | Lowercases acronyms | ✓ | ✓ |
| author | Truncates ("and others") | Abbreviates, missing/extra | ✓ |

\* FLOWER (CoRL 2025) — too recent for DBLP/S2 to have updated

**Official sources are always correct** but require manual effort.

**bibtools matches official sources** by fetching from CrossRef/DBLP/arXiv directly.

| Paper | Venue | GS | S2 | Official | bibtools |
|-------|-------|:--:|:--:|:--------:|:--------:|
| Deep Learning | Nature 2015 | ✓ | ✓ | ✓ | - |
| ResNet | CVPR 2016 | ✓ | ✗ year | ✓ | ✓ |
| Attention Is All You Need | NeurIPS 2017 | ✓ | ✓ | ✓ | ✓ |
| LoRA | ICLR 2022 | ✓ | ✗ arXiv | ✓ | ✓ |
| TD-MPC | ICML 2022 | ✗ arXiv | ✓ | ✓ | ✓ |
| DiT | ICCV 2023 | ✓ | ✗ year | ✓ | ✓ |
| StreamingLLM | ICLR 2024 | ✗ arXiv | ✗ arXiv | ✓ | ✓ |
| OpenVLA | CoRL 2024 | ✗ arXiv | ✗ arXiv | ✓ | ✓ (DBLP warning)† |
| HAMLET | arXiv 2025 | ✓ | ✓ | ✓ | ✓ |
| Hi Robot | ICML 2025 | ✗ arXiv | ✗ arXiv | ✓ | ✓ (DBLP warning)† |
| UP-VLA | ICML 2025 | ✗ arXiv | ✗ arXiv | ✓ | ✓ |
| Sliding Windows Are Not the End | ACL 2025 | ✓ | ✗ arXiv | ✓ | ✓ |
| FLOWER | CoRL 2025 | ✗ arXiv | ✗ arXiv | ✓ | ✗ arXiv |

† bibtools correctly fetches venue from DBLP, but cross-check with arXiv detects author name differences (e.g., "Michael Equi" vs "Michael Robert Equi"). This is validation working as intended.

---

## Detailed Comparison

### 1. Deep Learning (Nature 2015)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Deep learning | Deep Learning | Deep Learning | - |
| author | LeCun, Yann and ... | Yann LeCun and ... | LeCun, Yann and ... | - |
| venue | nature | - | Nature | - |
| year | 2015 | 2015 | 2015 | - |

bibtools: Not indexed in Semantic Scholar.

---

### 2. ResNet (CVPR 2016)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Deep residual learning... | Deep Residual Learning... | Deep Residual Learning... | Deep Residual Learning... |
| author | He, Kaiming and ... | Kaiming He and ... | He, Kaiming and ... | He, Kaiming and ... |
| venue | Proceedings of the IEEE... | 2016 IEEE CVPR | CVPR | 2016 IEEE CVPR |
| year | 2016 | **2015** ❌ | 2016 | 2016 |

**S2 shows wrong year (2015 instead of 2016).**

---

### 3. Attention Is All You Need (NeurIPS 2017)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Attention is all you need | Attention is All you Need | Attention is All you Need | Attention is All you Need |
| author | Vaswani, Ashish and ... | Ashish Vaswani and ... | Vaswani, Ashish and ... | Vaswani, Ashish and ... |
| venue | Advances in neural info... | Neural Information Processing Systems | Advances in Neural Info... | NIPS |
| year | 2017 | 2017 | 2017 | 2017 |

---

### 4. LoRA (ICLR 2022)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Lora: Low-rank adaptation... | LoRA: Low-Rank Adaptation... | LoRA: Low-Rank Adaptation... | LoRA: Low-Rank Adaptation... |
| author | Hu, Edward J and ... others | J. Edward Hu and ... | Edward J Hu and ... | Hu, Edward J. and ... |
| venue | ICLR (as @article) | **ArXiv** ❌ | ICLR | ICLR |
| year | 2022 | **2021** ❌ | 2022 | 2022 |

**S2 shows ArXiv 2021 instead of ICLR 2022.**

---

### 5. TD-MPC (ICML 2022)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Temporal difference learning... | Temporal Difference Learning... | Temporal Difference Learning... | Temporal Difference Learning... |
| author | Hansen, Nicklas and ... | Nicklas Hansen and ... | Hansen, Nicklas A and ... | Hansen, Nicklas and ... |
| venue | **arXiv preprint** ❌ | ICML | ICML (PMLR) | ICML |
| year | 2022 | 2022 | 2022 | 2022 |

**GS shows arXiv, but the paper was published at ICML 2022.**

---

### 6. DiT (ICCV 2023)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Scalable diffusion models... | Scalable Diffusion Models... | Scalable Diffusion Models... | Scalable Diffusion Models... |
| author | Peebles, William and ... | William S. Peebles and ... | Peebles, William and ... | Peebles, William and ... |
| venue | Proceedings of the IEEE/CVF... | 2023 IEEE/CVF ICCV | ICCV | 2023 IEEE/CVF ICCV |
| year | 2023 | **2022** ❌ | 2023 | 2023 |

**S2 shows wrong year (2022 instead of 2023).**

---

### 7. StreamingLLM (ICLR 2024)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Efficient streaming... | Efficient Streaming... | Efficient Streaming... | Efficient Streaming... |
| author | Xiao, Guangxuan and ... | Guangxuan Xiao and ... | Guangxuan Xiao and ... | Xiao, Guangxuan and ... |
| venue | **arXiv preprint** ❌ | **ArXiv** ❌ | ICLR | ICLR |
| year | **2023** ❌ | **2023** ❌ | 2024 | 2024 |

**Both GS and S2 show arXiv 2023, but the paper was published at ICLR 2024.**

---

### 8. OpenVLA (CoRL 2024)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Openvla: An open-source... | OpenVLA: An Open-Source... | OpenVLA: An Open-Source... | OpenVLA: An Open-Source... |
| author | Kim, Moo Jin and ... others | Moo Jin Kim and ... | Kim, Moo Jin and ... (17 total) | ⚠ arXiv cross-check failed |
| venue | **arXiv preprint** ❌ | **ArXiv** ❌ | CoRL (PMLR) | CoRL |
| year | 2024 | 2024 | 2024 | 2024 |

**Both GS and S2 show arXiv instead of CoRL 2024.**

⚠ **bibtools arXiv cross-check**: DBLP has "Ethan Paul Foster", "Pannag R. Sanketi" but arXiv has "Ethan Foster", "Pannag Sanketi". Also arXiv includes "Grace Lam" who is not in DBLP.

---

### 9. HAMLET (arXiv 2025)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | HAMLET: Switch your... | HAMLET: Switch your... | HAMLET: Switch your... | HAMLET: Switch your... |
| author | Koo, Myungkyu and ... | Myungkyu Koo and ... | Myungkyu Koo and ... | Koo, Myungkyu and ... |
| venue | arXiv preprint | ArXiv | arXiv | arXiv |
| year | 2025 | 2025 | 2025 | 2025 |

All sources agree (paper is arXiv-only).

---

### 10. Hi Robot (ICML 2025)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Hi robot: Open-ended... | Hi Robot: Open-Ended... | Hi Robot: Open-Ended... | Hi Robot: Open-Ended... |
| author | Shi, Lucy Xiaoyang and ... others | Lucy Xiaoyang Shi and ... | Lucy Xiaoyang Shi and ... | ⚠ arXiv cross-check failed |
| venue | **arXiv preprint** ❌ | **ArXiv** ❌ | ICML | ICML |
| year | 2025 | 2025 | 2025 | 2025 |

**Both GS and S2 show arXiv, but the paper was accepted at ICML 2025.**

⚠ **bibtools arXiv cross-check**: DBLP has "Michael Robert Equi" but arXiv has "Michael Equi". This discrepancy is caught by arxiv cross-check.

---

### 11. UP-VLA (ICML 2025)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Up-vla: A unified understanding... | UP-VLA: A Unified Understanding... | UP-VLA: A Unified Understanding... | UP-VLA: A Unified Understanding... |
| author | Zhang, Jianke and ... | Jianke Zhang and ... | Zhang, Jianke and ... | Zhang, Jianke and ... |
| venue | **arXiv preprint** ❌ | **ArXiv** ❌ | ICML | ICML |
| year | 2025 | 2025 | 2025 | 2025 |

**Both GS and S2 show arXiv, but the paper was accepted at ICML 2025.**

---

### 12. Sliding Windows (ACL 2025)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Sliding windows are not... | Sliding Windows Are Not... | Sliding Windows Are Not... | Sliding Windows Are Not... |
| author | Liu, Wenhan and ... | Wenhan Liu and ... | Liu, Wenhan and ... | Liu, Wenhan and ... |
| venue | Proceedings of the 63rd ACL... | **ArXiv** ❌ | Proceedings of the 63rd ACL... | Proceedings of the 63rd ACL... |
| year | 2025 | **2024** ❌ | 2025 | 2025 |

**S2 shows ArXiv 2024 instead of ACL 2025.**

---

### 13. FLOWER (CoRL 2025)

| | GS | S2 | Official | bibtools |
|-|----|----|---------:|----------|
| title | Flower: Democratizing... | FLOWER: Democratizing... | FLOWER: Democratizing... | FLOWER: Democratizing... |
| author | Reuss, Moritz and ... | Moritz Reuss and ... | Reuss, Moritz and ... | Reuss, Moritz and ... |
| venue | **arXiv preprint** ❌ | **ArXiv** ❌ | CoRL | **arXiv** ❌ |
| year | 2025 | 2025 | 2025 | 2025 |

**GS, S2, and bibtools all show arXiv, but the paper was accepted at CoRL 2025.**

❌ **bibtools**: S2 has not yet updated to show CoRL 2025 venue, so bibtools also fails.

---

## Common Errors

### Google Scholar

| Field | Issue | Examples |
|-------|-------|----------|
| venue | Shows "arXiv preprint" for conference papers | TD-MPC, StreamingLLM, OpenVLA, Hi Robot, UP-VLA, FLOWER |
| year | arXiv submission year instead of publication year | StreamingLLM (2023→2024) |
| title | Lowercases everything, including acronyms | "Lora", "Openvla", "Up-vla", "Flower" |
| author | Truncates with "and others" | OpenVLA, Hi Robot |
| type | Uses `@article` for conference papers | LoRA |
| metadata | Fabricated volume/number/pages | LoRA (volume=1, number=2, pages=3) |

### Semantic Scholar

| Field | Issue | Examples |
|-------|-------|----------|
| venue | Shows "ArXiv" for conference papers | LoRA, StreamingLLM, OpenVLA, Hi Robot, UP-VLA, Sliding Windows, FLOWER |
| year | arXiv submission year instead of publication year | ResNet (2015→2016), DiT (2022→2023), LoRA (2021→2022), Sliding Windows (2024→2025) |
| author | Abbreviates first names | "X. Zhang" (Xiangyu Zhang) |
| author | Adds/omits middle initials inconsistently | "Geoffrey E. Hinton", "William S. Peebles" |
| author | Missing authors | LoRA missing "Lu Wang" |
| author | Extra authors not in official | OpenVLA includes "Grace Lam" |
