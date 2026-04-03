/// social_scanner::py — Social Media Chat Scanner for RAG_RAT
/// =========================================================
/// 
/// Supports:
/// 1. **WhatsApp**  — exported .txt chat files (Export Chat feature)
/// 2. **Telegram**  — exported JSON (Telegram Desktop) + live via Telethon API
/// 3. **Discord**   — exported JSON (DiscordChatExporter) + live via discord.py bot
/// 
/// Returns the standard ``(text, images, sources)`` tuple compatible with
/// ``content_extractor::scan_web``, ``scan_folder``, and ``email_scanner``.
/// 
/// Usage::
/// 
/// from social_scanner import (
/// scan_whatsapp_export, scan_telegram_export, scan_telegram_live,
/// scan_discord_export, scan_discord_live, scan_social,
/// )
/// 
/// # WhatsApp exported chat file
/// text, images, sources = scan_whatsapp_export("chat::txt", max_messages=500)
/// 
/// # Telegram exported JSON
/// text, images, sources = scan_telegram_export("result.json", max_messages=500)
/// 
/// # Telegram live (requires telethon + phone auth)
/// text, images, sources = await scan_telegram_live(
/// api_id=12345, api_hash="abc...", phone="+1234567890",
/// chat_name="MyGroup", max_messages=200,
/// )
/// 
/// # Discord live (requires bot token)
/// text, images, sources = await scan_discord_live(
/// bot_token="...", channel_id=123456, max_messages=500,
/// )

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const SUPPORTED_PLATFORMS: &str = "('whatsapp', 'telegram', 'discord')";

pub static _WA_PATTERNS: std::sync::LazyLock<Vec<re::compile>> = std::sync::LazyLock::new(|| Vec::new());

pub static _WA_SYSTEM: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// Try to parse a WhatsApp chat line → (timestamp, author, message) or None.
pub fn _parse_wa_line(line: String) -> Option<(String, String, String)> {
    // Try to parse a WhatsApp chat line → (timestamp, author, message) or None.
    for pat in _WA_PATTERNS.iter() {
        let mut m = pat.match(line.trim().to_string());
        if m {
            (m.group(1).trim().to_string(), m.group(2).trim().to_string(), m.group(3).trim().to_string())
        }
    }
    None
}

/// Parse a WhatsApp exported .txt chat file.
/// 
/// Parameters
/// ----------
/// path : str
/// Path to the exported .txt file.
/// max_messages : int
/// Maximum messages to ingest.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
/// Combined text, media list, source list.
pub fn scan_whatsapp_export(path: String, max_messages: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Parse a WhatsApp exported .txt chat file.
    // 
    // Parameters
    // ----------
    // path : str
    // Path to the exported .txt file.
    // max_messages : int
    // Maximum messages to ingest.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    // Combined text, media list, source list.
    let mut p = PathBuf::from(path);
    if !p.exists() {
        return Err(anyhow::anyhow!("FileNotFoundError(f'WhatsApp export not found: {path}')"));
    }
    if !p.is_file() {
        return Err(anyhow::anyhow!("ValueError(f'Expected a file, got directory: {path}')"));
    }
    let mut raw = p.read_to_string(), /* errors= */ "replace".to_string());
    let mut lines = raw.lines().map(|s| s.to_string()).collect::<Vec<String>>();
    let mut messages = vec![];
    let mut images = vec![];
    let mut current_msg = None;
    for line in lines.iter() {
        let mut parsed = _parse_wa_line(line);
        if parsed {
            if current_msg {
                messages.push(current_msg);
                if messages.len() >= max_messages {
                    break;
                }
            }
            let (mut ts, mut author, mut text) = parsed;
            if _WA_SYSTEM.search(text) {
                if ("media omitted".to_string(), "image omitted".to_string(), "video omitted".to_string()).iter().map(|kw| text.to_lowercase().contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
                    images.push(HashMap::from([("type".to_string(), "media".to_string()), ("author".to_string(), author), ("timestamp".to_string(), ts)]));
                }
                let mut current_msg = None;
                continue;
            }
            let mut current_msg = HashMap::from([("timestamp".to_string(), ts), ("author".to_string(), author), ("text".to_string(), text)]);
        } else if (current_msg && line.trim().to_string()) {
            current_msg["text".to_string()] += ("\n".to_string() + line.trim().to_string());
        }
    }
    if (current_msg && messages.len() < max_messages) {
        messages.push(current_msg);
    }
    let mut total = messages.len();
    logger.info(format!("WhatsApp export: parsed {} messages from {}", total, p.name));
    let mut all_text = vec![];
    let mut all_sources = vec![];
    for (idx, msg) in messages.iter().enumerate().iter() {
        let mut block = format!("[{}] {}:\n{}\n", msg["timestamp".to_string()], msg["author".to_string()], msg["text".to_string()]);
        all_text.push(block);
        all_sources.push(HashMap::from([("type".to_string(), "whatsapp".to_string()), ("path".to_string(), format!("whatsapp://{}/{}", p.file_stem().unwrap_or_default().to_str().unwrap_or(""), idx)), ("title".to_string(), format!("{} — {}", msg["author".to_string()], msg["timestamp".to_string()])), ("from".to_string(), msg["author".to_string()]), ("date".to_string(), msg["timestamp".to_string()]), ("chars".to_string(), msg["text".to_string()].len()), ("platform".to_string(), "whatsapp".to_string())]));
        if progress_callback {
            // try:
            {
                progress_callback((idx + 1), total);
            }
            // except Exception as exc:
        }
    }
    let mut combined = all_text.join(&"\n".to_string());
    logger.info(format!("WhatsApp scan done: {} messages, {} chars, {} media", total, combined.len(), images.len()));
    Ok((combined, images, all_sources))
}

/// Convert Telegram's mixed text field to plain string.
/// 
/// Telegram exports text as either a plain string or a list of
/// text_entity dicts like [{"type": "plain", "text": "Hello"}, ...].
pub fn _telegram_text_to_str(text_field: Box<dyn std::any::Any>) -> String {
    // Convert Telegram's mixed text field to plain string.
    // 
    // Telegram exports text as either a plain string or a list of
    // text_entity dicts like [{"type": "plain", "text": "Hello"}, ...].
    if /* /* isinstance(text_field, str) */ */ true {
        text_field
    }
    if /* /* isinstance(text_field, list) */ */ true {
        let mut parts = vec![];
        for item in text_field.iter() {
            if /* /* isinstance(item, str) */ */ true {
                parts.push(item);
            } else if /* /* isinstance(item, dict) */ */ true {
                parts.push(item.get(&"text".to_string()).cloned().unwrap_or("".to_string()));
            }
        }
        parts.join(&"".to_string())
    }
    if text_field { text_field.to_string() } else { "".to_string() }
}

/// Parse a Telegram Desktop JSON export (``result.json``).
/// 
/// Parameters
/// ----------
/// path : str
/// Path to the exported JSON file.
/// max_messages : int
/// Maximum messages to ingest.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub fn scan_telegram_export(path: String, max_messages: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Parse a Telegram Desktop JSON export (``result.json``).
    // 
    // Parameters
    // ----------
    // path : str
    // Path to the exported JSON file.
    // max_messages : int
    // Maximum messages to ingest.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    let mut p = PathBuf::from(path);
    if !p.exists() {
        return Err(anyhow::anyhow!("FileNotFoundError(f'Telegram export not found: {path}')"));
    }
    let mut data = serde_json::from_str(&p.read_to_string())).unwrap();
    let mut chat_name = data.get(&"name".to_string()).cloned().unwrap_or("Telegram Chat".to_string());
    let mut raw_messages = data.get(&"messages".to_string()).cloned().unwrap_or(vec![]);
    let mut messages = vec![];
    let mut images = vec![];
    for msg in raw_messages.iter() {
        if msg.get(&"type".to_string()).cloned() != "message".to_string() {
            continue;
        }
        let mut text = _telegram_text_to_str(msg.get(&"text".to_string()).cloned().unwrap_or("".to_string()));
        if !text.trim().to_string() {
            if (msg.get(&"photo".to_string()).cloned() || msg.get(&"file".to_string()).cloned()) {
                images.push(HashMap::from([("type".to_string(), "media".to_string()), ("media_type".to_string(), msg.get(&"media_type".to_string()).cloned().unwrap_or("unknown".to_string())), ("file".to_string(), msg.get(&"file".to_string()).cloned().unwrap_or(msg.get(&"photo".to_string()).cloned().unwrap_or("".to_string())))]));
            }
            continue;
        }
        messages.push(HashMap::from([("id".to_string(), msg.get(&"id".to_string()).cloned().unwrap_or("".to_string())), ("author".to_string(), msg.get(&"from".to_string()).cloned().unwrap_or(msg.get(&"actor".to_string()).cloned().unwrap_or("Unknown".to_string()))), ("date".to_string(), msg.get(&"date".to_string()).cloned().unwrap_or("".to_string())), ("text".to_string(), text)]));
        if messages.len() >= max_messages {
            break;
        }
    }
    let mut total = messages.len();
    logger.info(format!("Telegram export '{}': parsed {} messages", chat_name, total));
    let mut all_text = vec![];
    let mut all_sources = vec![];
    for (idx, msg) in messages.iter().enumerate().iter() {
        let mut block = format!("[{}] {}:\n{}\n", msg["date".to_string()], msg["author".to_string()], msg["text".to_string()]);
        all_text.push(block);
        all_sources.push(HashMap::from([("type".to_string(), "telegram".to_string()), ("path".to_string(), format!("telegram://{}/{}", chat_name, msg["id".to_string()])), ("title".to_string(), format!("{} — {}", msg["author".to_string()], msg["date".to_string()])), ("from".to_string(), msg["author".to_string()]), ("date".to_string(), msg["date".to_string()]), ("chars".to_string(), msg["text".to_string()].len()), ("platform".to_string(), "telegram".to_string()), ("chat_name".to_string(), chat_name)]));
        if progress_callback {
            // try:
            {
                progress_callback((idx + 1), total);
            }
            // except Exception as exc:
        }
    }
    let mut combined = all_text.join(&"\n".to_string());
    logger.info(format!("Telegram scan done: {} messages, {} chars", total, combined.len()));
    Ok((combined, images, all_sources))
}

/// Fetch messages from a Telegram chat/group using the Telethon API.
/// 
/// Requires ``pip install telethon``.
/// 
/// Parameters
/// ----------
/// api_id : int
/// Telegram API ID from https://my.telegram.org
/// api_hash : str
/// Telegram API hash.
/// phone : str
/// Phone number (e.g. "+1234567890").
/// chat_name : str
/// Chat/group name or username (e.g. "@mygroup" or "My Group").
/// max_messages : int
/// Maximum messages to fetch.
/// session_name : str
/// Telethon session file name.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub async fn scan_telegram_live(api_id: i64, api_hash: String, phone: String, chat_name: String, max_messages: i64, session_name: String, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Fetch messages from a Telegram chat/group using the Telethon API.
    // 
    // Requires ``pip install telethon``.
    // 
    // Parameters
    // ----------
    // api_id : int
    // Telegram API ID from https://my.telegram.org
    // api_hash : str
    // Telegram API hash.
    // phone : str
    // Phone number (e.g. "+1234567890").
    // chat_name : str
    // Chat/group name or username (e.g. "@mygroup" or "My Group").
    // max_messages : int
    // Maximum messages to fetch.
    // session_name : str
    // Telethon session file name.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    // try:
    {
        // TODO: from telethon import TelegramClient
        // TODO: from telethon.errors import SessionPasswordNeededError
    }
    // except ImportError as _e:
    let mut session_dir = PathBuf::from("data/social_sessions".to_string());
    session_dir.create_dir_all();
    let mut session_path = (session_dir / session_name).to_string();
    let mut client = TelegramClient(session_path, api_id, api_hash);
    client.start(/* phone= */ phone).await;
    if !client.is_user_authorized().await {
        return Err(anyhow::anyhow!("PermissionError('Telegram authentication failed. You may need to enter the code sent to your Telegram app. Run interactively first.')"));
    }
    // try:
    {
        let mut entity = client.get_entity(chat_name).await;
    }
    // except Exception as exc:
    let mut messages_list = vec![];
    let mut images = vec![];
    // async for
    while let Some(message) = client.iter_messages(entity, /* limit= */ max_messages).next().await {
        if message.text {
            let mut sender = "".to_string();
            if message.sender {
                let mut sender = (/* getattr */ "".to_string() || "".to_string());
                let mut last = (/* getattr */ "".to_string() || "".to_string());
                if last {
                    sender += format!(" {}", last);
                }
                if !sender {
                    let mut sender = (/* getattr */ "Unknown".to_string() || "Unknown".to_string());
                }
            }
            messages_list.push(HashMap::from([("id".to_string(), message.id), ("author".to_string(), sender), ("date".to_string(), if message.date { message.date.isoformat() } else { "".to_string() }), ("text".to_string(), message.text)]));
        } else if (message.photo || message.document) {
            images.push(HashMap::from([("type".to_string(), "media".to_string()), ("media_type".to_string(), if message.photo { "photo".to_string() } else { "document".to_string() }), ("message_id".to_string(), message.id)]));
        }
        if (progress_callback && messages_list) {
            // try:
            {
                progress_callback(messages_list.len(), max_messages);
            }
            // except Exception as exc:
        }
    }
    client.disconnect().await;
    messages_list.reverse();
    let mut total = messages_list.len();
    let mut resolved_name = /* getattr */ chat_name;
    logger.info(format!("Telegram live '{}': fetched {} messages", resolved_name, total));
    let mut all_text = vec![];
    let mut all_sources = vec![];
    for (idx, msg) in messages_list.iter().enumerate().iter() {
        let mut block = format!("[{}] {}:\n{}\n", msg["date".to_string()], msg["author".to_string()], msg["text".to_string()]);
        all_text.push(block);
        all_sources.push(HashMap::from([("type".to_string(), "telegram".to_string()), ("path".to_string(), format!("telegram://{}/{}", resolved_name, msg["id".to_string()])), ("title".to_string(), format!("{} — {}", msg["author".to_string()], msg["date".to_string()])), ("from".to_string(), msg["author".to_string()]), ("date".to_string(), msg["date".to_string()]), ("chars".to_string(), msg["text".to_string()].len()), ("platform".to_string(), "telegram".to_string()), ("chat_name".to_string(), resolved_name)]));
    }
    let mut combined = all_text.join(&"\n".to_string());
    logger.info(format!("Telegram live scan done: {} messages, {} chars", total, combined.len()));
    Ok((combined, images, all_sources))
}

/// Parse a Discord chat export JSON (DiscordChatExporter format).
/// 
/// Parameters
/// ----------
/// path : str
/// Path to the exported JSON file.
/// max_messages : int
/// Maximum messages to ingest.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub fn scan_discord_export(path: String, max_messages: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Parse a Discord chat export JSON (DiscordChatExporter format).
    // 
    // Parameters
    // ----------
    // path : str
    // Path to the exported JSON file.
    // max_messages : int
    // Maximum messages to ingest.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    let mut p = PathBuf::from(path);
    if !p.exists() {
        return Err(anyhow::anyhow!("FileNotFoundError(f'Discord export not found: {path}')"));
    }
    let mut data = serde_json::from_str(&p.read_to_string())).unwrap();
    let mut guild_name = data.get(&"guild".to_string()).cloned().unwrap_or(HashMap::new()).get(&"name".to_string()).cloned().unwrap_or("Discord".to_string());
    let mut channel_name = data.get(&"channel".to_string()).cloned().unwrap_or(HashMap::new()).get(&"name".to_string()).cloned().unwrap_or("unknown".to_string());
    let mut raw_messages = data.get(&"messages".to_string()).cloned().unwrap_or(vec![]);
    let mut messages = vec![];
    let mut images = vec![];
    for msg in raw_messages.iter() {
        let mut content = msg.get(&"content".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
        let mut author = msg.get(&"author".to_string()).cloned().unwrap_or(HashMap::new()).get(&"name".to_string()).cloned().unwrap_or("Unknown".to_string());
        let mut timestamp = msg.get(&"timestamp".to_string()).cloned().unwrap_or("".to_string());
        for att in msg.get(&"attachments".to_string()).cloned().unwrap_or(vec![]).iter() {
            images.push(HashMap::from([("type".to_string(), "attachment".to_string()), ("filename".to_string(), att.get(&"fileName".to_string()).cloned().unwrap_or("".to_string())), ("url".to_string(), att.get(&"url".to_string()).cloned().unwrap_or("".to_string()))]));
        }
        if !content {
            continue;
        }
        messages.push(HashMap::from([("id".to_string(), msg.get(&"id".to_string()).cloned().unwrap_or("".to_string())), ("author".to_string(), author), ("date".to_string(), timestamp), ("text".to_string(), content)]));
        if messages.len() >= max_messages {
            break;
        }
    }
    let mut total = messages.len();
    logger.info(format!("Discord export '{}/{}': parsed {} messages", guild_name, channel_name, total));
    let mut all_text = vec![];
    let mut all_sources = vec![];
    for (idx, msg) in messages.iter().enumerate().iter() {
        let mut block = format!("[{}] {}:\n{}\n", msg["date".to_string()], msg["author".to_string()], msg["text".to_string()]);
        all_text.push(block);
        all_sources.push(HashMap::from([("type".to_string(), "discord".to_string()), ("path".to_string(), format!("discord://{}/{}/{}", guild_name, channel_name, msg["id".to_string()])), ("title".to_string(), format!("{} — {}", msg["author".to_string()], msg["date".to_string()])), ("from".to_string(), msg["author".to_string()]), ("date".to_string(), msg["date".to_string()]), ("chars".to_string(), msg["text".to_string()].len()), ("platform".to_string(), "discord".to_string()), ("guild".to_string(), guild_name), ("channel".to_string(), channel_name)]));
        if progress_callback {
            // try:
            {
                progress_callback((idx + 1), total);
            }
            // except Exception as exc:
        }
    }
    let mut combined = all_text.join(&"\n".to_string());
    logger.info(format!("Discord scan done: {} messages, {} chars", total, combined.len()));
    Ok((combined, images, all_sources))
}

/// Fetch messages from a Discord channel using a bot token.
/// 
/// Requires ``pip install discord.py``.
/// 
/// Parameters
/// ----------
/// bot_token : str
/// Discord Bot token.
/// channel_id : int
/// Numeric channel ID.
/// max_messages : int
/// Maximum messages to fetch.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub async fn scan_discord_live(bot_token: String, channel_id: i64, max_messages: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Fetch messages from a Discord channel using a bot token.
    // 
    // Requires ``pip install discord.py``.
    // 
    // Parameters
    // ----------
    // bot_token : str
    // Discord Bot token.
    // channel_id : int
    // Numeric channel ID.
    // max_messages : int
    // Maximum messages to fetch.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    // try:
    {
        // TODO: import discord
    }
    // except ImportError as _e:
    let mut intents = discord.Intents.default();
    intents.message_content = true;
    let mut client = discord.Client(/* intents= */ intents);
    let mut messages_list = vec![];
    let mut images = vec![];
    let mut fetch_done = false;
    let on_ready = || {
        // global/nonlocal fetch_done
        // try:
        {
            let mut channel = client.get_channel(channel_id);
            if channel.is_none() {
                let mut channel = client.fetch_channel(channel_id).await;
            }
            let mut count = 0;
            // async for
            while let Some(message) = channel.history(/* limit= */ max_messages).next().await {
                if message.content {
                    messages_list.push(HashMap::from([("id".to_string(), message.id.to_string()), ("author".to_string(), message.author.display_name), ("date".to_string(), message.created_at.isoformat()), ("text".to_string(), message.content)]));
                }
                for att in message.attachments.iter() {
                    images.push(HashMap::from([("type".to_string(), "attachment".to_string()), ("filename".to_string(), att.filename), ("url".to_string(), att.url)]));
                }
                count += 1;
                if progress_callback {
                    // try:
                    {
                        progress_callback(count, max_messages);
                    }
                    // except Exception as exc:
                }
            }
        }
        // except Exception as exc:
        // finally:
            let mut fetch_done = true;
            client.close().await;
    };
    // try:
    {
        client.start(bot_token).await;
    }
    // except Exception as _e:
    messages_list.reverse();
    let mut total = messages_list.len();
    logger.info(format!("Discord live: fetched {} messages from channel {}", total, channel_id));
    let mut all_text = vec![];
    let mut all_sources = vec![];
    for (idx, msg) in messages_list.iter().enumerate().iter() {
        let mut block = format!("[{}] {}:\n{}\n", msg["date".to_string()], msg["author".to_string()], msg["text".to_string()]);
        all_text.push(block);
        all_sources.push(HashMap::from([("type".to_string(), "discord".to_string()), ("path".to_string(), format!("discord://live/{}/{}", channel_id, msg["id".to_string()])), ("title".to_string(), format!("{} — {}", msg["author".to_string()], msg["date".to_string()])), ("from".to_string(), msg["author".to_string()]), ("date".to_string(), msg["date".to_string()]), ("chars".to_string(), msg["text".to_string()].len()), ("platform".to_string(), "discord".to_string()), ("channel_id".to_string(), channel_id.to_string())]));
    }
    let mut combined = all_text.join(&"\n".to_string());
    Ok((combined, images, all_sources))
}

/// Unified synchronous entry point for social media scanning.
/// 
/// Parameters
/// ----------
/// platform : str
/// One of ``"whatsapp"``, ``"telegram"``, ``"discord"``.
/// mode : str
/// ``"export"`` for file-based parsing, ``"live"`` for API-based.
/// **kwargs
/// Forwarded to the underlying scanner function.
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub fn scan_social(platform: String, mode: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Unified synchronous entry point for social media scanning.
    // 
    // Parameters
    // ----------
    // platform : str
    // One of ``"whatsapp"``, ``"telegram"``, ``"discord"``.
    // mode : str
    // ``"export"`` for file-based parsing, ``"live"`` for API-based.
    // **kwargs
    // Forwarded to the underlying scanner function.
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    let mut platform = platform.to_lowercase().trim().to_string();
    if platform == "whatsapp".to_string() {
        if mode == "live".to_string() {
            return Err(anyhow::anyhow!("NotImplementedError(\"WhatsApp does not offer a public API for personal accounts. Please use the 'Export Chat' feature in WhatsApp to create a .txt file, then use mode='export'.\")"));
        }
        scan_whatsapp_export(/* ** */ kwargs)
    } else if platform == "telegram".to_string() {
        if mode == "live".to_string() {
            // TODO: import asyncio
            asyncio.run(scan_telegram_live(/* ** */ kwargs))
        }
        scan_telegram_export(/* ** */ kwargs)
    } else if platform == "discord".to_string() {
        if mode == "live".to_string() {
            // TODO: import asyncio
            asyncio.run(scan_discord_live(/* ** */ kwargs))
        }
        scan_discord_export(/* ** */ kwargs)
    } else {
        return Err(anyhow::anyhow!("ValueError(f\"Unsupported platform: '{platform}'. Supported: {', '.join(SUPPORTED_PLATFORMS)}\")"));
    }
}
