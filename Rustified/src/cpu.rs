// ============================================================================
// CPU Feature Detection Module
// Detects CPU capabilities: AVX2, SSE2, etc.
// ============================================================================

#[derive(Debug, Clone)]
pub struct CpuFeatures {
    pub has_avx2: bool,
    pub has_sse2: bool,
    pub vendor: String,
    pub brand: String,
}

impl CpuFeatures {
    pub fn display(&self) -> String {
        let cpu_tier = if self.has_avx2 {
            "AVX2 (Optimized)"
        } else if self.has_sse2 {
            "SSE2 (Standard)"
        } else {
            "Baseline"
        };

        format!(
            "{} — {} ({})",
            self.brand, self.vendor, cpu_tier
        )
    }

    pub fn bundle_variant(&self) -> &'static str {
        if self.has_avx2 {
            "avx2"
        } else if self.has_sse2 {
            "sse2"
        } else {
            "baseline"
        }
    }
}

pub fn detect_cpu_features() -> CpuFeatures {
    // Use raw CPUID if available on x86/x64
    #[cfg(target_arch = "x86_64")]
    {
        detect_x86_64_features()
    }

    #[cfg(not(target_arch = "x86_64"))]
    {
        // Fallback for ARM, etc.
        CpuFeatures {
            has_avx2: false,
            has_sse2: false,
            vendor: "Unknown".to_string(),
            brand: "Unknown CPU".to_string(),
        }
    }
}

#[cfg(target_arch = "x86_64")]
fn detect_x86_64_features() -> CpuFeatures {
    // Using inline assembly to call CPUID
    let (vendor, brand, has_sse2, has_avx2) = unsafe {
        // CPUID function 0: vendor info
        let mut eax = 0u32;
        let mut ebx = 0u32;
        let mut ecx = 0u32;
        let mut edx = 0u32;

        // Get vendor string
        std::arch::x86_64::__cpuid(0);
        let cpuid_0 = std::arch::x86_64::__cpuid(0);
        let vendor_bytes = [
            (cpuid_0.ebx as u8) as u8,
            ((cpuid_0.ebx >> 8) as u8) as u8,
            ((cpuid_0.ebx >> 16) as u8) as u8,
            ((cpuid_0.ebx >> 24) as u8) as u8,
            (cpuid_0.edx as u8) as u8,
            ((cpuid_0.edx >> 8) as u8) as u8,
            ((cpuid_0.edx >> 16) as u8) as u8,
            ((cpuid_0.edx >> 24) as u8) as u8,
            (cpuid_0.ecx as u8) as u8,
            ((cpuid_0.ecx >> 8) as u8) as u8,
            ((cpuid_0.ecx >> 16) as u8) as u8,
            ((cpuid_0.ecx >> 24) as u8) as u8,
        ];

        let vendor = String::from_utf8_lossy(&vendor_bytes).trim().to_string();

        // CPUID function 1: feature flags
        let cpuid_1 = std::arch::x86_64::__cpuid(1);
        let has_sse2 = (cpuid_1.edx & (1 << 26)) != 0;

        // CPUID function 7: extended features
        let cpuid_7 = std::arch::x86_64::__cpuid(7);
        let has_avx2 = (cpuid_7.ebx & (1 << 5)) != 0;

        // Get brand string (functions 0x80000002, 0x80000003, 0x80000004)
        let brand = get_cpu_brand();

        (vendor, brand, has_sse2, has_avx2)
    };

    CpuFeatures {
        has_avx2,
        has_sse2,
        vendor,
        brand,
    }
}

#[cfg(target_arch = "x86_64")]
fn get_cpu_brand() -> String {
    use std::arch::x86_64::__cpuid;

    let mut brand = String::new();

    for func in 0x80000002..=0x80000004 {
        let cpuid = unsafe { __cpuid(func) };

        brand.push_str(&cpuid_value_to_string(cpuid.eax));
        brand.push_str(&cpuid_value_to_string(cpuid.ebx));
        brand.push_str(&cpuid_value_to_string(cpuid.ecx));
        brand.push_str(&cpuid_value_to_string(cpuid.edx));
    }

    brand.trim().to_string()
}

#[cfg(target_arch = "x86_64")]
fn cpuid_value_to_string(value: u32) -> String {
    let bytes = [
        (value & 0xFF) as u8,
        ((value >> 8) & 0xFF) as u8,
        ((value >> 16) & 0xFF) as u8,
        ((value >> 24) & 0xFF) as u8,
    ];
    String::from_utf8_lossy(&bytes).to_string()
}
