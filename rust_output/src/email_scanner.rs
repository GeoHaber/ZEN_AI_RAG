/// email_scanner::py — Email scanning for RAG_RAT
/// ==============================================
/// 
/// Supports:
/// 1. IMAP (Gmail, Outlook, Yahoo, custom) — online mailboxes
/// 2. Local email files (.eml, .mbox)
/// 
/// Returns the same ``(text, images, sources)`` tuple as
/// ``content_extractor::scan_web`` / ``scan_folder``.
/// 
/// Usage::
/// 
/// from email_scanner import scan_email_imap, scan_email_local
/// 
/// text, images, sources = scan_email_imap(
/// server="imap.gmail.com",
/// email_addr="user@gmail.com",
/// password="app-password-here",
/// folder="INBOX",
/// max_emails=100,
/// days_back=30,
/// )
/// 
/// text, images, sources = scan_email_local(
/// path="C:/Users/me/emails",   # .eml or .mbox files
/// max_emails=500,
/// )

use anyhow::{Result, Context};
use crate::utils::*;
use regex::Regex;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static IMAP_PRESETS: std::sync::LazyLock<HashMap<String, (String, i64)>> = std::sync::LazyLock::new(|| HashMap::new());

pub static COMMON_FOLDERS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Decode an RFC-2047 encoded email header to plain text.
pub fn _decode_header(raw: Option<String>) -> String {
    // Decode an RFC-2047 encoded email header to plain text.
    if !raw {
        "".to_string()
    }
    let mut parts = email.header.decode_header(raw);
    let mut decoded = vec![];
    for (data, charset) in parts.iter() {
        if /* /* isinstance(data, bytes) */ */ true {
            decoded.push(data.decode((charset || "utf-8".to_string()), /* errors= */ "replace".to_string()));
        } else {
            decoded.push(data.to_string());
        }
    }
    decoded.join(&" ".to_string()).trim().to_string()
}

/// Extract the plain-text body from an email Message object.
pub fn _extract_body(msg: email::message::Message) -> String {
    // Extract the plain-text body from an email Message object.
    let mut body_parts = vec![];
    if msg.is_multipart() {
        for part in msg.walk().iter() {
            let mut ctype = part.get_content_type();
            let mut disposition = part.get(&"Content-Disposition".to_string()).cloned().unwrap_or("".to_string()).to_string();
            if (ctype == "text/plain".to_string() && !disposition.contains(&"attachment".to_string())) {
                let mut payload = part.get_payload(/* decode= */ true);
                if payload {
                    let mut charset = (part.get_content_charset() || "utf-8".to_string());
                    body_parts.push(payload.decode(charset, /* errors= */ "replace".to_string()));
                }
            } else if (ctype == "text/html".to_string() && !body_parts) {
                let mut payload = part.get_payload(/* decode= */ true);
                if payload {
                    let mut charset = (part.get_content_charset() || "utf-8".to_string());
                    let mut html = payload.decode(charset, /* errors= */ "replace".to_string());
                    body_parts.push(_strip_html(html));
                }
            }
        }
    } else {
        let mut payload = msg.get_payload(/* decode= */ true);
        if payload {
            let mut charset = (msg.get_content_charset() || "utf-8".to_string());
            let mut text = payload.decode(charset, /* errors= */ "replace".to_string());
            if msg.get_content_type() == "text/html".to_string() {
                let mut text = _strip_html(text);
            }
            body_parts.push(text);
        }
    }
    body_parts.join(&"\n".to_string()).trim().to_string()
}

/// Rough HTML-to-text (no dependency needed).
pub fn _strip_html(html: String) -> String {
    // Rough HTML-to-text (no dependency needed).
    let mut text = regex::Regex::new(&"<style[^>]*>.*?</style>".to_string()).unwrap().replace_all(&"".to_string(), html).to_string();
    let mut text = regex::Regex::new(&"<script[^>]*>.*?</script>".to_string()).unwrap().replace_all(&"".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"<br\\s*/?>".to_string()).unwrap().replace_all(&"\n".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"<[^>]+>".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"&nbsp;".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string();
    let mut text = regex::Regex::new(&"\\s+".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string();
    text.trim().to_string()
}

/// Pull out attachment metadata as image-like dicts.
pub fn _extract_attachments(msg: email::message::Message) -> Vec<HashMap> {
    // Pull out attachment metadata as image-like dicts.
    let mut images = vec![];
    if !msg.is_multipart() {
        images
    }
    for part in msg.walk().iter() {
        let mut disposition = part.get(&"Content-Disposition".to_string()).cloned().unwrap_or("".to_string()).to_string();
        if disposition.contains(&"attachment".to_string()) {
            let mut filename = _decode_header(part.get_filename());
            let mut ctype = part.get_content_type();
            let mut size = (part.get_payload(/* decode= */ true) || b"").len();
            images.push(HashMap::from([("type".to_string(), "attachment".to_string()), ("filename".to_string(), (filename || "unnamed".to_string())), ("content_type".to_string(), ctype), ("size".to_string(), size)]));
        }
    }
    images
}

/// Extract and normalise the Date header → ISO string.
pub fn _parse_date(msg: email::message::Message) -> Result<String> {
    // Extract and normalise the Date header → ISO string.
    let mut raw = msg.get(&"Date".to_string()).cloned().unwrap_or("".to_string());
    // try:
    {
        let mut parsed = email.parsedate_to_datetime(raw);
        parsed.isoformat()
    }
    // except Exception as _e:
}

/// Convert one email.message.Message → (body_text, attachments, source).
pub fn _msg_to_record(msg: email::message::Message, uid: String) -> (String, Vec<HashMap>, HashMap) {
    // Convert one email.message.Message → (body_text, attachments, source).
    let mut subject = _decode_header(msg.get(&"Subject".to_string()).cloned());
    let mut sender = _decode_header(msg.get(&"From".to_string()).cloned());
    let mut to = _decode_header(msg.get(&"To".to_string()).cloned());
    let mut date_str = _parse_date(msg);
    let mut body = _extract_body(msg);
    let mut attachments = _extract_attachments(msg);
    let mut block = format!("Subject: {}\nFrom: {}\nTo: {}\nDate: {}\n---\n{}\n", subject, sender, to, date_str, body);
    let mut source = HashMap::from([("type".to_string(), "email".to_string()), ("path".to_string(), if uid { format!("email://{}", uid) } else { format!("email://{}", subject[..60]) }), ("title".to_string(), (subject || "(no subject)".to_string())), ("from".to_string(), sender), ("to".to_string(), to), ("date".to_string(), date_str), ("chars".to_string(), body.len()), ("attachments".to_string(), attachments.len())]);
    (block, attachments, source)
}

/// Scan an IMAP mailbox and return ``(text, images, sources)``.
/// 
/// Parameters
/// ----------
/// server : str
/// IMAP hostname (e.g. ``imap.gmail.com``).
/// Can also be a preset key like ``"gmail"``, ``"outlook"``.
/// email_addr : str
/// Full email address (login username).
/// password : str
/// Password or app-specific password.
/// folder : str
/// Mailbox folder to scan (default ``"INBOX"``).
/// max_emails : int
/// Max messages to fetch (newest first).
/// days_back : int
/// Only fetch messages from the last N days.
/// progress_callback : optional
/// ``callback(done, total)`` — called after each email.
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
/// Combined text, attachments list, source list.
pub fn scan_email_imap(server: String, email_addr: String, password: String, folder: String, max_emails: i64, days_back: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Scan an IMAP mailbox and return ``(text, images, sources)``.
    // 
    // Parameters
    // ----------
    // server : str
    // IMAP hostname (e.g. ``imap.gmail.com``).
    // Can also be a preset key like ``"gmail"``, ``"outlook"``.
    // email_addr : str
    // Full email address (login username).
    // password : str
    // Password or app-specific password.
    // folder : str
    // Mailbox folder to scan (default ``"INBOX"``).
    // max_emails : int
    // Max messages to fetch (newest first).
    // days_back : int
    // Only fetch messages from the last N days.
    // progress_callback : optional
    // ``callback(done, total)`` — called after each email.
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    // Combined text, attachments list, source list.
    let mut preset = IMAP_PRESETS.get(&server::to_lowercase().trim().to_string()).cloned();
    if preset {
        let (mut server, mut port) = preset;
    } else {
        let mut port = 993;
    }
    let mut all_text = vec![];
    let mut all_images = vec![];
    let mut all_sources = vec![];
    let mut ctx = ssl.create_default_context();
    // try:
    {
        let mut conn = imaplib.IMAP4_SSL(server, port, /* ssl_context= */ ctx);
    }
    // except Exception as exc:
    // try:
    {
        conn.login(email_addr, password);
    }
    // except imaplib.IMAP4.error as exc:
    // try:
    {
        let (mut status, _) = conn.select(format!("\"{}\"", folder), /* readonly= */ true);
        if status != "OK".to_string() {
            conn.logout();
            return Err(anyhow::anyhow!("FileNotFoundError(f'Mailbox folder \"{folder}\" not found')"));
        }
        let mut since_date = (datetime::now() - timedelta(/* days= */ days_back)).strftime("%d-%b-%Y".to_string());
        let (_, mut msg_nums) = conn.search(None, format!("(SINCE \"{}\")", since_date));
        let mut uid_list = if msg_nums[0] { msg_nums[0].split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>() } else { vec![] };
        let mut uid_list = uid_list[-max_emails..][..];
        let mut total = uid_list.len();
        logger.info("IMAP %s/%s — %d messages to fetch".to_string(), server, folder, total);
        for (idx, uid) in uid_list.iter().enumerate().iter() {
            // try:
            {
                let (_, mut data) = conn.fetch(uid, "(RFC822)".to_string());
                let mut raw = if (data && data[0]) { data[0][1] } else { None };
                if !raw {
                    continue;
                }
                let mut msg = email.message_from_bytes(raw);
                let (mut body, mut attachments, mut source) = _msg_to_record(msg, /* uid= */ uid.decode("ascii".to_string(), /* errors= */ "replace".to_string()));
                all_text.push(body);
                all_images.extend(attachments);
                all_sources.push(source);
            }
            // except Exception as exc:
            if progress_callback {
                // try:
                {
                    progress_callback((idx + 1), total);
                }
                // except Exception as exc:
            }
        }
    }
    // finally:
        // try:
        {
            conn.close();
        }
        // except Exception as exc:
        conn.logout();
    let mut combined = all_text.join(&"\n\n".to_string());
    logger.info("IMAP scan done: %d emails, %d chars, %d attachments".to_string(), all_sources.len(), combined.len(), all_images.len());
    Ok((combined, all_images, all_sources))
}

/// Scan local ``.eml`` files or ``.mbox`` archives.
/// 
/// Parameters
/// ----------
/// path : str
/// Path to a folder of ``.eml`` files, a single ``.mbox`` file,
/// or a single ``.eml`` file.
/// max_emails : int
/// Maximum messages to process.
/// progress_callback : optional
/// ``callback(done, total)``
/// 
/// Returns
/// -------
/// (str, List[Dict], List[Dict])
pub fn scan_email_local(path: String, max_emails: i64, progress_callback: Option<Box<dyn Fn>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<(String, Vec<HashMap>, Vec<HashMap>)> {
    // Scan local ``.eml`` files or ``.mbox`` archives.
    // 
    // Parameters
    // ----------
    // path : str
    // Path to a folder of ``.eml`` files, a single ``.mbox`` file,
    // or a single ``.eml`` file.
    // max_emails : int
    // Maximum messages to process.
    // progress_callback : optional
    // ``callback(done, total)``
    // 
    // Returns
    // -------
    // (str, List[Dict], List[Dict])
    let mut p = PathBuf::from(path);
    if !p.exists() {
        return Err(anyhow::anyhow!("FileNotFoundError(f'Path does not exist: {path}')"));
    }
    let mut all_text = vec![];
    let mut all_images = vec![];
    let mut all_sources = vec![];
    let mut messages = vec![];
    if (p.is_file() && p.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase() == ".mbox".to_string()) {
        let mut mbox = mailbox.mbox(p.to_string());
        for (key, msg) in mbox.iter().iter() {
            messages.push((format!("mbox:{}", key), msg));
            if messages.len() >= max_emails {
                break;
            }
        }
        mbox.close();
    } else if (p.is_file() && p.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase() == ".eml".to_string()) {
        let mut f = File::open(p)?;
        {
            let mut msg = email.message_from_bytes(f.read());
        }
        messages.push((p.name, msg));
    } else if p.is_dir() {
        let mut eml_files = { let mut v = p.rglob("*.eml".to_string()).clone(); v.sort(); v }[..max_emails];
        let mut mbox_files = { let mut v = p.rglob("*.mbox".to_string()).clone(); v.sort(); v };
        for ef in eml_files.iter() {
            // try:
            {
                let mut f = File::open(ef)?;
                {
                    let mut msg = email.message_from_bytes(f.read());
                }
                messages.push((ef.to_string(), msg));
            }
            // except Exception as exc:
            if messages.len() >= max_emails {
                break;
            }
        }
        for mf in mbox_files.iter() {
            if messages.len() >= max_emails {
                break;
            }
            // try:
            {
                let mut mbox = mailbox.mbox(mf.to_string());
                for (key, msg) in mbox.iter().iter() {
                    messages.push((format!("{}:{}", mf.name, key), msg));
                    if messages.len() >= max_emails {
                        break;
                    }
                }
                mbox.close();
            }
            // except Exception as exc:
        }
    } else {
        return Err(anyhow::anyhow!("FileNotFoundError(f'Path is not a directory, .eml, or .mbox file: {path}')"));
    }
    let mut total = messages.len();
    logger.info("Local email scan — %d messages to process".to_string(), total);
    for (idx, (uid, msg)) in messages.iter().enumerate().iter() {
        // try:
        {
            let (mut body, mut attachments, mut source) = _msg_to_record(msg, /* uid= */ uid);
            all_text.push(body);
            all_images.extend(attachments);
            all_sources.push(source);
        }
        // except Exception as exc:
        if progress_callback {
            // try:
            {
                progress_callback((idx + 1), total);
            }
            // except Exception as exc:
        }
    }
    let mut combined = all_text.join(&"\n\n".to_string());
    logger.info("Local email scan done: %d emails, %d chars".to_string(), all_sources.len(), combined.len());
    Ok((combined, all_images, all_sources))
}

/// Unified entry point.
/// 
/// Parameters
/// ----------
/// mode : str
/// ``"imap"`` for online IMAP scanning, ``"local"`` for .eml/.mbox files.
/// **kwargs
/// Forwarded to ``scan_email_imap()`` or ``scan_email_local()``.
pub fn scan_email(mode: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> (String, Vec<HashMap>, Vec<HashMap>) {
    // Unified entry point.
    // 
    // Parameters
    // ----------
    // mode : str
    // ``"imap"`` for online IMAP scanning, ``"local"`` for .eml/.mbox files.
    // **kwargs
    // Forwarded to ``scan_email_imap()`` or ``scan_email_local()``.
    if mode == "local".to_string() {
        scan_email_local(/* ** */ kwargs)
    }
    scan_email_imap(/* ** */ kwargs)
}
