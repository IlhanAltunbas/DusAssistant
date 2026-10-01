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
