/// Inference router — embeddings, tokenize, detokenize, count_tokens.
/// 
/// Endpoints:
/// POST /v1/embeddings
/// POST /tokenize
/// POST /detokenize
/// POST /v1/count_tokens

use anyhow::{Result, Context};
use crate::helpers::{get_state, get_llm};
use crate::schemas::{EmbeddingRequest, TokenizeRequest, DetokenizeRequest, TokenCountRequest};
use std::collections::HashMap;
use tokio;

pub static ROUTER: std::sync::LazyLock<APIRouter> = std::sync::LazyLock::new(|| Default::default());

/// OpenAI-compatible embeddings.
pub async fn embeddings(req: EmbeddingRequest) -> Result<()> {
    // OpenAI-compatible embeddings.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    let mut inputs = if /* /* isinstance(req.input, list) */ */ true { req.input } else { vec![req.input] };
    // try:
    {
        let _ctx = state::inference_semaphore;
        {
            let mut result = llm.create_embedding(inputs);
        }
    }
    // except Exception as e:
    let mut data = if /* /* isinstance(result, dict) */ */ true { result.get(&"data".to_string()).cloned().unwrap_or(result) } else { result };
    let mut usage = if /* /* isinstance(result, dict) */ */ true { result.get(&"usage".to_string()).cloned().unwrap_or(HashMap::new()) } else { HashMap::new() };
    Ok(HashMap::from([("object".to_string(), "list".to_string()), ("data".to_string(), if /* /* isinstance(data, list) */ */ true { data } else { vec![HashMap::from([("object".to_string(), "embedding".to_string()), ("embedding".to_string(), data), ("index".to_string(), 0)])] }), ("model".to_string(), state::model_id), ("usage".to_string(), (usage || HashMap::from([("prompt_tokens".to_string(), inputs.iter().map(|t| t.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len()).collect::<Vec<_>>().iter().sum::<i64>()), ("total_tokens".to_string(), inputs.iter().map(|t| t.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len()).collect::<Vec<_>>().iter().sum::<i64>())])))]))
}

/// Tokenize text using the loaded model's tokenizer.
pub async fn tokenize(req: TokenizeRequest) -> Result<()> {
    // Tokenize text using the loaded model's tokenizer.
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    // try:
    {
        let mut tokens = llm.tokenize(req.content.encode("utf-8".to_string()), /* add_bos= */ req.add_special);
        let mut result = HashMap::from([("tokens".to_string(), tokens)]);
        if /* getattr */ false {
            let mut pieces = vec![];
            for tid in tokens.iter() {
                // try:
                {
                    let mut piece = llm.detokenize(vec![tid]).decode("utf-8".to_string(), /* errors= */ "replace".to_string());
                }
                // except Exception as _e:
                pieces.push(HashMap::from([("id".to_string(), tid), ("piece".to_string(), piece)]));
            }
            result["tokens".to_string()] = pieces;
        }
        result
    }
    // except Exception as e:
}

/// Convert tokens back to text.
pub async fn detokenize(req: DetokenizeRequest) -> Result<()> {
    // Convert tokens back to text.
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    // try:
    {
        let mut text = llm.detokenize(req.tokens).decode("utf-8".to_string(), /* errors= */ "replace".to_string());
        HashMap::from([("content".to_string(), text)])
    }
    // except Exception as e:
}

/// Count tokens in text without returning the full token list.
pub async fn count_tokens(req: TokenCountRequest) -> Result<()> {
    // Count tokens in text without returning the full token list.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    // try:
    {
        let mut tokens = llm.tokenize(req.content.encode("utf-8".to_string()), /* add_bos= */ false);
        HashMap::from([("count".to_string(), tokens.len()), ("model".to_string(), state::model_id)])
    }
    // except Exception as e:
}
