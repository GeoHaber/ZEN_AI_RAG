# ZEN_AI Production Microphone Self-Healing System

## Overview

The new `ProductionMicrophoneHealer` is a professional-grade diagnostic and auto-healing system for microphone issues. It provides:

✓ Device lock detection (finds which apps are using microphone)
✓ Audio quality scoring (0-100 scale)
✓ Intelligent device fallback
✓ Process monitoring
✓ Actionable recommendations

## Architecture

### Key Components

**ProductionMicrophoneHealer** - Main healing class
- `full_diagnostic()` - Run complete system check
- `auto_heal_with_recommendations()` - Full diagnostic + recommendations
- `score_device(device_id)` - Evaluate device quality
- `is_device_locked(device_id)` - Check if locked by other app

**ProcessAudioUsageDetector** - Process monitoring
- `find_processes_using_microphone()` - List audio-using apps

**DeviceScore** - Evaluation dataclass
- `availability_score` - Is device free? (0-100)
- `quality_score` - How good is audio? (0-100)
- `priority_score` - Is it preferred device? (0-100)
- `total_score` - Weighted combination

## Usage

### Run Standalone Diagnostic
```bash
python zena_mode/production_microphone_healer.py
```

Output:
```
[HEALING] MICROPHONE AUTO-HEALING SYSTEM
[INFO] Found 10 input device(s)
  Testing device #1: Microphone (Logi Webcam C920e)
    Availability: 100/100 - Device available
    Quality: 0/100 - Silent - no audio detected
    Priority: 100/100 - Logitech device (preferred)
    TOTAL: 70/100

[BEST] Device #1 - Microphone (Logi Webcam C920e)
[WARNING] Audio-using processes detected:
    * Google Chrome (PID: 2216)
    * Microsoft Edge (PID: 3564)
    ... and 64 more

[ADVICE] RECOMMENDATIONS:
  [ACTION] Microphone audio quality is very low. Increase microphone volume in Windows Sound Mixer
```

### Use in Python Code

```python
from zena_mode.production_microphone_healer import ProductionMicrophoneHealer

# Create healer instance
healer = ProductionMicrophoneHealer(timeout_sec=2.0)

# Run full diagnostic
result = healer.auto_heal_with_recommendations()

# Check status
if result['status'] == 'OK':
    print("Microphone ready!")
else:
    print("Issues found:")
    for rec in result['recommendations']:
        print(f"  {rec}")

# Get best device
best_device_id = result['diagnostic']['best_device_id']
```

## Understanding the Scores

### Availability Score (0-100)
| Score | Status | Meaning |
|-------|--------|---------|
| 100 | ✓ Available | Device is free, no locks detected |
| 0 | ✗ Locked | Another app is using the device |

### Quality Score (0-100)
| Score | Status | Meaning |
|-------|--------|---------|
| 100 | Excellent | Strong signal (RMS > 0.3) |
| 85 | Good | Clear audio (RMS 0.1-0.3) |
| 60 | Fair | Somewhat quiet (RMS 0.05-0.1) |
| 40 | Poor | Very quiet (RMS 0.01-0.05) |
| 0 | Silent | No audio (RMS < 0.01) |

### Priority Score (0-100)
| Device | Score | Reason |
|--------|-------|--------|
| Logitech | 100 | Preferred brand |
| Microphone | 80 | Labeled as microphone |
| Audio Input | 60 | Generic audio device |
| Unknown | 30 | Unrecognized device |

### Total Score (Weighted)
```
Total = (Availability × 0.5) + (Quality × 0.3) + (Priority × 0.2)
```

Higher availability matters most (50%), quality second (30%), and priority lowest (20%).

## Common Issues and Solutions

### Issue: "Microphone locked by: Google Chrome, Microsoft Edge"

**Cause**: Browser tabs or applications are using the microphone

**Solution**:
1. Check if any browser tab has camera/microphone permission active
2. Close browser tabs that accessed the microphone
3. Restart your browser
4. Check: Settings → Privacy → Camera/Microphone permissions

### Issue: "Microphone audio quality is very low"

**Cause**: Windows system microphone volume is too low

**Solution**:
1. Right-click speaker icon in Windows taskbar
2. Select "Sound settings"
3. Scroll to "Input" section
4. Find "Microphone (Logi Webcam C920e)"
5. Increase microphone volume slider to 80-100%

Alternatively:
```powershell
# PowerShell to check microphone level
Get-Volume
```

### Issue: "Device error: Unanticipated host error"

**Cause**: Hardware conflict or driver issue

**Solution**:
1. Unplug USB microphone and plug back in
2. Update audio drivers (Control Panel → Device Manager → Audio inputs)
3. Restart computer
4. Try a different USB port

## Integration Points

### Voice Manager Integration
The healer can be automatically called before recording:

```python
from zena_mode.production_microphone_healer import ProductionMicrophoneHealer
from zena_mode.voice_manager import VoiceManager

# Check microphone health before recording
healer = ProductionMicrophoneHealer()
diag = healer.full_diagnostic(verbose=False)

if diag['best_device_id'] is not None:
    # Safe to record
    vm = VoiceManager(device=diag['best_device_id'])
    audio_bytes = vm.record_audio()
```

### UI Integration
Display healer in debug audio interface:

```python
# In zena.py or debug_audio_page.py
@ui.page("/debug/microphone")
def microphone_diagnostic():
    healer = ProductionMicrophoneHealer()
    result = healer.auto_heal_with_recommendations()
    
    # Display device scores table
    with ui.column():
        ui.label("Device Diagnostic Report")
        
        for device in result['diagnostic']['devices']:
            ui.label(f"{device['device_name']}: {device['total_score']}/100")
        
        ui.label(f"Best Device: #{result['diagnostic']['best_device_id']}")
        
        for rec in result['recommendations']:
            ui.label(rec)
```

## Performance

**Diagnostic Time**: ~2-3 seconds per device tested
- Availability check: 200ms (stream open attempt)
- Quality check: 500ms (record & analyze)
- Total for 10 devices: ~7-10 seconds

**Memory Usage**: Negligible (<5MB)

**CPU Usage**: Low (mostly waiting for audio I/O)

## Advanced Usage

### Custom Device Scoring
```python
healer = ProductionMicrophoneHealer()
score = healer.score_device(device_id=1)

print(f"Device: {score.device_name}")
print(f"Total: {score.total_score}/100")
print(f"Details:")
print(f"  Availability: {score.availability_score} - {score.availability_reason}")
print(f"  Quality: {score.quality_score} - {score.quality_reason}")
print(f"  Priority: {score.priority_score} - {score.priority_reason}")
```

### Find Competing Processes
```python
healer = ProductionMicrophoneHealer()
processes = healer.process_detector.find_processes_using_microphone()

for proc in processes:
    print(f"{proc['name']} (PID: {proc['pid']})")
```

### Loopback Test Only
```python
healer = ProductionMicrophoneHealer()
success, confidence, reason = healer.verify_loopback(device_id=1)

if success:
    print(f"Loopback verified with {confidence*100:.1f}% confidence")
else:
    print(f"Loopback failed: {reason}")
```

## Best Practices

1. **Run before critical recording sessions**
   ```python
   healer.auto_heal_with_recommendations()
   ```

2. **Cache device selection**
   ```python
   best_device = result['diagnostic']['best_device_id']
   # Use same device for entire session
   ```

3. **Monitor in background**
   ```python
   # Periodically check health
   result = healer.full_diagnostic(verbose=False)
   if result['best_device_id'] is None:
       print("Microphone issue detected!")
   ```

4. **Provide user feedback**
   ```python
   for rec in result['recommendations']:
       ui.notify(rec)
   ```

## Technical Details

### Device Lock Detection
- Opens input stream (InputStream)
- If fails with "device busy" error → locked
- Catches RuntimeError with specific messages
- Returns which processes are likely using device

### Quality Measurement
- Records 1 second of audio at 16kHz
- Calculates RMS (root mean square) level
- RMS < 0.01 → Silent
- RMS 0.01-0.05 → Poor
- RMS 0.05-0.1 → Fair
- RMS 0.1-0.3 → Good
- RMS > 0.3 → Excellent

### Fallback Strategy
- Score all available devices
- Sort by total score (weighted)
- Availability (50%) most important
- Quality (30%) second
- Priority (20%) least important

## Files

- `zena_mode/production_microphone_healer.py` - Main implementation (400+ lines)
- `MICROPHONE_HEALING_GUIDE.md` - This guide
- `ui/debug_audio_page.py` - Debug interface (uses injected audio)
- `zena_mode/voice_manager.py` - Can call healer before recording

## Related

- [AUDIO_INJECTION_GUIDE.md](AUDIO_INJECTION_GUIDE.md) - Synthetic audio testing
- [zena_mode/voice_manager.py](zena_mode/voice_manager.py) - Audio recording
- [ui/debug_audio_page.py](ui/debug_audio_page.py) - Debug UI
