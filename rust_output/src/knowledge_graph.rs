/// Core/knowledge_graph::py — LightRAG-style Knowledge Graph for ZEN_RAG.
/// 
/// Phase 3.1: Entity and relationship extraction + graph-based multi-hop retrieval.
/// 
/// Inspired by:
/// - LightRAG (ICLR '25): dual-level retrieval — local (entity) + global (community)
/// - HippoRAG: entity-centric KG with PPR traversal
/// - EcphoryRAG: 94% token reduction via entity-centric indexing
/// 
/// Architecture:
/// - Entity extraction via LLM (NER) or spaCy fallback
/// - Relationship triples: (entity_a, relation, entity_b)
/// - Storage: SQLite (zero-dependency, works offline)
/// - Retrieval: entity match → related entity expansion → chunk recall
/// 
/// Usage:
/// kg = KnowledgeGraph(db_path="rag_storage/knowledge_graph::db")
/// kg.ingest_chunks(chunks, llm=my_llm)
/// results = kg.query("What hospitals does Dr. Smith work at?")

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const _SCHEMA_SQL: &str = "\\nCREATE TABLE IF NOT EXISTS entities (\\n    id       TEXT PRIMARY KEY,\\n    name     TEXT NOT NULL,\\n    type     TEXT DEFAULT 'UNKNOWN',\\n    aliases  TEXT DEFAULT '[]',\\n    chunk_id TEXT\\n);\\n\\nCREATE TABLE IF NOT EXISTS relations (\\n    id         TEXT PRIMARY KEY,\\n    subject_id TEXT NOT NULL,\\n    predicate  TEXT NOT NULL,\\n    object_id  TEXT NOT NULL,\\n    weight     REAL DEFAULT 1.0,\\n    chunk_id   TEXT,\\n    FOREIGN KEY(subject_id) REFERENCES entities(id),\\n    FOREIGN KEY(object_id)  REFERENCES entities(id)\\n);\\n\\nCREATE TABLE IF NOT EXISTS chunk_entities (\\n    chunk_id  TEXT NOT NULL,\\n    entity_id TEXT NOT NULL,\\n    PRIMARY KEY (chunk_id, entity_id)\\n);\\n\\nCREATE INDEX IF NOT EXISTS idx_entities_name   ON entities(name);\\nCREATE INDEX IF NOT EXISTS idx_relations_subj  ON relations(subject_id);\\nCREATE INDEX IF NOT EXISTS idx_relations_obj   ON relations(object_id);\\nCREATE INDEX IF NOT EXISTS idx_ce_chunk        ON chunk_entities(chunk_id);\\nCREATE INDEX IF NOT EXISTS idx_ce_entity       ON chunk_entities(entity_id);\\n";

pub const _LLM_ENTITY_PROMPT: &str = "Extract named entities and relationships from the text below.\\n\\nReturn ONLY a JSON object with this structure:\\n{{\\n  \"entities\": [\\n    {{\"name\": \"EntityName\", \"type\": \"PERSON|ORG|PLACE|CONCEPT|PRODUCT|OTHER\"}}\\n  ],\\n  \"relations\": [\\n    {{\"subject\": \"EntityA\", \"predicate\": \"relation_verb\", \"object\": \"EntityB\"}}\\n  ]\\n}}\\n\\nText:\\n{text}\\n\\nJSON:";

/// SQLite-backed knowledge graph with LLM/spaCy/regex entity extraction.
/// 
/// The graph enables multi-hop retrieval:
/// query → entity match → expand to related entities → recall chunks containing those entities
#[derive(Debug, Clone)]
pub struct KnowledgeGraph {
    pub db_path: PathBuf,
    pub _lock: std::sync::Mutex<()>,
}

impl KnowledgeGraph {
    pub fn new(db_path: String) -> Self {
        Self {
            db_path: PathBuf::from(db_path),
            _lock: std::sync::Mutex::new(()),
        }
    }
    pub fn _init_db(&self) -> Result<()> {
        let mut conn = /* sqlite3 */ self.db_path;
        {
            conn.executescript(_SCHEMA_SQL);
        }
    }
    pub fn _get_conn(&mut self) -> Result<sqlite3::Connection> {
        let mut conn = /* sqlite3 */ self.db_path, /* check_same_thread= */ false;
        conn.row_factory = sqlite3::Row;
        Ok(conn)
    }
    /// Extract entities and relations from chunks and store in the graph.
    /// 
    /// Args:
    /// chunks: List of chunk dicts with 'text' key.
    /// llm: Optional LLM adapter (for higher-quality extraction).
    /// use_spacy: Try spaCy before regex fallback.
    /// batch_size: Number of chunks to process per LLM call (batched for efficiency).
    /// 
    /// Returns:
    /// Stats dict: {"entities_added": N, "relations_added": M, "chunks_processed": P}
    pub fn ingest_chunks(&mut self, chunks: Vec<HashMap>, llm: Box<dyn std::any::Any>, use_spacy: bool, batch_size: i64) -> HashMap<String, i64> {
        // Extract entities and relations from chunks and store in the graph.
        // 
        // Args:
        // chunks: List of chunk dicts with 'text' key.
        // llm: Optional LLM adapter (for higher-quality extraction).
        // use_spacy: Try spaCy before regex fallback.
        // batch_size: Number of chunks to process per LLM call (batched for efficiency).
        // 
        // Returns:
        // Stats dict: {"entities_added": N, "relations_added": M, "chunks_processed": P}
        let mut stats = HashMap::from([("entities_added".to_string(), 0), ("relations_added".to_string(), 0), ("chunks_processed".to_string(), 0)]);
        for chunk in chunks.iter() {
            let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            let mut chunk_id = hashlib::sha256(text.as_bytes().to_vec()).hexdigest()[..16];
            if !text.trim().to_string() {
                continue;
            }
            let (mut entities, mut relations) = self._extract(text, llm, use_spacy);
            if !entities {
                continue;
            }
            let _ctx = self._lock;
            {
                let mut conn = self._get_conn();
                {
                    for ent in entities.iter() {
                        let mut eid = _entity_id(ent["name".to_string()]);
                        conn.execute("INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)".to_string(), (eid, ent["name".to_string()], ent.get(&"type".to_string()).cloned().unwrap_or("UNKNOWN".to_string()), chunk_id));
                        conn.execute("INSERT OR IGNORE INTO chunk_entities (chunk_id, entity_id) VALUES (?,?)".to_string(), (chunk_id, eid));
                        stats["entities_added".to_string()] += 1;
                    }
                    for rel in relations.iter() {
                        let mut sid = _entity_id(rel.get(&"subject".to_string()).cloned().unwrap_or("".to_string()));
                        let mut oid = _entity_id(rel.get(&"object".to_string()).cloned().unwrap_or("".to_string()));
                        let mut pred = rel.get(&"predicate".to_string()).cloned().unwrap_or("related_to".to_string());
                        let mut rid = hashlib::sha256(format!("{}{}{}", sid, pred, oid).as_bytes().to_vec()).hexdigest()[..16];
                        conn.execute("INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)".to_string(), (sid, rel.get(&"subject".to_string()).cloned().unwrap_or("".to_string()), "UNKNOWN".to_string(), chunk_id));
                        conn.execute("INSERT OR IGNORE INTO entities (id, name, type, chunk_id) VALUES (?,?,?,?)".to_string(), (oid, rel.get(&"object".to_string()).cloned().unwrap_or("".to_string()), "UNKNOWN".to_string(), chunk_id));
                        conn.execute("INSERT OR IGNORE INTO relations (id, subject_id, predicate, object_id, chunk_id) VALUES (?,?,?,?,?)".to_string(), (rid, sid, pred, oid, chunk_id));
                        stats["relations_added".to_string()] += 1;
                    }
                }
            }
            stats["chunks_processed".to_string()] += 1;
        }
        logger.info(format!("[KG] Ingested {} chunks => {} entities, {} relations", stats["chunks_processed".to_string()], stats["entities_added".to_string()], stats["relations_added".to_string()]));
        stats
    }
    /// Extract entities and relations using best available method.
    pub fn _extract(&self, text: String, llm: Box<dyn std::any::Any>, use_spacy: bool) -> Result<(Vec<HashMap>, Vec<HashMap>)> {
        // Extract entities and relations using best available method.
        if llm.is_some() {
            // try:
            {
                let mut prompt = format!(_LLM_ENTITY_PROMPT, /* text= */ text[..2000]);
                if /* hasattr(llm, "query_sync".to_string()) */ true {
                    let mut resp = llm.query_sync(prompt, /* max_tokens= */ 400, /* temperature= */ 0.1_f64);
                } else if /* hasattr(llm, "generate".to_string()) */ true {
                    let mut resp = llm.generate(prompt);
                } else {
                    let mut resp = "".to_string();
                }
                if resp {
                    let mut r#match = regex::Regex::new(&"\\{.*\\}".to_string()).unwrap().is_match(&resp);
                    if r#match {
                        let mut data = serde_json::from_str(&r#match.group()).unwrap();
                        (data.get(&"entities".to_string()).cloned().unwrap_or(vec![]), data.get(&"relations".to_string()).cloned().unwrap_or(vec![]))
                    }
                }
            }
            // except Exception as e:
        }
        if use_spacy {
            let (mut entities, mut relations) = _spacy_extract(text);
            if entities {
                (entities, relations)
            }
        }
        Ok(_regex_extract(text))
    }
    /// Find entities in the graph that match the query text.
    pub fn find_entities(&mut self, query: String, top_n: i64) -> Vec<HashMap> {
        // Find entities in the graph that match the query text.
        let mut tokens = re::split("\\W+".to_string(), query).iter().filter(|t| t.len() > 2).map(|t| t.to_lowercase()).collect::<Vec<_>>();
        if !tokens {
            vec![]
        }
        let mut conn = self._get_conn();
        {
            let mut results = vec![];
            let mut seen_ids = HashSet::new();
            for token in tokens[..5].iter() {
                let mut rows = conn.execute("SELECT * FROM entities WHERE LOWER(name) LIKE ? LIMIT 20".to_string(), (format!("%{}%", token))).fetchall();
                for row in rows.iter() {
                    if !seen_ids.contains(&row["id".to_string()]) {
                        seen_ids.insert(row["id".to_string()]);
                        results.push(/* dict(row) */ HashMap::new());
                    }
                }
            }
        }
        results[..top_n]
    }
    /// Graph traversal: expand entity set by following relations up to `hops` hops.
    /// Returns set of all entity IDs reachable within the hop limit.
    pub fn expand_entities(&mut self, entity_ids: Vec<String>, hops: i64) -> HashSet<String> {
        // Graph traversal: expand entity set by following relations up to `hops` hops.
        // Returns set of all entity IDs reachable within the hop limit.
        if !entity_ids {
            HashSet::new()
        }
        let mut visited = entity_ids.into_iter().collect::<HashSet<_>>();
        let mut frontier = entity_ids.into_iter().collect::<HashSet<_>>();
        let mut conn = self._get_conn();
        {
            for _ in 0..hops.iter() {
                if !frontier {
                    break;
                }
                let mut new_frontier = HashSet::new();
                for eid in frontier.iter() {
                    let mut rows = conn.execute("SELECT object_id FROM relations WHERE subject_id=? UNION SELECT subject_id FROM relations WHERE object_id=?".to_string(), (eid, eid)).fetchall();
                    for row in rows.iter() {
                        let mut nid = row[0];
                        if !visited.contains(&nid) {
                            visited.insert(nid);
                            new_frontier.insert(nid);
                        }
                    }
                }
                let mut frontier = new_frontier;
            }
        }
        visited
    }
    /// Return chunk IDs that contain any of the given entities.
    pub fn get_chunk_ids_for_entities(&mut self, entity_ids: HashSet<String>) -> Vec<String> {
        // Return chunk IDs that contain any of the given entities.
        if !entity_ids {
            vec![]
        }
        let mut placeholders = ("?".to_string() * entity_ids.len()).join(&",".to_string());
        let mut conn = self._get_conn();
        {
            let mut rows = conn.execute(format!("SELECT DISTINCT chunk_id FROM chunk_entities WHERE entity_id IN ({})", placeholders), entity_ids.into_iter().collect::<Vec<_>>()).fetchall();
        }
        rows.iter().map(|row| row[0]).collect::<Vec<_>>()
    }
    /// Entity-aware retrieval:
    /// 1. Find entities in query text
    /// 2. Expand entity set via graph traversal (multi-hop)
    /// 3. Recall chunks containing expanded entities
    /// 4. Optionally merge with standard RAG chunks (passed via rag_chunks)
    /// 
    /// Args:
    /// query_text: User query.
    /// rag_chunks: Standard RAG results (optional, for fusion).
    /// top_k: Number of results to return.
    /// hops: How many hops to traverse.
    /// 
    /// Returns:
    /// List of chunk dicts with '_kg_score' key.
    pub fn query(&mut self, query_text: String, rag_chunks: Vec<HashMap>, top_k: i64, hops: i64) -> Vec<HashMap> {
        // Entity-aware retrieval:
        // 1. Find entities in query text
        // 2. Expand entity set via graph traversal (multi-hop)
        // 3. Recall chunks containing expanded entities
        // 4. Optionally merge with standard RAG chunks (passed via rag_chunks)
        // 
        // Args:
        // query_text: User query.
        // rag_chunks: Standard RAG results (optional, for fusion).
        // top_k: Number of results to return.
        // hops: How many hops to traverse.
        // 
        // Returns:
        // List of chunk dicts with '_kg_score' key.
        if !query_text.trim().to_string() {
            if rag_chunks { rag_chunks[..top_k] } else { vec![] }
        }
        let mut matched_entities = self.find_entities(query_text, /* top_n= */ 10);
        let mut seed_ids = matched_entities.iter().map(|e| e["id".to_string()]).collect::<Vec<_>>();
        if !seed_ids {
            logger.debug("[KG] No entities found for query, returning RAG results only.".to_string());
            (rag_chunks || vec![])[..top_k]
        }
        let mut expanded_ids = self.expand_entities(seed_ids, /* hops= */ hops);
        let mut kg_chunk_ids = self.get_chunk_ids_for_entities(expanded_ids).into_iter().collect::<HashSet<_>>();
        if !kg_chunk_ids {
            (rag_chunks || vec![])[..top_k]
        }
        if rag_chunks {
            for chunk in rag_chunks.iter() {
                let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                let mut chunk_id = hashlib::sha256(text.as_bytes().to_vec()).hexdigest()[..16];
                chunk["_kg_score".to_string()] = if kg_chunk_ids.contains(&chunk_id) { 1.0_f64 } else { 0.0_f64 };
            }
            rag_chunks.sort(/* key= */ |c| (c.get(&"_kg_score".to_string()).cloned().unwrap_or(0.0_f64), c.get(&"rerank_score".to_string()).cloned().unwrap_or(c.get(&"score".to_string()).cloned().unwrap_or(0.0_f64))), /* reverse= */ true);
            rag_chunks[..top_k]
        }
        logger.debug(format!("[KG] Found {} chunks via entity expansion.", kg_chunk_ids.len()));
        vec![]
    }
    /// Return entity/relation counts.
    pub fn get_stats(&mut self) -> HashMap<String, i64> {
        // Return entity/relation counts.
        let mut conn = self._get_conn();
        {
            let mut entities = conn.execute("SELECT COUNT(*) FROM entities".to_string()).fetchone()[0];
            let mut relations = conn.execute("SELECT COUNT(*) FROM relations".to_string()).fetchone()[0];
            let mut chunks = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_entities".to_string()).fetchone()[0];
        }
        HashMap::from([("entities".to_string(), entities), ("relations".to_string(), relations), ("indexed_chunks".to_string(), chunks)])
    }
}

/// Extract entities using spaCy (no LLM needed). Returns (entities, relations=[]).
pub fn _spacy_extract(text: String) -> Result<(Vec<HashMap>, Vec<HashMap>)> {
    // Extract entities using spaCy (no LLM needed). Returns (entities, relations=[]).
    // try:
    {
        // TODO: import spacy
        let mut nlp = spacy.load("en_core_web_sm".to_string());
        let mut doc = nlp(text[..5000]);
        let mut entities = doc.ents.iter().filter(|ent| ent.text.trim().to_string().len() > 1).map(|ent| HashMap::from([("name".to_string(), ent.text.trim().to_string()), ("type".to_string(), ent.label_)])).collect::<Vec<_>>();
        (entities, vec![])
    }
    // except Exception as _e:
}

/// Minimal regex NER: capitalized noun phrases as UNKNOWN entities.
pub fn _regex_extract(text: String) -> (Vec<HashMap>, Vec<HashMap>) {
    // Minimal regex NER: capitalized noun phrases as UNKNOWN entities.
    let mut pattern = regex::Regex::new(&"\\b([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\b".to_string()).unwrap();
    let mut entities = pattern.finditer(text).iter().filter(|m| m.group(1).len() > 2).map(|m| HashMap::from([("name".to_string(), m.group(1)), ("type".to_string(), "UNKNOWN".to_string())])).collect::<Vec<_>>();
    let mut seen = HashSet::new();
    let mut unique = vec![];
    for e in entities.iter() {
        if !seen.contains(&e["name".to_string()].to_lowercase()) {
            seen.insert(e["name".to_string()].to_lowercase());
            unique.push(e);
        }
    }
    (unique[..20], vec![])
}

pub fn _entity_id(name: String) -> String {
    hashlib::sha256(name.to_lowercase().trim().to_string().as_bytes().to_vec()).hexdigest()[..16]
}
