# NLP пайплайн

1. DOCX разбивается на абзацы (`DocxIngestService`).
2. Natasha извлекает даты и ФИО (`ExtractService`).
3. Sentence-Transformers сопоставляет подразделения по справочнику (`SubdivisionSemanticService`).
4. `MatchService` применяет правило 2 из 3 (время, подразделение, нарушители).
5. `CompareService` формирует статусы и проценты, результат сохраняется в Redis.
