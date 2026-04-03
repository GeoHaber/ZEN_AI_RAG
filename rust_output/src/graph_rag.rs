/// Core/graph_rag::py — Graph RAG with Community Detection & Summarization.
/// 
/// Industry best practice: Beyond basic entity-triple storage, Graph RAG
/// builds community-level summaries enabling answers to global/thematic
/// queries that no single chunk can address.
/// 
/// Pipeline:
/// 1. Extract entities and relationships from chunks
/// 2. Build graph communities (connected components / Leiden)
/// 3. Generate summaries per community
/// 4. At query time: match communities → use summaries as context
/// 5. For local queries: traditional entity lookup + multi-hop
/// 
/// This is inspired by Microsoft's "GraphRAG" (2024) paper which showed
/// that community summaries dramatically improve answers to global
/// sensemaking questions ("What are the main themes in this dataset?").
/// 
/// References:
/// - Edge et al. "From Local to Global: A Graph RAG Approach" (Microsoft, 2024)
/// - Community detection via connected components (lightweight alternative to Leiden)

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// A community of related entities from the knowledge graph.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Community {
    pub community_id: String,
    pub entities: Vec<String>,
    pub relationships: Vec<(String, String, String)>,
    pub summary: String,
    pub keywords: Vec<String>,
    pub size: i64,
    pub level: i64,
}

/// Result from Graph RAG query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphRAGResult {
    pub answer: String,
    pub matched_communities: Vec<Community>,
    pub entity_context: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub strategy: String,
    pub community_summaries_used: i64,
}

/// Graph-based RAG with community detection and hierarchical summarization.
/// 
/// Extends the basic KnowledgeGraph with:
/// - Automatic community detection (connected components)
/// - LLM-generated community summaries
/// - Global query answering via community map-reduce
/// - Local query answering via entity + multi-hop traversal
/// 
/// Usage:
/// graph_rag = GraphRAG(knowledge_graph=kg, llm_fn=my_generate)
/// graph_rag::build_communities()  # After indexing documents
/// 
/// # Global query (themes, overview)
/// result = graph_rag::query("What are the main themes?", strategy="global")
/// 
/// # Local query (specific entity)
/// result = graph_rag::query("How does X relate to Y?", strategy="local")
#[derive(Debug, Clone)]
pub struct GraphRAG {
    pub kg: String,
    pub llm_fn: String,
    pub min_community_size: String,
    pub max_summary_len: String,
    pub communities: Vec<Community>,
    pub _entity_to_community: HashMap<String, String>,
}

impl GraphRAG {
    /// Args:
    /// knowledge_graph: KnowledgeGraph instance for entity/triple data
    /// llm_fn: function(prompt) -> str for summarization
    /// min_community_size: minimum entities to form a community
    /// max_community_summary_len: max chars per community summary
    pub fn new(knowledge_graph: Box<dyn std::any::Any>, llm_fn: Option<Box<dyn Fn>>, min_community_size: i64, max_community_summary_len: i64) -> Self {
        Self {
            kg: knowledge_graph,
            llm_fn,
            min_community_size,
            max_summary_len: max_community_summary_len,
            communities: Vec::new(),
            _entity_to_community: HashMap::new(),
        }
    }
    /// Detect communities via connected components and generate summaries.
    /// 
    /// Steps:
    /// 1. Extract adjacency from knowledge graph
    /// 2. Find connected components (lightweight community detection)
    /// 3. Filter by min size
    /// 4. Generate summaries per community
    pub fn build_communities(&mut self) -> Vec<Community> {
        // Detect communities via connected components and generate summaries.
        // 
        // Steps:
        // 1. Extract adjacency from knowledge graph
        // 2. Find connected components (lightweight community detection)
        // 3. Filter by min size
        // 4. Generate summaries per community
        if !self.kg {
            logger.warning("[GraphRAG] No knowledge graph provided".to_string());
            vec![]
        }
        let (mut adjacency, mut entity_names) = self._build_adjacency();
        if !adjacency {
            logger.info("[GraphRAG] Empty graph, no communities to build".to_string());
            vec![]
        }
        let mut components = self._connected_components(adjacency, entity_names);
        self.communities = vec![];
        self._entity_to_community = HashMap::new();
        for (i, (entities, relationships)) in components.iter().enumerate().iter() {
            if entities.len() < self.min_community_size {
                continue;
            }
            let mut cid = hashlib::sha256({ let mut v = entities.clone(); v.sort(); v }.join(&"|".to_string()).as_bytes().to_vec()).hexdigest()[..12];
            let mut community = Community(/* community_id= */ cid, /* entities= */ { let mut v = entities.clone(); v.sort(); v }, /* relationships= */ relationships, /* size= */ entities.len(), /* keywords= */ self._extract_keywords(entities, relationships));
            if self.llm_fn {
                community.summary = self._generate_community_summary(community);
            } else {
                community.summary = self._heuristic_summary(community);
            }
            self.communities.push(community);
            for entity in entities.iter() {
                self._entity_to_community[entity.to_lowercase()] = cid;
            }
        }
        logger.info(format!("[GraphRAG] Built {} communities from {} entities", self.communities.len(), self.communities.iter().map(|c| c.size).collect::<Vec<_>>().iter().sum::<i64>()));
        self.communities
    }
    /// Answer a query using the knowledge graph and community summaries.
    /// 
    /// Args:
    /// query: User query
    /// strategy: "local" (entity lookup), "global" (community summaries),
    /// or "auto" (detect best strategy)
    /// top_k_communities: max communities for global queries
    pub fn query(&mut self, query: String, strategy: String, top_k_communities: i64) -> GraphRAGResult {
        // Answer a query using the knowledge graph and community summaries.
        // 
        // Args:
        // query: User query
        // strategy: "local" (entity lookup), "global" (community summaries),
        // or "auto" (detect best strategy)
        // top_k_communities: max communities for global queries
        if strategy == "auto".to_string() {
            let mut strategy = self._detect_strategy(query);
        }
        if strategy == "global".to_string() {
            self._global_query(query, top_k_communities)
        } else {
            self._local_query(query)
        }
    }
    /// Answer using community summaries (map-reduce pattern).
    /// 
    /// 1. Match query to relevant communities
    /// 2. Collect community summaries
    /// 3. Use summaries as context for generation
    pub fn _global_query(&mut self, query: String, top_k: i64) -> Result<GraphRAGResult> {
        // Answer using community summaries (map-reduce pattern).
        // 
        // 1. Match query to relevant communities
        // 2. Collect community summaries
        // 3. Use summaries as context for generation
        let mut matched = self._match_communities(query, top_k);
        if !matched {
            GraphRAGResult(/* strategy= */ "global".to_string())
        }
        let mut summaries = vec![];
        for community in matched.iter() {
            if community.summary {
                summaries.push(format!("[Community: {}]\n{}", community.entities[..5].join(&", ".to_string()), community.summary));
            }
        }
        let mut context = summaries.join(&"\n\n".to_string());
        let mut answer = "".to_string();
        if (self.llm_fn && context) {
            // try:
            {
                let mut prompt = format!("Using the following knowledge graph community summaries, answer the question comprehensively.\n\nCommunity Summaries:\n{}\n\nQuestion: {}\n\nAnswer:", context, query);
                let mut answer = self.llm_fn(prompt);
            }
            // except Exception as e:
        }
        Ok(GraphRAGResult(/* answer= */ (answer || "".to_string()), /* matched_communities= */ matched, /* strategy= */ "global".to_string(), /* community_summaries_used= */ matched.len()))
    }
    /// Answer using entity lookup and multi-hop traversal.
    pub fn _local_query(&mut self, query: String) -> Result<GraphRAGResult> {
        // Answer using entity lookup and multi-hop traversal.
        if !self.kg {
            GraphRAGResult(/* strategy= */ "local".to_string())
        }
        let mut entities = self._extract_query_entities(query);
        let mut entity_context = vec![];
        for entity in entities[..5].iter() {
            // try:
            {
                let mut triples = self.kg.query_entity(entity);
                if triples {
                    entity_context.push(HashMap::from([("entity".to_string(), entity), ("facts".to_string(), triples[..10])]));
                }
            }
            // except Exception as _e:
        }
        if entities.len() >= 2 {
            // try:
            {
                let mut paths = self.kg.multi_hop(entities[0], entities[1], /* max_hops= */ 3);
                if paths {
                    entity_context.push(HashMap::from([("entity".to_string(), format!("{} → {}", entities[0], entities[1])), ("paths".to_string(), paths[..3])]));
                }
            }
            // except Exception as _e:
        }
        let mut matched_communities = vec![];
        for entity in entities.iter() {
            let mut cid = self._entity_to_community.get(&entity.to_lowercase()).cloned();
            if cid {
                let mut community = next(self.communities.iter().filter(|c| c.community_id == cid).map(|c| c).collect::<Vec<_>>(), None);
                if (community && !matched_communities.contains(&community)) {
                    matched_communities.push(community);
                }
            }
        }
        Ok(GraphRAGResult(/* entity_context= */ entity_context, /* matched_communities= */ matched_communities[..3], /* strategy= */ "local".to_string()))
    }
    /// Extract adjacency list from knowledge graph.
    pub fn _build_adjacency(&mut self) -> Result<(HashMap<String, HashSet<String>>, HashMap<String, String>)> {
        // Extract adjacency list from knowledge graph.
        let mut adjacency = defaultdict(set);
        let mut entity_names = HashMap::new();
        // try:
        {
            let mut conn = self.kg._get_conn();
            let mut rows = conn.execute("SELECT id, name FROM entities".to_string()).fetchall();
            for r in rows.iter() {
                entity_names[r["id".to_string()]] = r["name".to_string()];
            }
            let mut rows = conn.execute("SELECT subject_id, predicate, object_id FROM triples".to_string()).fetchall();
            for r in rows.iter() {
                let (mut sid, mut oid) = (r["subject_id".to_string()], r["object_id".to_string()]);
                adjacency[&sid].insert(oid);
                adjacency[&oid].insert(sid);
            }
        }
        // except Exception as e:
        Ok((adjacency, entity_names))
    }
    /// Find connected components in the graph.
    pub fn _connected_components(adjacency: HashMap<String, HashSet<String>>, entity_names: HashMap<String, String>) -> Vec<(Vec<String>, Vec<(String, String, String)>)> {
        // Find connected components in the graph.
        let mut visited = HashSet::new();
        let mut components = vec![];
        for node in adjacency.iter() {
            if visited.contains(&node) {
                continue;
            }
            let mut component_nodes = HashSet::new();
            let mut queue = vec![node];
            while queue {
                let mut current = queue.remove(&0);
                if visited.contains(&current) {
                    continue;
                }
                visited.insert(current);
                component_nodes.insert(current);
                for neighbor in adjacency.get(&current).cloned().unwrap_or(HashSet::new()).iter() {
                    if !visited.contains(&neighbor) {
                        queue.push(neighbor);
                    }
                }
            }
            let mut names = component_nodes.iter().map(|n| entity_names.get(&n).cloned().unwrap_or(n)).collect::<Vec<_>>();
            let mut relationships = vec![];
            for n in component_nodes.iter() {
                for neighbor in adjacency.get(&n).cloned().unwrap_or(HashSet::new()).iter() {
                    if component_nodes.contains(&neighbor) {
                        let mut subj = entity_names.get(&n).cloned().unwrap_or(n);
                        let mut obj = entity_names.get(&neighbor).cloned().unwrap_or(neighbor);
                        relationships.push((subj, "related_to".to_string(), obj));
                    }
                }
            }
            components.push((names, relationships));
        }
        components
    }
    /// Match query to relevant communities via keyword overlap.
    pub fn _match_communities(&mut self, query: String, top_k: i64) -> Vec<Community> {
        // Match query to relevant communities via keyword overlap.
        let mut query_words = re::findall("\\b\\w{3,}\\b".to_string(), query).iter().map(|w| w.to_lowercase()).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>();
        let mut scored = vec![];
        for community in self.communities.iter() {
            let mut community_words = community.keywords.iter().map(|w| w.to_lowercase()).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>();
            for entity in community.entities.iter() {
                community_words.extend(re::findall("\\b\\w{3,}\\b".to_string(), entity).iter().map(|w| w.to_lowercase()).collect::<Vec<_>>());
            }
            let mut overlap = (query_words & community_words).len();
            if overlap > 0 {
                let mut score = (overlap / query_words.len().max(1));
                scored.push((community, score));
            }
        }
        scored.sort(/* key= */ |x| x[1], /* reverse= */ true);
        scored[..top_k].iter().map(|(c, _)| c).collect::<Vec<_>>()
    }
    /// Use LLM to generate a community summary.
    pub fn _generate_community_summary(&mut self, community: Community) -> Result<String> {
        // Use LLM to generate a community summary.
        // try:
        {
            let mut entities_str = community.entities[..15].join(&", ".to_string());
            let mut rels_str = community.relationships[..20].iter().map(|(s, p, o)| format!("  - {} → {} → {}", s, p, o)).collect::<Vec<_>>().join(&"\n".to_string());
            let mut prompt = format!("The following entities and relationships form a thematic community in a knowledge graph. Write a concise summary (2-4 sentences) describing the main theme and key facts.\n\nEntities: {}\nRelationships:\n{}\n\nSummary:", entities_str, rels_str);
            let mut response = self.llm_fn(prompt);
            if (response && response.trim().to_string().len() > 20) {
                response.trim().to_string()[..self.max_summary_len]
            }
        }
        // except Exception as e:
        Ok(self._heuristic_summary(community))
    }
    /// Generate a simple summary without LLM.
    pub fn _heuristic_summary(community: Community) -> String {
        // Generate a simple summary without LLM.
        let mut entities = community.entities[..8].join(&", ".to_string());
        let mut n_rels = community.relationships.len();
        format!("This community contains {} entities including {}. There are {} known relationships among them.", community.size, entities, n_rels)
    }
    /// Extract keywords from community entities and relationships.
    pub fn _extract_keywords(entities: Vec<String>, relationships: Vec<(String, String, String)>) -> Vec<String> {
        // Extract keywords from community entities and relationships.
        let mut words = HashSet::new();
        for entity in entities.iter() {
            words.extend(re::findall("\\b\\w{3,}\\b".to_string(), entity).iter().map(|w| w.to_lowercase()).collect::<Vec<_>>());
        }
        for (s, p, o) in relationships.iter() {
            words.extend(re::findall("\\b\\w{3,}\\b".to_string(), format!("{} {} {}", s, p, o)).iter().map(|w| w.to_lowercase()).collect::<Vec<_>>());
        }
        { let mut v = words.clone(); v.sort(); v }
    }
    /// Extract potential entity names from query.
    pub fn _extract_query_entities(query: String) -> Vec<String> {
        // Extract potential entity names from query.
        let mut entities = re::findall("\\b[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\b".to_string(), query);
        entities += re::findall("\"([^\"]+)\"".to_string(), query);
        entities += re::findall("'([^']+)'".to_string(), query);
        if !entities {
            let mut entities = re::findall("\\b\\w{4,}\\b".to_string(), query).iter().filter(|w| !HashSet::from(["what".to_string(), "where".to_string(), "when".to_string(), "which".to_string(), "about".to_string(), "does".to_string(), "have".to_string(), "that".to_string(), "this".to_string(), "with".to_string(), "from".to_string(), "they".to_string(), "been".to_string(), "were".to_string(), "their".to_string(), "between".to_string(), "relationship".to_string(), "connection".to_string()]).contains(&w.to_lowercase())).map(|w| w).collect::<Vec<_>>();
        }
        entities[..5]
    }
    /// Detect whether a query is global or local.
    pub fn _detect_strategy(query: String) -> String {
        // Detect whether a query is global or local.
        let mut global_markers = vec!["main themes".to_string(), "overview".to_string(), "summarize".to_string(), "key topics".to_string(), "what are the".to_string(), "list all".to_string(), "major findings".to_string(), "general".to_string(), "overall".to_string(), "themes".to_string(), "categories".to_string()];
        let mut q_lower = query.to_lowercase();
        for marker in global_markers.iter() {
            if q_lower.contains(&marker) {
                "global".to_string()
            }
        }
        "local".to_string()
    }
}
