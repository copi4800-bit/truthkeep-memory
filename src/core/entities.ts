/**
 * Heuristic entity extraction — no NER model required.
 * Pattern-based extraction for names, files, URLs, tech terms.
 */

export interface ExtractedEntity {
  text: string;
  type: string;
  confidence: number;
}

/**
 * Extract entities from content using regex heuristics.
 */
export function extractEntities(content: string): ExtractedEntity[] {
  const entities: ExtractedEntity[] = [];
  const seen = new Set<string>();

  function add(text: string, type: string, confidence: number): void {
    const key = text.toLowerCase();
    if (seen.has(key) || text.length < 2) return;
    seen.add(key);
    entities.push({ text, type, confidence });
  }

  // @mentions
  const mentions = content.match(/@[\w]+/g);
  if (mentions) {
    for (const m of mentions) add(m.slice(1), "person", 0.8);
  }

  // URLs
  const urls = content.match(/https?:\/\/[^\s)]+/g);
  if (urls) {
    for (const url of urls) add(url, "url", 0.9);
  }

  // File paths (with extensions)
  const paths = content.match(/(?:[\w./\\-]+\/)?[\w.-]+\.\w{1,10}/g);
  if (paths) {
    for (const p of paths) {
      if (p.includes("/") || p.includes("\\")) add(p, "file", 0.7);
    }
  }

  // Capitalized phrases (2+ words, likely names)
  const capitalized = content.match(/\b[A-Z][\w]*(?:\s+[A-Z][\w]*)+\b/g);
  if (capitalized) {
    for (const phrase of capitalized) {
      if (phrase.length > 3 && phrase.length < 60) add(phrase, "named_entity", 0.6);
    }
  }

  // Quoted strings (potential terms/names)
  const quoted = content.match(/"([^"]{2,50})"/g);
  if (quoted) {
    for (const q of quoted) add(q.slice(1, -1), "term", 0.5);
  }

  // Technical terms (snake_case, camelCase, PascalCase)
  const techTerms = content.match(
    /\b[a-z]+(?:_[a-z]+){1,5}\b|\b[a-z]+(?:[A-Z][a-z]+){1,5}\b|\b[A-Z][a-z]+(?:[A-Z][a-z]+){1,5}\b/g,
  );
  if (techTerms) {
    for (const term of techTerms) {
      if (term.length > 4) add(term, "technical", 0.5);
    }
  }

  return entities;
}

/**
 * Extract entity mentions from text for matching against known entities.
 * Returns lowercase normalized names.
 */
export function extractEntityMentions(content: string): string[] {
  const entities = extractEntities(content);
  return entities.map((e) => e.text.toLowerCase());
}
