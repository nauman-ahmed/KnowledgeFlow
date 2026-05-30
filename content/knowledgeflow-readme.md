# KnowledgeFlow Sample Library

This folder holds **curated source documents** for the knowledge assistant. Topics can vary; everything lives in one flat library.

## Adding documents

1. Drop PDF, DOCX, TXT, or Markdown files here.
2. Run ingest from `backend/` (available in M2):

   ```bash
   python -m app.ingest
   ```

3. Ask questions in chat — RAG searches the full corpus (no section routing).

## Sample files (M0)

| File | Topic |
|------|--------|
| intro-to-investing.md | Finance basics |
| compound-interest.txt | Finance concept |
| music-theory-basics.txt | Music |
| study-habits.md | Education |
| knowledgeflow-readme.md | Meta / how the library works |
