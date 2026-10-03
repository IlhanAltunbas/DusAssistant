# Evaluation set

`sorular.jsonl` holds 28 questions used to measure retrieval and answer quality before any change reaches production.

| Type (`tur`) | TR | EN | What it measures |
|---|---|---|---|
| `tek_dil` | 5 | 5 | Question and answer source in the same language |
| `capraz_dil` | 5 | 5 | The answer exists **only** in the other language's books; the known weak spot, since the question's language decides which books are retrieved |
| `cevapsiz` | 2 | 2 | Not in any source; the correct behaviour is to say so instead of answering |
| `takip` | 2 | 2 | Follow-up that depends on `gecmis` (chat history); exercises query rewriting |

Each line has the question, its language, the chat history if any, the PDF pages that contain the answer (`beklenen_kaynaklar`, 1-based PDF page numbers; one hit among them counts), and 1–3 key facts the answer must contain (`anahtar_bilgiler`).

## How it was built

1. The four source books were extracted to text page by page with the same PDF library the ingestion uses.
2. Two LLM agents drafted questions in parallel, one per source language, under written rules: phrase questions like a student rather than copying the book's wording; for cross-lingual questions, show by search that the fact is absent from the question-language books; for unanswerable questions, show it is absent from all four.
3. Every expected page had to come with a verbatim quote. A script checked each quote against the extracted text of that exact page and rejected the question otherwise; it also reported word overlap between question and quote to catch questions copied from the source.
4. A human reviewed the questions for relevance to the exam.

The quotes stay out of the repository with the books themselves (`eval/yerel/`, git-ignored), because the books are copyrighted.

Because the questions were drafted by an LLM, they may be easier or more uniform than real student questions; the scores are best read as a regression baseline, not as an absolute quality claim.

After the first retrieval run, two questions had the answer on pages the key did not list (the retriever had found them, at rank 1 in one case). Those pages were added to the key only after the same quote check; no question was changed to improve a score.

## Retrieval baseline (2026-10-01)

```bash
python -m eval.retrieval
```

Runs the 24 answerable questions through the production query path (follow-ups are rewritten by the same LLM step first) against the live Azure AI Search index, top 5 chunks.

| Type | Question language | hit@5 | MRR | Retrieved chunks TR / EN |
|---|---|---|---|---|
| Same language | EN | 5/5 | 0.90 | 0 / 25 |
| Same language | TR | 3/5 | 0.30 | 25 / 0 |
| Cross-lingual | EN (answer in TR books) | 3/5 | 0.22 | 7 / 18 |
| Cross-lingual | TR (answer in EN books) | 2/5 | 0.13 | 19 / 6 |
| Follow-up | EN + TR | 2–4 of 4 | 0.50–0.62 | |
| **Total** | | **15–17/24** | **0.41–0.43** | 61 / 59 |

* The question's language decides which books are retrieved: Turkish questions get Turkish chunks and English questions English chunks, so cross-lingual questions succeed mainly when the key term is the same in both languages (PRF, Periotest).
* Turkish same-language retrieval is clearly weaker than English (MRR 0.30 vs 0.90).
* Everything except follow-ups is deterministic across runs; follow-ups vary because the query rewrite is an LLM call, so they are reported as a range over three runs.

**Exhaustive vector search (later the same day).** Investigating a miss showed that Azure AI Search's default approximate search (HNSW) can skip the most similar chunk entirely: for the sentence defining Ante's law, exhaustive search ranks its chunk first (score 0.768) while approximate search does not return it in the top 5. With ~7,200 vectors exhaustive search is cheap, so the retriever now uses it. The retrieval numbers above did not change: none of the 24 eval questions was affected, and the real cross-lingual misses are ranking problems (the same chunk scores 0.52 against the English question and 0.36 against the Turkish one, below other chunks).

## Answer baseline (2026-10-01)

```bash
python -m eval.cevaplar            # 28 questions x 3 runs, judge budget capped at $2.50
```

Each question is answered three times through the production code path (answers vary between runs). What code can check, code checks: the answer language and whether the assistant gave its fixed "no information" sentence. Two judgements need meaning, so an LLM judge from a different model family (Claude Sonnet 5.5; answers come from Azure OpenAI gpt-5-mini) makes them, with structured output: which key facts the answer states, and which claims in the answer the retrieved excerpts do not support. The run stops calling the judge when its estimated spend reaches the budget. This run made 53 judge calls for $0.47.

| Type | Question language | Fully correct | Key facts covered* | Faithful* | Refused although answerable | Right language |
|---|---|---|---|---|---|---|
| Same language | EN | 60% | 70% | 73% | 0% | 100% |
| Same language | TR | 40% | 54% | 77% | 13% | 100% |
| Cross-lingual | EN (answer in TR books) | 40% | 83% | 78% | 40% | 100% |
| Cross-lingual | TR (answer in EN books) | 7% | 50% | 86% | 53% | 100% |
| Follow-up | EN | 67% | 100% | 75% | 33% | 100% |
| Follow-up | TR | 67% | 80% | 100% | 17% | 100% |
| **Total (72 answers)** | | **42%** | **69%** | **79%** | **26%** | **100%** |

\* Among answers that did not refuse.

Unanswerable questions: refused correctly in 12 of 12 answers.

What the numbers and a manual check of the judge's reasoning show:

* **Answer language and refusing out-of-scope questions work.** Both earlier fixes hold at 100%.
* **Cross-lingual retrieval is the main gap.** When the answer is only in English books, a Turkish question is fully answered 7% of the time; most of the rest are honest refusals, because the right chunks were never retrieved.
* **A page hit is not a chunk hit.** For the Ramfjord-teeth question the retriever returned the right page at rank 2, but the chunk it returned named the teeth without listing them, and the assistant correctly said the list was missing. Page-level hit@5 overstates retrieval quality.
* **Wrong context can produce a confident wrong answer.** When the low-dose doxycycline page was not retrieved, the assistant answered with the antibacterial doxycycline regimen from another page instead of refusing. This is the cost of the instruction to answer from partial information, which was added to cut false refusals.
* **The judge is strict.** Checked by hand on four cases it was right each time; where a key fact bundles two claims, it marks the whole fact missing if one part is absent, so scores err on the low side.

## Dependency upgrade check (2026-10-03)

LangChain was upgraded from 0.1 to 1.x (needed for LangGraph), together with the OpenAI SDK (1.109 → 2.54) and the Anthropic SDK (0.104 → 0.125). `langchain-community`, which is no longer maintained, was removed: PDF loading now calls `pypdf` directly the way the old loader did, and Qdrant goes through `langchain-qdrant`. The eval was used to show behaviour did not change:

* **Ingestion:** re-chunking the four PDFs with the new code gives 7,198 chunks, the same as the live index, and 50 of 50 randomly sampled chunks match the indexed ones exactly (text, book and page).
* **Retrieval:** identical to the baseline, question by question (16/24, MRR 0.42).
* **Answers:** one run per question, inside the range of the baseline runs: fully correct 50%, key facts 77%, faithful 72%, false refusal 25%, language 100%, unanswerable refused 4 of 4. One run is too few to claim a change in either direction; the full three-run eval is repeated before the next deploy.

## Chain vs agent (2026-10-03)

```bash
python -m eval.cevaplar --mod agent      # ASSISTANT_MODE=agent, see app/ajan.py
```

The agent mode lets the model decide when and in which language to search (LangGraph; first search forced, at most 3 rounds and 2 searches per round, then an answer without tools). Both modes were run the same day under the same concurrency (4 parallel questions); answer times include it.

| | Chain, 2026-10-01 (3 runs) | Chain, 2026-10-03 (1 run) | Agent, 2026-10-03 (3 runs) |
|---|---|---|---|
| Fully correct | 42% | 54% | **71%** |
| Key facts covered* | 69% | 80% | 84% |
| Faithful* | 79% | 72% | **64%** |
| Refused although answerable | 26% | 25% | **3%** |
| Cross-lingual TR → EN, fully correct | 7% | 20% | **60%** |
| Right language / unanswerable refused | 100% / 12 of 12 | 100% / 4 of 4 | 100% / 12 of 12 |
| Median answer time (slowest 10% from) | not measured | 3.0 s (5.3 s) | 6.1 s (10.0 s) |
| Searches per question | 1 | 1 | 1.58 |

\* Among answers that did not refuse.

What this shows:

* **The agent fixes the main gap.** Searching again in the other language takes Turkish questions whose answer is only in the English books from 7–20% to 60% fully correct, and answerable questions are almost never refused (3% instead of about 25%).
* **It answers more, and adds more.** Faithfulness drops from 72–79% to 64%. Of the 25 answers with unsupported claims, 16 have a single one; most are small additions to correct content (a direction of an effect the excerpt did not state, "black" triangles, an explicit tooth-by-tooth mapping), and a few are textbook knowledge not in the excerpts (calling healthy sulcus fluid a transudate). The judge sees every passage the agent retrieved across its searches, which is what the answer was written from.
* **It is about twice as slow**: one more model call per question on average.
* **Not switched yet.** For exam preparation an unsupported detail is a real cost, so the next step is a prompt change aimed at faithfulness, measured the same way, before choosing the production mode.

This run used the agent before a review added three safeguards (answering malformed tool calls, at most 2 searches per round, and a provider-neutral final answer); they change behaviour only in rare paths, and the decision run will use the final code.

### Faithfulness prompt and decision (2026-10-04)

The agent's system prompt was changed to name the kinds of unsupported additions found above (no direction of an effect, numbers, item-by-item mappings, causes or explanations the passages do not state) and to say that information about a different substance or procedure is not relevant. Two intermediate versions were rejected along the way, both caught by code checks before a full judged run:

* "Every statement must be written in the passages" made the model quote Turkish passages verbatim inside English answers (language dropped to 92%).
* Asking it to "say which part the sources do not cover" made it describe a different gel's study for an unanswerable curcumin question instead of refusing.

One judged run was lost: the eval crashed while printing a row for an unanswerable question that had been answered, before saving its results. The script now saves first; the printed rows were enough to recover the numbers quoted above.

Final prompt, three runs, final code:

| | Chain (2026-10-01, 3 runs) | Agent, first prompt (3 runs) | **Agent, final prompt (3 runs)** |
|---|---|---|---|
| Fully correct | 42% | 71% | **72%** |
| Key facts covered* | 69% | 84% | 86% |
| Faithful* | 79% | 64% | **77%** |
| Refused although answerable | 26% | 3% | **4%** |
| Right language / unanswerable refused | 100% / 12 of 12 | 100% / 12 of 12 | 100% / 12 of 12 |
| Median answer time (slowest 10% from) | 3.0 s (5.3 s)** | 6.1 s (10.0 s) | 5.3 s (8.3 s) |

\* Among answers that did not refuse. \** Chain timing from the 2026-10-03 single run.

Faithfulness is back in the chain's range (72–79%) while the agent keeps its gains: 30 points more fully correct answers and almost no false refusals. Three of the 16 unfaithful answers come from one Turkish follow-up question where the model mixes up furcation grades in every run. **Decision: the agent mode goes into the next release**, at the cost of about 2 seconds more per answer.
