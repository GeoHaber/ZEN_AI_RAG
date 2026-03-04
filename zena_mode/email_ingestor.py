import logging
import mailbox
from email.utils import parsedate_to_datetime
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Try importing PST handling libraries
try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    from libratom.lib.pff import PffArchive
    LIBRATOM_AVAILABLE = True
except ImportError:
    LIBRATOM_AVAILABLE = False

logger = logging.getLogger(__name__)

class EmailIngestor:
    """
    Ingests email archives (MBOX, PST) and converts them to RAG-ready documents.
    """

    def __init__(self):
        self.supported_formats = {'.mbox', '.pst', '.ost'}

    def ingest(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Auto-detect format and ingest email file.
        Returns list of documents compatible with RAG pipeline.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[Email] File not found: {file_path}")
            return []

        ext = path.suffix.lower()
        if ext == '.mbox':
            return self.scan_mbox(path)
        elif ext in ['.pst', '.ost']:
            return self.scan_pst(path)
        else:
            logger.error(f"[Email] Unsupported format: {ext}")
            return []

    def scan_mbox(self, path: Path) -> List[Dict[str, Any]]:
        """Parse MBOX files (Thunderbird, etc)"""
        logger.info(f"[Email] Scanning MBOX: {path}")
        documents = []
        try:
            mbox = mailbox.mbox(str(path))
            for i, message in enumerate(mbox):
                try:
                    doc = self._process_message(message, source=f"mbox::{path.name}::{i}")
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.warning(f"[Email] Failed to process message {i}: {e}")
            logger.info(f"[Email] Extracted {len(documents)} emails from MBOX")
        except Exception as e:
            logger.error(f"[Email] MBOX scan failed: {e}")
        return documents

    def scan_pst(self, path: Path) -> List[Dict[str, Any]]:
        """Parse PST/OST files using best available method"""
        logger.info(f"[Email] Scanning PST: {path}")
        
        # Method 1: Libratom (Forensics Library - Best for standalone)
        if LIBRATOM_AVAILABLE:
            return self._scan_pst_libratom(path)
        
        # Method 2: Win32 COM (Uses local Outlook - Good if installed)
        if WIN32_AVAILABLE:
            return self._scan_pst_win32(path)
            
        logger.warning("[Email] partial PST support: Install 'libratom' or use on Windows with Outlook.")
        return []

    def _scan_pst_win32(self, path: Path) -> List[Dict[str, Any]]:
        """Use local Outlook to read PST (Windows only)"""
        documents = []
        try:
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            # PST must be added to store to be read
            try:
                outlook.AddStore(str(path))
            except Exception as e:
                # Might already be open
                logger.debug(f"[Email] AddStore warning (might be open): {e}")

            # Find the store
            pst_store = None
            for store in outlook.Stores:
                if str(path) not in str(store.FilePath):
                    continue
                pst_store = store
                break

            if not pst_store:
                logger.error("[Email] Could not load PST in Outlook")
                return []

            root = pst_store.GetRootFolder()
            documents.extend(self._walk_outlook_folders(root, source_file=path.name))
            
            # Cleanup: Remove store? Maybe dangerous if user uses it.
            # safe to leave open usually
            
        except Exception as e:
            logger.error(f"[Email] Win32 PST scan failed: {e}")
        
        return documents

    def _walk_outlook_folders(self, folder, source_file) -> List[Dict]:
        """Walk outlook folders."""
        docs = []
        try:
            for item in folder.Items:
                try:
                    # Only process MailItem (Class 43)
                    if getattr(item, 'Class', 0) == 43:
                        sender = getattr(item, 'SenderName', 'Unknown')
                        subject = getattr(item, 'Subject', 'No Subject')
                        body = getattr(item, 'Body', '')
                        received_time = getattr(item, 'ReceivedTime', datetime.now())
                        
                        # Normalize date
                        if hasattr(received_time, 'strftime'):
                            date_str = received_time.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            date_str = str(received_time)

                        content = f"Date: {date_str}\nFrom: {sender}\nSubject: {subject}\n\n{body}"
                        
                        docs.append({
                            "content": content,
                            "title": f"Email: {subject}",
                            "url": f"pst://{source_file}/{getattr(item, 'EntryID', 'unknown')}",
                            "metadata": {
                                "date": date_str,
                                "sender": sender,
                                "type": "email"
                            }
                        })
                except Exception:
                    continue
            
            for sub in folder.Folders:
                docs.extend(self._walk_outlook_folders(sub, source_file))
                
        except Exception as e:
            logger.debug(f"[Email] Folder error: {e}")
        return docs
        
    def _scan_pst_libratom(self, path: Path) -> List[Dict[str, Any]]:
        """Use libratom for standalone PST parsing"""
        documents = []
        try:
            archive = PffArchive(str(path))
            for folder in archive.folders():
                if folder.name == "Top of Personal Folders": continue
                for message in folder.sub_messages:
                    try:
                        # Libratom logic (simplified)
                        # We need to extract properties relative to mapping
                        sender = message.get_transport_headers().get('From', 'Unknown')
                        subject = message.subject
                        body = message.get_plain_text_body() 
                        date = message.client_submit_time
                        
                        content = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{body}"
                        documents.append({
                            "content": content,
                            "title": f"Email: {subject}",
                            "url": f"pst://{path.name}/{message.identifier}",
                             "metadata": {
                                "date": str(date),
                                "sender": sender,
                                "type": "email"
                            }
                        })
                    except Exception: continue
        except Exception as e:
            logger.error(f"[Email] Libratom error: {e}")
        return documents

    def _process_message(self, message, source: str) -> Optional[Dict[str, Any]]:
        """Normalize Python email.message.Message to RAG Doc"""
        try:
            subject = message['subject'] or "No Subject"
            sender = message['from'] or "Unknown Sender"
            date_header = message['date']
            
            # Normalize Date
            date_str = "Unknown Date"
            if date_header:
                try:
                    dt = parsedate_to_datetime(date_header)
                    date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_str = str(date_header)

            # Extract Body
            body = ""
            if message.is_multipart():
                for part in message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors='replace')
            else:
                payload = message.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors='replace')

            # Build Content for LLM
            # We structure it so the LLM clearly sees the metadata in the text
            full_text = f"Date: {date_str}\nFrom: {sender}\nSubject: {subject}\n\n{body}"
            
            return {
                "content": full_text,
                "title": f"Email: {subject}",
                "url": source,
                "metadata": {
                    "date": date_str,
                    "sender": sender,
                    "year": int(date_str[:4]) if date_str[:4].isdigit() else 0,
                    "type": "email"
                }
            }
        except Exception as e:
            logger.debug(f"[Email] Processing error: {e}")
            return None
