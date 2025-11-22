// Simple cost estimator for demo purposes.
// It maps providers/models to a cost per token and returns estimated cost.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use lazy_static::lazy_static;

#[derive(Deserialize, Serialize, Debug)]
struct ProviderConfig {
    models: Option<HashMap<String, f64>>,
    default: f64,
}

#[derive(Deserialize, Serialize, Debug)]
struct CostRatesConfig {
    providers: HashMap<String, ProviderConfig>,
}

lazy_static! {
    static ref COST_RATES: CostRatesConfig = {
        let config_path = "src-tauri/config/cost_rates.json";
        match fs::read_to_string(config_path) {
            Ok(content) => {
                serde_json::from_str(&content).unwrap_or_else(|_| default_config())
            }
            Err(_) => default_config(),
        }
    };
}

fn default_config() -> CostRatesConfig {
    serde_json::from_str(r#"{
        "providers": {
            "openai": {
                "models": {
                    "gpt-4-turbo": 0.00006,
                    "gpt-4": 0.0002
                },
                "default": 0.00003
            },
            "anthropic": {
                "default": 0.000025
            },
            "ollama": {
                "default": 0.000001
            },
            "gemini": {
                "default": 0.00004
            }
        }
    }"#).unwrap()
}

pub fn cost_per_token(provider: &str, model: Option<&str>) -> f64 {
    if let Some(provider_config) = COST_RATES.providers.get(provider) {
        if let Some(model) = model {
            if let Some(models) = &provider_config.models {
                if let Some(cost) = models.get(model) {
                    return *cost;
                }
            }
        }
        provider_config.default
    } else {
        0.00002 // fallback
    }
}

pub fn estimate_cost(provider: &str, model: Option<&str>, tokens: usize) -> f64 {
    let per_token = cost_per_token(provider, model);
    (tokens as f64) * per_token
}

// Very naive token estimate based on characters: 1 token ≈ 4 chars
pub fn estimate_tokens_from_text(text: &str) -> usize {
    let len = text.chars().count();
    ((len as f64) / 4.0).ceil() as usize
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cost_per_token_known_provider() {
        let cost = cost_per_token("openai", Some("gpt-4-turbo"));
        assert_eq!(cost, 0.00006);
    }

    #[test]
    fn test_cost_per_token_default_model() {
        let cost = cost_per_token("openai", Some("unknown-model"));
        assert_eq!(cost, 0.00003); // default for openai
    }

    #[test]
    fn test_cost_per_token_unknown_provider() {
        let cost = cost_per_token("unknown", None);
        assert_eq!(cost, 0.00002); // fallback
    }

    #[test]
    fn test_estimate_cost() {
        let cost = estimate_cost("openai", Some("gpt-4-turbo"), 1000);
        assert_eq!(cost, 0.06); // 1000 * 0.00006
    }

    #[test]
    fn test_estimate_tokens_from_text() {
        let tokens = estimate_tokens_from_text("hello world");
        assert_eq!(tokens, 3); // 11 chars / 4 ≈ 2.75, ceil to 3
    }
}
