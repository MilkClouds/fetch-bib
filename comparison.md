# BibTeX Source Comparison

Comparison of BibTeX from **Google Scholar**, **Official sources**, and **bibtools**.

## Summary

**Google Scholar often has wrong venue/year for arXiv papers that were later published at conferences.** Out of 10 test papers, GS had critical errors in 3 cases (StreamingLLM, Hi Robot, FLOWER) where it showed "arXiv" instead of the actual conference. GS also uses lowercase titles and sometimes fabricates metadata (LoRA's fake volume/number/pages).

**bibtools relies on Semantic Scholar**, which may not yet have updated venue info for very recent publications. FLOWER (CoRL 2025) is an example where Semantic Scholar still shows arXiv.

**Official sources are always correct** but require manual effort to find the right publisher page.

**bibtools matches official sources** for venue and year in all cases where the paper is indexed in Semantic Scholar. It automates what would otherwise require visiting multiple publisher sites.

| Paper | Venue | GS | Official | bibtools |
|-------|-------|:--:|:--------:|:--------:|
| Deep Learning | Nature 2015 | ✓ | ✓ | - |
| Deep Residual Learning for Image Recognition | CVPR 2016 | ✓ | ✓ | ✓ |
| Attention Is All You Need | NeurIPS 2017 | ✓ | ✓ | ✓ |
| LoRA: Low-Rank Adaptation of Large Language Models | ICLR 2022 | ✓ | ✓ | ✓ |
| TD-MPC | ICML 2022 | ✗ arXiv | ✓ | ✓ |
| Scalable Diffusion Models with Transformers | ICCV 2023 | ✓ | ✓ | ✓ |
| Efficient Streaming Language Models with Attention Sinks | ICLR 2024 | ✗ arXiv 2023 | ✓ | ✓ |
| OpenVLA | CoRL 2024 | ✗ arXiv 2024 | ✓ | ✓ (catches [DBLP error](#7-openvla-corl-2024-️)) |
| HAMLET | arXiv 2025 | ✓ | ✓ | ✓ |
| Hi Robot | ICML 2025 | ✗ arXiv | ✓ | ✓ (catches [DBLP error](#10-hi-robot-icml-2025-️)) |
| UP-VLA | ICML 2025 | ✗ arXiv | ✓ | ✓ |
| Sliding Windows Are Not the End | ACL 2025 | ✓ | ✓ | ✓ |
| FLOWER | CoRL 2025 | ✗ arXiv | ✓ | ✗ arXiv |

---

## Detailed Comparison

### 1. Deep Learning (Nature 2015)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Deep learning | Deep Learning | - |
| author | LeCun, Yann and ... | LeCun, Yann and ... | - |
| venue | nature | Nature | - |
| year | 2015 | 2015 | - |

bibtools: Not indexed in Semantic Scholar.

---

### 2. ResNet (CVPR 2016)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Deep residual learning... | Deep Residual Learning... | Deep Residual Learning... |
| author | He, Kaiming and ... | He, Kaiming and ... | He, Kaiming and ... |
| venue | Proceedings of the IEEE conference... | CVPR | 2016 IEEE CVPR |
| year | 2016 | 2016 | 2016 |

---

### 3. Attention Is All You Need (NeurIPS 2017)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Attention is all you need | Attention is All you Need | Attention is All you Need |
| author | Vaswani, Ashish and ... | Vaswani, Ashish and ... | Vaswani, Ashish and ... |
| venue | Advances in neural information... | Advances in Neural Information... | NIPS |
| year | 2017 | 2017 | 2017 |

---

### 4. LoRA (ICLR 2022)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Lora: Low-rank adaptation... | LoRA: Low-Rank Adaptation... | LoRA: Low-Rank Adaptation... |
| author | Hu, Edward J and ... others | Edward J Hu and ... | Hu, Edward J. and ... |
| venue | ICLR (as @article) | International Conference on Learning Representations | ICLR |
| year | 2022 | 2022 | 2022 |

GS uses `@article` with fake volume=1, number=2, pages=3.

---

### 4b. TD-MPC (ICML 2022) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Temporal difference learning... | Temporal Difference Learning... | Temporal Difference Learning... |
| author | Hansen, Nicklas and ... | Hansen, Nicklas A and ... | Hansen, Nicklas and ... |
| venue | **arXiv preprint** ❌ | ICML (PMLR) | ICML |
| year | 2022 | 2022 | 2022 |

**GS shows arXiv, but the paper was published at ICML 2022.**

---

### 5. DiT (ICCV 2023)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Scalable diffusion models... | Scalable Diffusion Models... | Scalable Diffusion Models... |
| author | Peebles, William and ... | Peebles, William and ... | Peebles, William and ... |
| venue | Proceedings of the IEEE/CVF... | ICCV | 2023 IEEE/CVF ICCV |
| year | 2023 | 2023 | 2023 |

---

### 6. StreamingLLM (ICLR 2024) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Efficient streaming... | Efficient Streaming... | Efficient Streaming... |
| author | Xiao, Guangxuan and ... | Guangxuan Xiao and ... | Xiao, Guangxuan and ... |
| venue | **arXiv preprint** ❌ | ICLR | ICLR |
| year | **2023** ❌ | 2024 | 2024 |

**GS shows arXiv 2023, but the paper was published at ICLR 2024.**

---

### 7. OpenVLA (CoRL 2024) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Openvla: An open-source... | OpenVLA: An Open-Source... | OpenVLA: An Open-Source... |
| author | Kim, Moo Jin and ... others | Kim, Moo Jin and ... (17 total) | ⚠ arXiv cross-check failed |
| venue | **arXiv preprint** ❌ | CoRL (PMLR) | CoRL |
| year | 2024 | 2024 | 2024 |

**GS shows arXiv preprint instead of CoRL 2024.**

⚠ **bibtools arXiv cross-check**: DBLP has "Ethan Paul Foster", "Pannag R. Sanketi" but arXiv has "Ethan Foster", "Pannag Sanketi". Also arXiv includes "Grace Lam" who is not in DBLP.

---

### 9. HAMLET (arXiv 2025)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | HAMLET: Switch your... | HAMLET: Switch your... | HAMLET: Switch your... |
| author | Koo, Myungkyu and ... | Myungkyu Koo and ... | Koo, Myungkyu and ... |
| venue | arXiv preprint | arXiv | arXiv |
| year | 2025 | 2025 | 2025 |

All sources agree (paper is arXiv-only).

---

### 10. Hi Robot (ICML 2025) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Hi robot: Open-ended... | Hi Robot: Open-Ended... | Hi Robot: Open-Ended... |
| author | Shi, Lucy Xiaoyang and ... others | Lucy Xiaoyang Shi and ... | ⚠ arXiv cross-check failed |
| venue | **arXiv preprint** ❌ | ICML | ICML |
| year | 2025 | 2025 | 2025 |

**GS shows arXiv, but the paper was accepted at ICML 2025.**

⚠ **bibtools arXiv cross-check**: DBLP has "Michael Robert Equi" but arXiv has "Michael Equi". This discrepancy is caught by arxiv cross-check.

---

### 10b. UP-VLA (ICML 2025) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Up-vla: A unified understanding... | UP-VLA: A Unified Understanding... | UP-VLA: A Unified Understanding... |
| author | Zhang, Jianke and ... | Zhang, Jianke and ... | Zhang, Jianke and ... |
| venue | **arXiv preprint** ❌ | ICML | ICML |
| year | 2025 | 2025 | 2025 |

**GS shows arXiv, but the paper was accepted at ICML 2025.**

---

### 11. Sliding Windows (ACL 2025)

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Sliding windows are not... | Sliding Windows Are Not... | Sliding Windows Are Not... |
| author | Liu, Wenhan and ... | Liu, Wenhan and ... | Liu, Wenhan and ... |
| venue | Proceedings of the 63rd ACL... | Proceedings of the 63rd ACL... | Proceedings of the 63rd ACL... |
| year | 2025 | 2025 | 2025 |

---

### 12. FLOWER (CoRL 2025) ⚠️

| | Google Scholar | Official | bibtools |
|-|----------------|----------|----------|
| title | Flower: Democratizing... | FLOWER: Democratizing... | FLOWER: Democratizing... |
| author | Reuss, Moritz and ... | Reuss, Moritz and ... | Reuss, Moritz and ... |
| venue | **arXiv preprint** ❌ | CoRL | **arXiv** ❌ |
| year | 2025 | 2025 | 2025 |

**GS shows arXiv, but the paper was accepted at CoRL 2025.**

❌ **bibtools**: Semantic Scholar has not yet updated to show CoRL 2025 venue.

---

## Common Google Scholar Errors

1. **Wrong venue**: Shows "arXiv preprint" for conference papers (TD-MPC, StreamingLLM, OpenVLA, Hi Robot, UP-VLA, FLOWER)
2. **Wrong year**: Shows arXiv submission year instead of publication year
3. **Wrong type**: Uses `@article` for conference papers
4. **Fake metadata**: Invents volume/number/pages (LoRA)
5. **Lowercase titles**: Does not preserve title case
6. **Author truncation**: Uses "and others" instead of full list

