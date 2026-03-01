# -*- coding: utf-8 -*-
"""
ui/formatters.py - Data Formatting Utilities
Consistent formatting for model info, file sizes, numbers, etc.
"""

from typing import Optional, Tuple


class _FormattersBase:
    """Base methods for Formatters."""

    def file_size(bytes_size: int, precision: int = 1) -> str:
        """
        Format bytes to human-readable size.
        
        Args:
            bytes_size: Size in bytes
            precision: Decimal places
            
        Returns:
            Formatted string like "4.2 GB"
        """
        if bytes_size < 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = float(bytes_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.{precision}f} {units[unit_index]}"
    
    @staticmethod
    def gb_to_display(gb: float) -> str:
        """Format GB value for display."""
        if gb < 1:
            return f"{int(gb * 1024)} MB"
        return f"{gb:.1f} GB"
    
    # ==========================================================================
    # NUMBER FORMATTING
    # ==========================================================================
    
    @staticmethod
    def number_abbreviated(num: int) -> str:
        """
        Format large numbers with K, M, B suffixes.
        
        Args:
            num: Number to format
            
        Returns:
            Formatted string like "1.2M+"
        """
        if num < 0:
            return "0"
        
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B+"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M+"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K+"
        else:
            return str(num)
    
    @staticmethod
    def downloads(count: int) -> str:
        """Format download count for display."""
        return f"📊 {Formatters.number_abbreviated(count)} downloads"
    
    @staticmethod
    def stars(count: int) -> str:
        """Format star count for display."""
        return f"⭐ {Formatters.number_abbreviated(count)}"
    
    # ==========================================================================
    # MODEL INFO FORMATTING
    # ==========================================================================
    
    @staticmethod
    def model_parameters(size_gb: float) -> str:
        """
        Estimate parameters from model size (rough Q4_K_M estimate).
        
        Args:
            size_gb: Model file size in GB
            
        Returns:
            Human-readable parameter count
        """
        # Q4_K_M is roughly 4.5 bits per parameter
        # So 1B params ≈ 0.56 GB
        estimated_params = size_gb / 0.56
        
        if estimated_params >= 1:
            return f"~{estimated_params:.0f}B parameters"
        else:
            return f"~{estimated_params * 1000:.0f}M parameters"
    
    @staticmethod
    def ram_estimate(size_gb: float, overhead: float = 1.2) -> str:
        """
        Estimate RAM needed for model.
        
        Args:
            size_gb: Model file size in GB
            overhead: Multiplier for KV cache and overhead
            
        Returns:
            RAM requirement string
        """
        ram_needed = size_gb * overhead
        
        if ram_needed < 4:
            return f"~{ram_needed:.1f}GB RAM (runs on most systems)"
        elif ram_needed < 8:
            return f"~{ram_needed:.0f}GB RAM (needs decent GPU/RAM)"
        elif ram_needed < 16:
            return f"~{ram_needed:.0f}GB RAM (needs 16GB+ system)"
        else:
            return f"~{ram_needed:.0f}GB RAM (needs high-end system)"


class Formatters(_FormattersBase):
    """
    Data formatting utilities for consistent display across the UI.
    """
    
    # ==========================================================================
    # FILE SIZE FORMATTING
    # ==========================================================================
    
    @staticmethod
    
    @staticmethod
    def speed_rating(size_gb: float) -> Tuple[str, str]:
        """
        Get speed and quality ratings based on model size.
        
        Args:
            size_gb: Model file size in GB
            
        Returns:
            Tuple of (speed_rating, quality_rating)
        """
        if size_gb <= 2.5:
            return ("⚡⚡⚡ Fast", "⭐⭐⭐")
        elif size_gb <= 5:
            return ("⚡⚡ Balanced", "⭐⭐⭐⭐")
        elif size_gb <= 6:
            return ("⚡⚡ Balanced", "⭐⭐⭐⭐")
        else:
            return ("⚡ Moderate", "⭐⭐⭐⭐⭐")
    
    @staticmethod
    def quantization_human(quant: str) -> str:
        """
        Convert quantization code to human-readable description.
        
        Args:
            quant: Quantization string (e.g., "Q4_K_M")
            
        Returns:
            Human-readable description
        """
        quant_map = {
            "Q2_K": "Tiny (lowest quality, fastest)",
            "Q3_K_S": "Small (low quality, very fast)",
            "Q3_K_M": "Small (low quality, fast)",
            "Q3_K_L": "Small-Medium (decent quality, fast)",
            "Q4_0": "Medium (good quality, balanced)",
            "Q4_K_S": "Medium (good quality, balanced)",
            "Q4_K_M": "Balanced (good speed + quality) ⭐ RECOMMENDED",
            "Q4_K_L": "Medium-Large (better quality)",
            "Q5_0": "Large (high quality, slower)",
            "Q5_K_S": "Large (high quality, slower)",
            "Q5_K_M": "Large (high quality, slower)",
            "Q6_K": "Very Large (excellent quality, slow)",
            "Q8_0": "Huge (best quality, slowest)",
            "F16": "Full precision (research only)",
            "F32": "Full precision (research only)",
        }
        
        # Try exact match first
        if quant.upper() in quant_map:
            return quant_map[quant.upper()]
        
        # Try partial match
        quant_upper = quant.upper()
        for key, value in quant_map.items():
            if key in quant_upper:
                return value
        
        return "Balanced (good speed + quality) ⭐ RECOMMENDED"
    
    # ==========================================================================
    # CONTEXT WINDOW FORMATTING
    # ==========================================================================
    
    @staticmethod
    def context_window(tokens: int) -> str:
        """
        Format context window size with word estimate.
        
        Args:
            tokens: Number of tokens
            
        Returns:
            Formatted string with word estimate
        """
        words = int(tokens * 0.75)  # Rough estimate: 1 token ≈ 0.75 words
        
        if tokens >= 1000:
            token_str = f"{tokens // 1000}K"
        else:
            token_str = str(tokens)
        
        if words >= 1000:
            word_str = f"~{words // 1000:,}K"
        else:
            word_str = f"~{words:,}"
        
        return f"{token_str} tokens ({word_str} words)"
    
    # ==========================================================================
    # TIME FORMATTING
    # ==========================================================================
    
    @staticmethod
    def duration(seconds: float) -> str:
        """
        Format duration in seconds to human-readable.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted string like "2m 30s"
        """
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
    
    @staticmethod
    def eta(elapsed: float, current: int, total: int) -> str:
        """
        Calculate and format ETA.
        
        Args:
            elapsed: Seconds elapsed
            current: Current progress count
            total: Total count
            
        Returns:
            ETA string like "2m 30s"
        """
        if current <= 0:
            return "Calculating..."
        
        avg_time = elapsed / current
        remaining = avg_time * (total - current)
        return Formatters.duration(remaining)
    
    # ==========================================================================
    # TOKENS / PERFORMANCE
    # ==========================================================================
    
    @staticmethod
    def tokens_per_second(tokens: int, seconds: float) -> str:
        """Format tokens per second rate."""
        if seconds <= 0:
            return "N/A"
        rate = tokens / seconds
        return f"{rate:.1f} tok/s"
    
    # ==========================================================================
    # TRUNCATION
    # ==========================================================================
    
    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate text to max length with suffix.
        
        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: String to append when truncated
            
        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def preview(text: str, max_length: int = 300) -> str:
        """Create a preview of long text, removing newlines."""
        clean = text.strip().replace('\n', ' ').replace('  ', ' ')
        return Formatters.truncate(clean, max_length)
