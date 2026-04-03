/// Demo: Advanced Chunking Strategies
/// 
/// Demonstrates different chunking approaches for optimal retrieval.

use anyhow::{Result, Context};
use crate::chunking_strategies::{FixedSizeChunker, SentenceChunker, ParagraphChunker, SlidingWindowChunker, RecursiveChunker, MarkdownChunker};

pub const SAMPLE_TEXT: &str = "\\nMachine Learning Basics\\n\\nMachine learning is a subset of artificial intelligence. It enables systems to learn from data without being explicitly programmed.\\n\\nThere are three main types of machine learning. Supervised learning uses labeled data. Unsupervised learning finds patterns in unlabeled data. Reinforcement learning learns through trial and error.\\n\\nDeep Learning\\n\\nDeep learning is a specialized form of machine learning. It uses neural networks with multiple layers. These networks can learn complex patterns.\\n\\nApplications include image recognition, natural language processing, and game playing. Deep learning has revolutionized many fields in recent years.\\n";

pub static STRATEGIES: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub const MARKDOWN_TEXT: &str = "\\n# Introduction\\n\\nThis is the introduction section. It provides an overview of the topic.\\n\\n## Background\\n\\nThe background section gives context. It explains why this topic matters.\\n\\n### Historical Context\\n\\nHere we discuss the history. This helps understand how we got here.\\n\\n## Main Content\\n\\nThis is the main content section. It contains the core information.\\n\\n### Key Points\\n\\n- Point 1: First important point\\n- Point 2: Second important point\\n- Point 3: Third important point\\n\\n## Conclusion\\n\\nThe conclusion summarizes everything. It ties all the pieces together.\\n";

pub static MD_CHUNKER: std::sync::LazyLock<MarkdownChunker> = std::sync::LazyLock::new(|| Default::default());

pub static MD_CHUNKS: std::sync::LazyLock<String /* md_chunker.chunk */> = std::sync::LazyLock::new(|| Default::default());
